"""Génération en volume de la banque d'items (exécution Epic 2).

Parcourt les compétences seedées et génère des items EN (statut ai_generated)
en couvrant les `item_contexts` du référentiel. Idempotent/résumable :
on ne regénère pas si la compétence a déjà atteint sa cible.

Usage :
    GROQ_API_KEY=... python scripts/generate_bank.py [--per-context N] [--only CODE]

Pré-requis : alembic upgrade head + seed_referentiel. N'insère que du EN
(la traduction AR et la revue suivent les workflows T2.3/T2.4).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from src.db import SessionLocal, make_engine
from src.items.generation import GenerationError, generate_items
from src.items.review import insert_generated_items
from src.llm.client import GroqClient
from src.models.base import AnswerFormat
from src.models.competency import Competency
from src.models.item import Item

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "referentiel_fractions.json"


def _contexts_by_code() -> dict:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {n["code"]: n.get("item_contexts", []) for n in data["nodes"]}


def _count_items(s, competency_id) -> int:
    return s.execute(
        select(func.count()).select_from(Item)
        .where(Item.competency_id == competency_id, Item.deleted_at.is_(None))
    ).scalar_one()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--per-context", type=int, default=2, help="items par contexte (défaut 2)")
    p.add_argument("--only", help="ne traiter qu'un code de compétence")
    p.add_argument("--retries", type=int, default=2)
    args = p.parse_args()

    contexts_map = _contexts_by_code()
    client = GroqClient()
    engine = make_engine()

    total_new = 0
    with SessionLocal(bind=engine) as s:
        comps = s.execute(select(Competency).order_by(Competency.code)).scalars().all()
        if args.only:
            comps = [c for c in comps if c.code == args.only]

        for comp in comps:
            contexts = contexts_map.get(comp.code) or ["default"]
            target = len(contexts) * args.per_context
            have = _count_items(s, comp.id)
            if have >= target:
                print(f"= {comp.code}: {have}/{target} (déjà complet, skip)")
                continue

            batch = []
            for ctx in contexts:
                target_spec = {"context": ctx}
                for _ in range(args.per_context):
                    for attempt in range(args.retries + 1):
                        try:
                            batch += generate_items(
                                comp, [target_spec], client, answer_format=AnswerFormat.MCQ
                            )
                            break
                        except GenerationError as e:
                            print(f"  ! {comp.code} [{ctx}] sortie invalide (essai {attempt+1}): {str(e)[:80]}")
                        except Exception as e:  # rate limit / réseau
                            wait = 2 * (attempt + 1)
                            print(f"  … {comp.code} [{ctx}] erreur API (essai {attempt+1}), pause {wait}s: {str(e)[:80]}")
                            time.sleep(wait)
            if batch:
                inserted = insert_generated_items(s, batch)
                total_new += len(inserted)
                print(f"+ {comp.code}: +{len(inserted)} items (total {_count_items(s, comp.id)})")

    print(f"\nTerminé : {total_new} nouveaux items générés.")


if __name__ == "__main__":
    main()
