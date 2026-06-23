"""Traduction AR industrielle de la banque (ALLaM) — Epic 2.4 à l'échelle.

Pour chaque item sans content_ar : ALLaM propose la version arabe, persistée via
set_arabic (ar_validated=False → en attente de validation linguiste). Idempotent
(skip si content_ar déjà présent), résumable, retries sur erreur API.

Usage : GROQ_API_KEY=... python scripts/translate_bank_ar.py [--limit N]
Pré-requis : alembic upgrade head + banque seedée.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.arabic import ALLAM_MODEL, TranslationError, translate_to_arabic
from src.items.review import set_arabic
from src.llm.client import GroqClient
from src.models.competency import Competency  # noqa: F401  (FK)
from src.models.item import Item


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--retries", type=int, default=2)
    args = p.parse_args()

    client = GroqClient(model=ALLAM_MODEL)
    engine = make_engine()
    done = failed = skipped = 0

    with SessionLocal(bind=engine) as s:
        items = s.execute(
            select(Item).where(Item.deleted_at.is_(None)).order_by(Item.created_at)
        ).scalars().all()
        if args.limit:
            items = items[: args.limit]

        for it in items:
            if it.content_ar:
                skipped += 1
                continue
            for attempt in range(args.retries + 1):
                try:
                    ar = translate_to_arabic(it.content_en, client, answer_format=it.answer_format)
                    set_arabic(s, it, ar, by="allam")
                    done += 1
                    break
                except TranslationError as e:
                    print(f"  ! {it.id} sortie AR invalide (essai {attempt+1}): {str(e)[:70]}")
                    if attempt == args.retries:
                        failed += 1
                except Exception as e:  # rate limit / réseau
                    wait = 2 * (attempt + 1)
                    print(f"  … {it.id} erreur API (essai {attempt+1}), pause {wait}s: {str(e)[:70]}")
                    time.sleep(wait)
                    if attempt == args.retries:
                        failed += 1
            if (done + failed) % 25 == 0 and (done + failed) > 0:
                print(f"  … {done} traduits, {failed} échecs")

    print(f"\nTerminé : {done} traduits (ar_validated=False), {skipped} déjà faits, {failed} échecs.")


if __name__ == "__main__":
    main()
