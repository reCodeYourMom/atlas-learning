"""Contrôle de fidélité math des traductions AR (assist validation linguiste).

Vérifie que chaque content_ar préserve la réponse + les options (chiffres) du content_en.
Les items qui échouent ont eu un nombre altéré par la traduction → à revoir en priorité.
`--flag` marque les items recalés dans provenance (ar_math_broken).

Usage : python scripts/check_ar_fidelity.py [--flag]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.arabic import ar_math_preserved
from src.models.competency import Competency  # noqa: F401 (FK)
from src.models.item import Item


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--flag", action="store_true")
    args = p.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        items = s.execute(select(Item).where(Item.deleted_at.is_(None))).scalars().all()
        translated = [it for it in items if it.content_ar]
        broken = [it for it in translated if not ar_math_preserved(it.content_en, it.content_ar)]

        if args.flag:
            for it in broken:
                it.provenance = {**(it.provenance or {}), "ar_math_broken": True}
            s.commit()

        print(f"AR traduits : {len(translated)}/{len(items)}")
        print(f"Fidélité math OK : {len(translated) - len(broken)}/{len(translated)}")
        print(f"À revoir en priorité (nombre altéré) : {len(broken)}"
              + (" (flaggés)" if args.flag else ""))
        for it in broken[:10]:
            print(f"  ✗ {it.id}  EN={it.content_en.get('answer')}  AR={it.content_ar.get('answer')}")


if __name__ == "__main__":
    main()
