"""Validation des contraintes T1.1 contre la DB pointée par DATABASE_URL.

Sert à prouver les ACs sur un VRAI Postgres (enums natifs, FK, checks),
là où les tests unitaires tournent sur SQLite. À lancer après
`alembic upgrade head` sur la cible.

Codes préfixés `__VALIDATE__` puis nettoyés : n'altère pas les données seedées.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, DataError

from src.db import SessionLocal, active, make_engine
from src.models.base import CompetencyStatus, EdgeType, Subject
from src.models.competency import Competency, CompetencyPrerequisite

PFX = "__VALIDATE__"


def _comp(code: str) -> Competency:
    return Competency(
        code=PFX + code, label_en="x", label_ar="س", subject=Subject.MATH,
        grade=4, difficulty_prior=1200.0, status=CompetencyStatus.ACTIVE,
    )


def _cleanup(engine) -> None:
    with SessionLocal(bind=engine) as s:
        ids = s.execute(
            select(Competency.id).where(Competency.code.like(PFX + "%"))
        ).scalars().all()
        if ids:
            s.execute(delete(CompetencyPrerequisite).where(
                CompetencyPrerequisite.source_id.in_(ids)
                | CompetencyPrerequisite.target_id.in_(ids)
            ))
            s.execute(delete(Competency).where(Competency.id.in_(ids)))
            s.commit()


def main() -> None:
    engine = make_engine()
    print(f"Cible : {engine.url.render_as_string(hide_password=True)}  (dialect={engine.dialect.name})")
    _cleanup(engine)
    checks = []

    # AC2 — code unique
    with SessionLocal(bind=engine) as s:
        s.add(_comp("DUP")); s.commit()
        s.add(_comp("DUP"))
        try:
            s.commit(); ok = False
        except IntegrityError:
            s.rollback(); ok = True
    checks.append(("AC2 code dupliqué rejeté", ok))

    # AC3 — anti self-loop (CheckConstraint)
    with SessionLocal(bind=engine) as s:
        a = _comp("A"); s.add(a); s.commit()
        s.add(CompetencyPrerequisite(source_id=a.id, target_id=a.id,
                                     edge_type=EdgeType.HARD, correlation_strength=0.5))
        try:
            s.commit(); ok = False
        except IntegrityError:
            s.rollback(); ok = True
    checks.append(("AC3 auto-référence (A,A) rejetée", ok))

    # AC4 — FK source_id inexistant
    with SessionLocal(bind=engine) as s:
        b = _comp("B"); s.add(b); s.commit()
        s.add(CompetencyPrerequisite(source_id=uuid.uuid4(), target_id=b.id,
                                     edge_type=EdgeType.HARD, correlation_strength=0.5))
        try:
            s.commit(); ok = False
        except IntegrityError:
            s.rollback(); ok = True
    checks.append(("AC4 FK source inexistante rejetée", ok))

    # AC5 — soft delete masqué par requête par défaut
    with SessionLocal(bind=engine) as s:
        c = _comp("SOFT"); s.add(c); s.commit()
        c.deleted_at = datetime(2026, 1, 1, tzinfo=timezone.utc); s.commit()
        total = s.execute(
            select(func.count()).select_from(Competency).where(Competency.code == PFX + "SOFT")
        ).scalar_one()
        visible = s.execute(active(Competency).where(Competency.code == PFX + "SOFT")).scalars().all()
        ok = (total == 1 and visible == [])
    checks.append(("AC5 soft delete masqué par défaut", ok))

    _cleanup(engine)

    print()
    all_ok = True
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        all_ok = all_ok and ok
    print()
    if not all_ok:
        print("VALIDATION ÉCHOUÉE"); sys.exit(1)
    print(f"{len(checks)}/{len(checks)} contraintes validées sur {engine.dialect.name}")


if __name__ == "__main__":
    main()
