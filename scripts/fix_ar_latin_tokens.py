"""Correction des tokens latins résiduels dans les content_ar (errata E8).

Corrections HUMAINES, item par item (pas de traduction automatique) : chaque
remplacement est une décision de traduction en contexte, journalisée dans
provenance (action `ar_latin_token_fix` + ancien contenu) — auditable et
rejouable. Idempotent : un item déjà corrigé (plus de tokens) est sauté.

Trouvés en banque (scan du 2026-07-11, scripts/check_ar_fidelity.py) :
- « ONE » non traduit dans un stem de fraction → « جزءًا واحدًا » (accusatif) ;
- markup `<frac{a}{b}>` / `\x0crac{a}{b}` (le `\\f` de `\\frac` avalé en form
  feed) → notation acceptée « a/b » (chiffres occidentaux, E7) ; l'option
  textuelle « They are equal » → « هما متساويان ».

Usage : DATABASE_URL=sqlite:///atlas_bank.db python scripts/fix_ar_latin_tokens.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.arabic import ar_content_latin_tokens
from src.models.base import utcnow
from src.models.competency import Competency  # noqa: F401 (FK)
from src.models.item import Item

# item_id -> paires (ancien, nouveau) appliquées sur stem/options/answer
FIXES = {
    # EN « What fraction is ONE part? » — « ONE جزء » → « جزءًا واحدًا »
    "17bc5788-7abf-4645-a28f-f6fc00bd7766": [
        ("ONE جزء", "جزءًا واحدًا"),
    ],
    # markup <frac{a}{b}> résiduel + option « They are equal » non traduite
    "bf2d5bb8-6146-4bc7-bb37-1af4ecad5221": [
        ("<frac{They are equal}{2}>", "هما متساويان"),
        ("<frac{1}{4}>", "1/4"),
        ("<frac{3}{4}>", "3/4"),
        ("<frac{3}{5}>", "3/5"),
    ],
    # « \x0crac{a}{b} » (\f de \frac avalé) → fraction en notation acceptée
    "05a496bd-68f3-4302-baca-d5ea3a7d409d": [
        ("ل\x0crac{1}{3} و\x0crac{1}{8}", "لـ 1/3 و 1/8"),
    ],
    "a5482fdc-85d4-47c4-9318-c2471d555c0f": [
        ("ل\x0crac{1}{5} و\x0crac{1}{6}", "لـ 1/5 و 1/6"),
    ],
}


def _apply(text: str, pairs: list) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def fix(session) -> list:  # noqa: ANN001
    """Applique FIXES. Retourne les items corrigés [(id, tokens_avant)]."""
    fixed = []
    for item_id, pairs in FIXES.items():
        it = session.execute(
            select(Item).where(Item.id == uuid.UUID(item_id), Item.deleted_at.is_(None))
        ).scalar_one_or_none()
        if it is None or not it.content_ar:
            continue
        tokens_before = ar_content_latin_tokens(it.content_ar)
        if not tokens_before:
            continue  # déjà corrigé (idempotent)

        old_content = dict(it.content_ar)
        new_content = {
            **old_content,
            "stem": _apply(old_content.get("stem") or "", pairs),
            "answer": _apply(old_content.get("answer") or "", pairs),
        }
        if old_content.get("options") is not None:
            new_content["options"] = [_apply(o, pairs) for o in old_content["options"]]

        remaining = ar_content_latin_tokens(new_content)
        if remaining:
            raise RuntimeError(f"{item_id} : tokens restants après correction : {remaining}")

        # réassignation (pas de mutation en place : la colonne JSON doit voir le changement)
        it.content_ar = new_content
        it.provenance = {
            **(it.provenance or {}),
            "ar_latin_token_fix": {
                "action": "ar_latin_token_fix",
                "tokens": tokens_before,
                "old_content_ar": old_content,
                "fixed_at": utcnow().isoformat(),
            },
        }
        fixed.append((item_id, tokens_before))
    session.commit()
    return fixed


def main() -> None:
    with SessionLocal(bind=make_engine()) as s:
        fixed = fix(s)
        print(f"Items corrigés : {len(fixed)}")
        for item_id, tokens in fixed:
            it = s.execute(select(Item).where(Item.id == uuid.UUID(item_id))).scalar_one()
            print(f"  ✓ {item_id}  tokens={tokens}")
            print(f"    stem AR : {it.content_ar.get('stem')!r}")


if __name__ == "__main__":
    main()
