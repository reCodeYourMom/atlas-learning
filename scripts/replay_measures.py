"""Rejoue TOUTES les réponses (append-only) à travers le moteur, à graphe courant.

Pourquoi
--------
Le graphe de prérequis bouge (revue experte → nouveau poids, arête requalifiée, nouveau
nœud avec ponts). Les `Response` sont append-only précisément « pour recalculer a
posteriori » (DataModel §5.2), mais aucun outil ne le faisait : les abilities et la
propagation en base reflétaient le graphe d'AVANT. Ce script remet les estimations à
zéro puis rejoue chaque réponse, dans l'ordre chronologique, via `apply_measurement`
(le même code que le chemin nominal) — sans réécrire aucune Response.

Portée : GLOBALE, jamais par école. La difficulté d'un item est partagée entre tous les
répondants ; ne rejouer qu'un tenant fausserait `difficulty_elo` pour les autres.

Ce qui est remis à zéro puis recalculé : `student_competency_ability` (toutes lignes),
`item.difficulty_elo` (= difficulty_prior) et `item.n_responses`.
Ce qui n'est PAS touché : `response`, `assessment_session`, les items, le graphe, l'audit.

Sécurité : dry-run par défaut (compte ce qui serait rejoué). `--execute` pour agir,
dans UNE transaction (tout ou rien). À lancer hors trafic (les sessions en cours
verraient leurs abilities changer sous elles).

Usage :
  python scripts/replay_measures.py              # dry-run
  python scripts/replay_measures.py --execute
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select, update

from src.audit import log_action
from src.db import SessionLocal, make_engine
from src.engine.service import apply_measurement
from src.models.item import Item
from src.models.measurement import Response, StudentCompetencyAbility


def replay(session, *, execute: bool = False, actor: str = "replay_measures") -> dict:
    n_resp = session.execute(select(func.count()).select_from(Response)).scalar_one()
    n_abil = session.execute(select(func.count()).select_from(StudentCompetencyAbility)).scalar_one()
    n_items = session.execute(
        select(func.count()).select_from(Item).where(Item.n_responses > 0)
    ).scalar_one()
    report = {"responses": n_resp, "abilities_reset": n_abil, "items_reset": n_items,
              "executed": False, "skipped_missing_item": 0}
    if not execute:
        return report

    session.execute(delete(StudentCompetencyAbility))
    session.execute(update(Item).values(difficulty_elo=Item.difficulty_prior, n_responses=0))
    session.flush()

    # Ordre chronologique strict ; l'id départage les égalités (déterminisme).
    q = select(Response).order_by(Response.created_at, Response.id).execution_options(yield_per=500)
    items: dict = {}
    replayed = 0
    for resp in session.execute(q).scalars():
        it = items.get(resp.item_id)
        if it is None:
            it = session.get(Item, resp.item_id)
            if it is None:
                report["skipped_missing_item"] += 1
                continue
            items[resp.item_id] = it
        apply_measurement(session, student_id=resp.student_id, item=it,
                          school_id=resp.school_id, is_correct=resp.is_correct,
                          measured_at=resp.created_at)
        replayed += 1
    log_action(session, action="engine.replay_measures",
               details={"responses": replayed, "abilities_reset": n_abil,
                        "items_reset": n_items, "actor": actor})
    session.commit()
    report.update(executed=True, replayed=replayed)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Rejoue les réponses à travers le moteur (graphe courant).")
    ap.add_argument("--execute", action="store_true", help="agir (défaut : dry-run)")
    args = ap.parse_args()
    with SessionLocal(bind=make_engine()) as s:
        try:
            r = replay(s, execute=args.execute)
        except Exception:
            s.rollback()
            raise
    if r["executed"]:
        print(f"Rejoué : {r['replayed']} réponses ; {r['abilities_reset']} abilities et "
              f"{r['items_reset']} difficultés d'items recalculées"
              + (f" ; {r['skipped_missing_item']} réponses sans item ignorées" if r["skipped_missing_item"] else "") + ".")
    else:
        print(f"[dry-run] {r['responses']} réponses seraient rejouées, {r['abilities_reset']} abilities "
              f"et {r['items_reset']} difficultés d'items remises à zéro. Ajouter --execute.")


if __name__ == "__main__":
    main()
