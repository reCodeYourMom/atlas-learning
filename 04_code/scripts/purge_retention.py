"""Purge de rétention des données mineurs (PDPL) — cible cron nocturne.

Un élève désinscrit (soft delete par la sync de rostering ou par le staff) ne doit pas
rester indéfiniment en base : passé RETENTION_DAYS (env, défaut 30 jours), ses données
sont SUPPRIMÉES DUREMENT — réponses, abilities, sessions, inscriptions et liens parent
suivent par cascade FK (mêmes cascades que le droit à l'oubli, cf. compliance/service.py).

SÉCURITÉ DU SCRIPT :
  - ne touche QUE les lignes `deleted_at` NON NULL et plus vieilles que la rétention —
    jamais un élève actif, jamais un soft delete récent (fenêtre de récupération) ;
  - LEGAL HOLD (avis juridique 2026-07-08) : n'efface JAMAIS un élève dont `legal_hold`
    est posé, ni aucun élève d'une école dont `legal_hold` est posé (instruction
    documentée du controller / litige) — ces élèves sont comptés `held_skipped` ;
  - RETENTION_DAYS est PLAFONNÉ à MAX_RETENTION_DAYS (30) : la fenêtre de grâce ne peut
    pas être étendue par configuration au-delà du maximum juridiquement retenu ;
  - --dry-run PAR DÉFAUT (rapport sans rien supprimer) ; exécution réelle via --execute ;
  - chaque purge est journalisée dans AuditLog (append-only, sans PII).

Purge aussi les `jti` de liens magiques expirés (table consumed_token, anti-rejeu) :
une fois le jeton expiré, la ligne de consommation ne sert plus à rien.

Usage   : DATABASE_URL=... python scripts/purge_retention.py [--execute] [--retention-days N]
Cron ex.: 10 3 * * *  cd /app/04_code && python scripts/purge_retention.py --execute
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.audit import log_action
from src.db import SessionLocal, make_engine
from src.models.base import ensure_utc, utcnow
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import AppUser, ParentStudent
from src.models.session import AssessmentSession
from src.models.token import ConsumedToken

DEFAULT_RETENTION_DAYS = 30
# Plafond juridique de la fenêtre de grâce (avis 2026-07-08) : RETENTION_DAYS ne peut pas
# être étendu au-delà, quelle que soit la configuration.
MAX_RETENTION_DAYS = 30


def _count(s: Session, model, where) -> int:
    return s.execute(select(func.count()).select_from(model).where(where)).scalar_one()


def purge_retention(s: Session, *, retention_days: Optional[int] = None,
                    now: Optional[datetime] = None, execute: bool = False) -> dict:
    """Purge les élèves soft-deleted au-delà de la rétention + les jti expirés.

    `execute=False` (défaut) = dry-run : rapporte ce qui SERAIT purgé, ne supprime rien
    et n'écrit rien (ni delete, ni audit, ni commit).
    """
    now = ensure_utc(now) or utcnow()   # naïf accepté (tests) → réinterprété UTC
    configured = retention_days if retention_days is not None else int(
        os.environ.get("RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
    # Plafond juridique : la fenêtre de grâce ne peut jamais dépasser MAX_RETENTION_DAYS.
    days = min(configured, MAX_RETENTION_DAYS)
    cutoff = now - timedelta(days=days)

    # Écoles sous legal hold tenant-large → aucun de leurs élèves n'est purgé.
    held_school_ids = set(s.execute(
        select(School.id).where(School.legal_hold.is_not(None))
    ).scalars().all())

    # GARDE-FOU : deleted_at NON NULL **et** plus vieux que la rétention, rien d'autre.
    # On récupère tous les éligibles PAR DATE puis on écarte ceux sous legal hold — propre
    # (Student.legal_hold posé) ou hérité (école sous hold) — comptés en `held_skipped`.
    eligible = s.execute(
        select(Student).where(Student.deleted_at.is_not(None), Student.deleted_at < cutoff)
    ).scalars().all()

    def _held(st) -> bool:
        return st.legal_hold is not None or st.school_id in held_school_ids

    students = [st for st in eligible if not _held(st)]
    held_skipped = sum(1 for st in eligible if _held(st))

    purged, users_purged = [], 0
    for st in students:
        related = {
            "responses": _count(s, Response, Response.student_id == st.id),
            "abilities": _count(s, StudentCompetencyAbility,
                                StudentCompetencyAbility.student_id == st.id),
            "sessions": _count(s, AssessmentSession, AssessmentSession.student_id == st.id),
            "parent_links": _count(s, ParentStudent, ParentStudent.student_id == st.id),
        }
        purged.append({"student_id": str(st.id), "deleted_at": st.deleted_at.isoformat(),
                       **related})
        if not execute:
            continue
        school_id, student_id, user_id = st.school_id, st.id, st.user_id
        s.delete(st)   # cascade FK : response, ability, session, inscriptions, liens parent
        s.flush()
        # Le compte élève (email = PII) n'est purgé QUE s'il est lui-même soft-deleted
        # au-delà de la rétention — jamais un compte encore vivant.
        if user_id is not None:
            u = s.get(AppUser, user_id)
            # ensure_utc : deleted_at relu de SQLite est naïf (convention UTC) — sans ça,
            # la comparaison avec `cutoff` (aware) lèverait TypeError.
            if u is not None and u.deleted_at is not None and ensure_utc(u.deleted_at) < cutoff:
                s.delete(u)
                users_purged += 1
        log_action(s, action="retention.purge_student", school_id=school_id,
                   resource_type="student", resource_id=student_id,
                   details={"retention_days": days, **related})

    # jti consommés dont le jeton est expiré : plus aucun rejeu possible → ligne inutile.
    tokens_expired = _count(s, ConsumedToken, ConsumedToken.expires_at < now)
    if execute:
        s.execute(delete(ConsumedToken).where(ConsumedToken.expires_at < now))
        log_action(s, action="retention.purge",
                   details={"students": len(purged), "users": users_purged,
                            "consumed_tokens": tokens_expired, "retention_days": days,
                            "held_skipped": held_skipped})
        s.commit()

    return {"dry_run": not execute, "retention_days": days, "cutoff": cutoff.isoformat(),
            "students": purged, "users_purged": users_purged,
            "consumed_tokens_purged": tokens_expired, "held_skipped": held_skipped}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Purge de rétention des données mineurs (dry-run par défaut).")
    parser.add_argument("--execute", action="store_true",
                        help="supprime réellement (sinon : rapport dry-run)")
    parser.add_argument("--retention-days", type=int, default=None,
                        help=f"surcharge RETENTION_DAYS (env, défaut {DEFAULT_RETENTION_DAYS})")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = purge_retention(s, retention_days=args.retention_days, execute=args.execute)

    mode = "EXÉCUTÉ" if args.execute else "DRY-RUN (rien supprimé — utiliser --execute)"
    print(f"[{mode}] rétention {report['retention_days']} j — cutoff {report['cutoff']}")
    for st in report["students"]:
        print(f"  élève {st['student_id']} (soft-deleted {st['deleted_at']}) : "
              f"{st['responses']} réponses, {st['abilities']} abilities, "
              f"{st['sessions']} sessions, {st['parent_links']} liens parent")
    print(f"  total : {len(report['students'])} élève(s), {report['users_purged']} compte(s), "
          f"{report['consumed_tokens_purged']} jti expiré(s)")
    if report["held_skipped"]:
        print(f"  legal hold : {report['held_skipped']} élève(s) éligible(s) NON purgé(s) "
              f"(conservation imposée)")


if __name__ == "__main__":
    main()
