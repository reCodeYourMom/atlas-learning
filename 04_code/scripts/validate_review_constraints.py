"""Validation T2.3 contre DATABASE_URL (vrai Postgres) — flux de revue.

Insère des items synthétiques (préfixe compétence `__VALIDATE_REVIEW__`),
exerce approve / reject / no-skip, vérifie content_ar nullable, puis nettoie.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, inspect, select

from src.db import SessionLocal, make_engine
from src.items.generation import GeneratedItem
from src.items.review import (
    InvalidTransition,
    approve,
    insert_generated_items,
    list_pending,
    promote,
    reject,
)
from src.models.base import AnswerFormat, CompetencyStatus, ItemStatus, Subject
from src.models.competency import Competency
from src.models.item import Item

PFX = "__VALIDATE_REVIEW__"


def _gen(cid):
    return [GeneratedItem(competency_id=cid,
                          content_en={"stem": f"q{i}", "options": ["1/4", "3/4"], "answer": "3/4"},
                          answer_format=AnswerFormat.MCQ, difficulty_prior=1180.0,
                          context_tags={"simplify": bool(i)}, provenance={"model": "m"})
            for i in range(2)]


def _cleanup(engine):
    with SessionLocal(bind=engine) as s:
        ids = s.execute(select(Competency.id).where(Competency.code.like(PFX + "%"))).scalars().all()
        if ids:
            s.execute(delete(Item).where(Item.competency_id.in_(ids)))
            s.execute(delete(Competency).where(Competency.id.in_(ids)))
            s.commit()


def main():
    engine = make_engine()
    print(f"Cible : {engine.url.render_as_string(hide_password=True)}  (dialect={engine.dialect.name})")
    _cleanup(engine)
    checks = []

    # content_ar nullable (migration 0003)
    col = {c["name"]: c for c in inspect(engine).get_columns("item")}["content_ar"]
    checks.append(("content_ar nullable (migration 0003)", col["nullable"] is True))

    with SessionLocal(bind=engine) as s:
        c = Competency(code=PFX + "C", label_en="x", label_ar="س", subject=Subject.MATH,
                       grade=4, difficulty_prior=1200.0, status=CompetencyStatus.ACTIVE)
        s.add(c); s.commit(); cid = c.id
        items = insert_generated_items(s, _gen(cid))
        checks.append(("insertion ai_generated + content_ar=None",
                       all(i.status == ItemStatus.AI_GENERATED and i.content_ar is None for i in items)))
        checks.append(("list_pending voit les 2", len(list_pending(s)) == 2))

        # AC1 approve
        approve(s, items[0], reviewer="nassim")
        checks.append(("AC1 approve → human_reviewed", items[0].status == ItemStatus.HUMAN_REVIEWED))

        # AC2 no skip
        try:
            promote(s, items[1], ItemStatus.ACTIVE, reviewer="nassim"); skip_ok = False
        except InvalidTransition:
            skip_ok = True
        checks.append(("AC2 ai_generated → active refusé", skip_ok))

        # AC3 reject soft delete
        reject(s, items[1], reviewer="nassim", reason="ambigu")
        iid = items[1].id
        still = s.execute(select(Item).where(Item.id == iid)).scalar_one_or_none()
        checks.append(("AC3 reject = soft delete (non détruit)",
                       still is not None and still.deleted_at is not None))

        # AC4 reviewer dans provenance
        checks.append(("AC4 provenance reviewer enregistré",
                       items[0].provenance.get("reviewer") == "nassim"))

    _cleanup(engine)

    print()
    ok_all = True
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}"); ok_all = ok_all and ok
    print()
    if not ok_all:
        print("VALIDATION ÉCHOUÉE"); sys.exit(1)
    print(f"{len(checks)}/{len(checks)} vérifs T2.3 OK sur {engine.dialect.name}")


if __name__ == "__main__":
    main()
