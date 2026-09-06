"""Traduction AR de la banque SANS LLM — pendant déterministe de translate_bank_ar.py.

Même contrat que la voie ALLaM (`set_arabic` → `ar_validated=False`, en attente de
validation), mais l'arabe vient des ~37 gabarits de `items/arabic_deterministic` au lieu
d'un appel réseau. Aucune clé d'API, aucune latence, résultat identique à chaque exécution.

À utiliser pour la banque déterministe. Le contenu rédigé à la main ou généré par LLM garde
la voie ALLaM : ici, un énoncé non reconnu n'est PAS traduit (jamais de devinette), il est
compté et signalé.

Usage :
    python scripts/translate_bank_ar_deterministic.py [--validate] [--limit N]

--validate : pose aussi ar_validated=True (linguiste « deterministic-ar »). À réserver aux
             environnements de démo/CI : en production, la validation reste humaine.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.items.arabic import ar_math_preserved
from src.items.arabic_deterministic import translate_content
from src.items.review import set_arabic, validate_arabic
from src.db import SessionLocal, make_engine
from src.models.base import ItemStatus
from src.models.competency import Competency  # noqa: F401  (FK)
from src.models.item import Item

BY = "deterministic-ar"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--validate", action="store_true",
                   help="pose ar_validated=True (démo/CI uniquement)")
    args = p.parse_args()

    done = skipped = uncovered = broken = validated = 0
    misses = []

    with SessionLocal(bind=make_engine()) as s:
        items = s.execute(
            select(Item).where(Item.deleted_at.is_(None)).order_by(Item.created_at)
        ).scalars().all()
        if args.limit:
            items = items[: args.limit]

        for it in items:
            if not it.content_ar:
                ar = translate_content(it.content_en)
                if ar is None:
                    uncovered += 1
                    misses.append((it.content_en or {}).get("stem", "?"))
                    continue
                # Garde-fou identique à la voie LLM : un nombre altéré = on ne persiste pas.
                if not ar_math_preserved(it.content_en, ar):
                    broken += 1
                    continue
                set_arabic(s, it, ar, by=BY)
                done += 1
            else:
                skipped += 1

            # validate_arabic exige human_reviewed ; on ne force aucune transition ici.
            if args.validate and not it.ar_validated and it.status == ItemStatus.HUMAN_REVIEWED:
                validate_arabic(s, it, linguist=BY)
                validated += 1

    print(f"AR déterministe : {done} traduits, {skipped} déjà pourvus, "
          f"{validated} validés, {uncovered} non couverts, {broken} math altérée")
    if misses:
        print("\nÉnoncés sans gabarit AR (à ajouter dans items/arabic_deterministic) :")
        for m in dict.fromkeys(misses[:10]):
            print(f"  · {m}")


if __name__ == "__main__":
    main()
