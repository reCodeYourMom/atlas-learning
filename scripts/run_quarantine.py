"""Job quarantaine — balaie les items actifs et sort du pool ceux qui dérivent (cible cron).

Câble le garde-fou T2.5 (src/items/quarantine.py), jusqu'ici DORMANT (aucun appelant
runtime), sur le trafic RÉEL (table response) : pour chaque item actif, on compare le
taux de réussite observé au taux attendu à l'ability MOYENNE RÉELLE des répondants de
l'item — PAS la constante DEFAULT_REFERENCE_ABILITY (1200) : un item difficile servi à
des élèves forts réussirait « trop » par rapport à 1200 et serait quarantainé à tort,
alors qu'il est parfaitement cohérent avec sa cohorte (note de conception connue).

SÉCURITÉ DU SCRIPT :
  - --dry-run PAR DÉFAUT (rapport sans rien changer) ; exécution réelle via --execute ;
  - ne touche QUE les items `active` non supprimés (active_pool), jamais les autres ;
  - la quarantaine est RÉVERSIBLE (review.promote → active) ;
  - chaque mise en quarantaine est journalisée dans AuditLog (append-only, sans PII).

Usage   : DATABASE_URL=... python scripts/run_quarantine.py [--execute]
                          [--min-responses N] [--max-divergence X]
Cron    : deploy/prod/quarantine.cron (même patron que backup.cron / retention.cron).
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.audit import log_action
from src.db import SessionLocal, make_engine
from src.engine.service import ELO_START
from src.items.quarantine import (
    DEFAULT_MAX_DIVERGENCE,
    DEFAULT_MIN_RESPONSES,
    ItemStats,
    active_pool,
    apply_quarantine,
    expected_success,
    is_drifting,
)
from src.models.base import ItemStatus
from src.models.item import Item
from src.models.measurement import Response, StudentCompetencyAbility


def _item_stats(s: Session, item) -> Optional[tuple]:  # noqa: ANN001
    """(ItemStats, reference_ability) de l'item d'après le trafic réel, ou None si muet.

    reference_ability = ability moyenne ACTUELLE des répondants de l'item sur SA
    compétence (repli ELO_START si aucune ligne ability — ne devrait pas arriver :
    on_response crée l'ability à la première réponse).
    """
    rows = s.execute(
        select(Response.student_id, Response.is_correct).where(Response.item_id == item.id)
    ).all()
    if not rows:
        return None
    n = len(rows)
    success_rate = sum(1 for r in rows if r.is_correct) / n
    student_ids = {r.student_id for r in rows}
    abilities = s.execute(
        select(StudentCompetencyAbility.ability_elo).where(
            StudentCompetencyAbility.student_id.in_(student_ids),
            StudentCompetencyAbility.competency_id == item.competency_id,
        )
    ).scalars().all()
    reference = sum(abilities) / len(abilities) if abilities else ELO_START
    return ItemStats(n_responses=n, success_rate=success_rate,
                     difficulty_elo=item.difficulty_elo), reference


def run_quarantine(
    s: Session,
    *,
    min_responses: int = DEFAULT_MIN_RESPONSES,
    max_divergence: float = DEFAULT_MAX_DIVERGENCE,
    execute: bool = False,
) -> dict:
    """Balaie les items actifs, quarantaine ceux qui dérivent. Retourne un rapport.

    `execute=False` (défaut) = dry-run : rapporte ce qui SERAIT quarantainé, ne change
    rien (ni statut, ni audit, ni commit).
    """
    scanned, flagged = 0, []
    for item in active_pool(s):
        scanned += 1
        computed = _item_stats(s, item)
        if computed is None:
            continue  # item jamais répondu : rien à juger
        stats, reference = computed
        if not is_drifting(stats, min_responses=min_responses,
                           max_divergence=max_divergence, reference_ability=reference):
            continue
        entry = {
            "item_id": str(item.id),
            "competency_id": str(item.competency_id),
            "n_responses": stats.n_responses,
            "success_rate": round(stats.success_rate, 4),
            "expected": round(expected_success(stats.difficulty_elo, reference), 4),
            "reference_ability": round(reference, 1),
            "difficulty_elo": round(stats.difficulty_elo, 1),
        }
        if execute:
            # TOCTOU (revue 2026-07-08) : entre le scan (active_pool) et l'application,
            # un promote/reject concurrent (reviewer humain) peut changer le statut —
            # l'instance scannée reste `active` EN MÉMOIRE et apply_quarantine écrasait
            # la décision du reviewer (last-write-wins sur status ET sur le dict
            # provenance réécrit par _stamp_reviewer). SELECT ... FOR UPDATE
            # (+ populate_existing : sans lui, s.get rendrait l'instance PÉRIMÉE de
            # l'identity map sans la rafraîchir) verrouille la ligne jusqu'au commit et
            # recharge son état RÉEL ; on re-vérifie le statut SOUS le verrou.
            # Limite connue : SQLite (dev/CI) ignore FOR UPDATE silencieusement — le
            # rafraîchissement reste effectif, le verrou ne l'est qu'en prod (Postgres),
            # même convention que engine/service.py.
            locked = s.get(Item, item.id, with_for_update=True, populate_existing=True)
            if locked is None or locked.status != ItemStatus.ACTIVE or locked.deleted_at is not None:
                continue  # course perdue : promu/rejeté/supprimé entre le scan et le verrou
            changed = apply_quarantine(
                s, locked, stats, by="quarantine-job",
                min_responses=min_responses, max_divergence=max_divergence,
                reference_ability=reference,
            )
            if not changed:  # défense en profondeur (apply_quarantine re-teste le statut)
                continue
            log_action(s, action="item.quarantine", resource_type="item",
                       resource_id=item.id, details=entry)
            s.commit()
        flagged.append(entry)
    return {"dry_run": not execute, "scanned": scanned,
            "min_responses": min_responses, "max_divergence": max_divergence,
            "quarantined": flagged}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quarantaine des items actifs dérivants (dry-run par défaut).")
    parser.add_argument("--execute", action="store_true",
                        help="quarantaine réelle (sinon : rapport dry-run)")
    parser.add_argument("--min-responses", type=int, default=DEFAULT_MIN_RESPONSES,
                        help=f"nb minimal de réponses avant de juger (défaut {DEFAULT_MIN_RESPONSES})")
    parser.add_argument("--max-divergence", type=float, default=DEFAULT_MAX_DIVERGENCE,
                        help=f"écart observé/attendu toléré (défaut {DEFAULT_MAX_DIVERGENCE})")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = run_quarantine(s, min_responses=args.min_responses,
                                max_divergence=args.max_divergence, execute=args.execute)

    mode = "EXÉCUTÉ" if args.execute else "DRY-RUN (rien changé — utiliser --execute)"
    print(f"[{mode}] {report['scanned']} item(s) actif(s) balayé(s), "
          f"{len(report['quarantined'])} en dérive")
    for e in report["quarantined"]:
        print(f"  item {e['item_id']} : réussite {e['success_rate']:.2f} "
              f"vs attendu {e['expected']:.2f} (référence ability {e['reference_ability']}, "
              f"difficulté {e['difficulty_elo']}) sur {e['n_responses']} réponses")


if __name__ == "__main__":
    main()
