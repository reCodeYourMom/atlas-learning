"""Démo T2.2 : génère des items réels via Groq pour une compétence seedée.

Usage :
    GROQ_API_KEY=... python scripts/generate_items_demo.py [CODE_COMPETENCE]

Pré-requis : `alembic upgrade head` + `python scripts/seed_referentiel.py`.
N'insère RIEN en base (sortie revue T2.3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.generation import generate_items
from src.llm.client import GroqClient
from src.models.base import AnswerFormat
from src.models.competency import Competency

DEFAULT_CODE = "MATH.G4.NF.ADD_LIKE_NO_SIMPLIFY"


def main() -> None:
    code = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CODE
    with SessionLocal(bind=make_engine()) as s:
        comp = s.execute(select(Competency).where(Competency.code == code)).scalar_one_or_none()
        if comp is None:
            sample = s.execute(select(Competency.code).limit(10)).scalars().all()
            print(f"Compétence '{code}' introuvable. Exemples : {sample}")
            sys.exit(1)
        print(f"Compétence : {comp.code} — {comp.label_en} (G{comp.grade}, prior={comp.difficulty_prior})\n")

        targets = [{"simplify": False}, {"simplify": True}]
        items = generate_items(comp, targets, GroqClient(), answer_format=AnswerFormat.MCQ)

    for i, it in enumerate(items, 1):
        print(f"--- Item {i}  context={it.context_tags}  status={it.status.value} ---")
        print(json.dumps(it.content_en, indent=2, ensure_ascii=False))
        print(f"provenance: {it.provenance}\n")
    print(f"{len(items)} items générés (non insérés).")


if __name__ == "__main__":
    main()
