"""Validation des contraintes Item (T2.1) contre DATABASE_URL — vrai Postgres.

À lancer après `alembic upgrade head`. Crée/nettoie une compétence + items
préfixés `__VALIDATE_ITEM__`, ne touche pas aux données seedées.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.db import SessionLocal, make_engine
from src.models.base import AnswerFormat, CompetencyStatus, Subject
from src.models.competency import Competency
from src.models.item import Item

PFX = "__VALIDATE_ITEM__"
VALID = {"stem": "1/2 + 1/4 = ?", "options": ["3/4", "1/2"], "answer": "3/4"}


def _item(cid, **over) -> Item:
    kw = dict(competency_id=cid, content_en=dict(VALID), content_ar=dict(VALID),
              answer_format=AnswerFormat.MCQ, difficulty_prior=1180.0)
    kw.update(over)
    return Item(**kw)


def _cleanup(engine) -> None:
    with SessionLocal(bind=engine) as s:
        ids = s.execute(select(Competency.id).where(Competency.code.like(PFX + "%"))).scalars().all()
        if ids:
            s.execute(delete(Item).where(Item.competency_id.in_(ids)))
            s.execute(delete(Competency).where(Competency.id.in_(ids)))
            s.commit()


def main() -> None:
    engine = make_engine()
    print(f"Cible : {engine.url.render_as_string(hide_password=True)}  (dialect={engine.dialect.name})")
    _cleanup(engine)
    checks = []

    with SessionLocal(bind=engine) as s:
        c = Competency(code=PFX + "C", label_en="x", label_ar="س", subject=Subject.MATH,
                       grade=4, difficulty_prior=1200.0, status=CompetencyStatus.ACTIVE)
        s.add(c); s.commit()
        cid = c.id

    # AC3 — difficulty_elo = difficulty_prior à la création
    with SessionLocal(bind=engine) as s:
        it = _item(cid, difficulty_prior=1337.0); s.add(it); s.commit()
        checks.append(("AC3 difficulty_elo défaut = prior", it.difficulty_elo == 1337.0))

    # AC5 — context_tags arbitraire round-trip
    with SessionLocal(bind=engine) as s:
        tags = {"simplify": False, "denominator_max": 8, "nested": {"reps": [1, 2, 3]}}
        it = _item(cid, context_tags=tags); s.add(it); s.commit(); iid = it.id
    with SessionLocal(bind=engine) as s:
        checks.append(("AC5 context_tags JSONB round-trip", s.get(Item, iid).context_tags == tags))

    # AC4 — RESTRICT bloque la suppression d'une compétence avec item vivant
    with SessionLocal(bind=engine) as s:
        comp = s.get(Competency, cid)
        s.delete(comp)
        try:
            s.commit(); ok = False
        except IntegrityError:
            s.rollback(); ok = True
    checks.append(("AC4 FK RESTRICT bloque suppression compétence", ok))

    _cleanup(engine)

    print()
    all_ok = True
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        all_ok = all_ok and ok
    print()
    if not all_ok:
        print("VALIDATION ÉCHOUÉE"); sys.exit(1)
    print(f"{len(checks)}/{len(checks)} contraintes Item validées sur {engine.dialect.name}")


if __name__ == "__main__":
    main()
