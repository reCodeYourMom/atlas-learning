"""Contrôle de fidélité math des traductions AR (assist validation linguiste).

Vérifie que chaque content_ar préserve la réponse + les options (nombres) du content_en.
Les items qui échouent ont eu un nombre altéré par la traduction → à revoir en priorité.
Ajout errata E8 (gate G3) : détection des tokens latins résiduels (mot anglais non
traduit, ex. « ONE ») que le check numérique ne peut pas attraper.
Ajout revue 2026-07-12 : détection des glyphes parasites non latins (±̆, π, Ⓒ, ⅕…) —
signature d'une corruption d'encodage, invisible aux deux checks précédents.

`--flag` RÉCONCILIE la provenance : pose `ar_math_broken` / `ar_latin_tokens` /
`ar_suspect_glyphs` sur les items recalés ET retire ces clés d'un item redevenu sain
(un flag obsolète noierait les vraies corruptions — 29 faux positifs constatés avec
l'ancien check par égalité de chaînes). Chaque passage `--flag` horodate `ar_checks_at`.

Usage : python scripts/check_ar_fidelity.py [--flag]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.arabic import (
    ar_content_latin_tokens,
    ar_content_suspect_glyphs,
    ar_math_preserved,
    ar_stem_numbers_preserved,
)
from src.models.base import utcnow
from src.models.competency import Competency  # noqa: F401 (FK)
from src.models.item import Item

_FLAG_KEYS = ("ar_math_broken", "ar_stem_numbers_lost", "ar_latin_tokens", "ar_suspect_glyphs")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--flag", action="store_true")
    args = p.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        items = s.execute(select(Item).where(Item.deleted_at.is_(None))).scalars().all()
        translated = [it for it in items if it.content_ar]
        broken = [it for it in translated if not ar_math_preserved(it.content_en, it.content_ar)]
        stem_lost = [it for it in translated
                     if not ar_stem_numbers_preserved(it.content_en, it.content_ar)]
        latin = [(it, toks) for it in translated
                 if (toks := ar_content_latin_tokens(it.content_ar))]
        glyphs = [(it, gl) for it in translated
                  if (gl := ar_content_suspect_glyphs(it.content_ar))]

        if args.flag:
            broken_ids = {it.id for it in broken}
            stem_lost_ids = {it.id for it in stem_lost}
            latin_by_id = {it.id: toks for it, toks in latin}
            glyphs_by_id = {it.id: gl for it, gl in glyphs}
            stamp = utcnow().isoformat()
            cleared = 0
            for it in translated:
                prov = dict(it.provenance or {})
                fresh = {
                    "ar_math_broken": True if it.id in broken_ids else None,
                    "ar_stem_numbers_lost": True if it.id in stem_lost_ids else None,
                    "ar_latin_tokens": latin_by_id.get(it.id),
                    "ar_suspect_glyphs": glyphs_by_id.get(it.id),
                }
                changed = False
                for key, value in fresh.items():
                    if value is not None and prov.get(key) != value:
                        prov[key] = value
                        changed = True
                    elif value is None and key in prov:
                        prov.pop(key)  # flag obsolète (faux positif de l'ancien check)
                        cleared += 1
                        changed = True
                if changed:
                    prov["ar_checks_at"] = stamp
                    it.provenance = prov
            s.commit()

        print(f"AR traduits : {len(translated)}/{len(items)}")
        print(f"Fidélité math OK : {len(translated) - len(broken)}/{len(translated)}")
        print(f"À revoir en priorité (nombre altéré) : {len(broken)}"
              + (" (flaggés)" if args.flag else ""))
        for it in broken[:10]:
            print(f"  ✗ {it.id}  EN={it.content_en.get('answer')}  AR={it.content_ar.get('answer')}")
        print(f"Énoncé AR perd un nombre du stem EN (CRIT-1) : {len(stem_lost)} item(s)"
              + (" (flaggés)" if args.flag else ""))
        for it in stem_lost[:10]:
            print(f"  ✗ {it.id}  EN={it.content_en.get('stem')!r}  AR={it.content_ar.get('stem')!r}")
        print(f"Tokens latins résiduels (E8) : {len(latin)} item(s)"
              + (" (flaggés)" if args.flag else ""))
        for it, toks in latin[:10]:
            print(f"  ✗ {it.id}  tokens={toks}  stem={it.content_ar.get('stem')!r}")
        print(f"Glyphes parasites (corruption d'encodage) : {len(glyphs)} item(s)"
              + (" (flaggés)" if args.flag else ""))
        for it, gl in glyphs[:10]:
            print(f"  ✗ {it.id}  glyphes={gl}  stem={it.content_ar.get('stem')!r}")
        if args.flag:
            print(f"Flags obsolètes retirés : {cleared}")


if __name__ == "__main__":
    main()
