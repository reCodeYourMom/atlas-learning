"""Tests T1.1 — contraintes des modèles du référentiel. 1 test = 1 AC du backlog.

Tourne sur SQLite fichier temporaire (FK activées via src.db.make_engine).
Les contraintes prouvées ici sont identiques en Postgres (Oracle UAE).
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db import active, make_engine
from src.models.base import Base, CompetencyStatus, EdgeType, Subject
from src.models.competency import Competency, CompetencyPrerequisite


def _fresh_session() -> Session:
    engine = make_engine("sqlite://")  # mémoire, FK ON
    Base.metadata.create_all(engine)
    return Session(engine)


def _competency(code: str) -> Competency:
    return Competency(
        code=code,
        label_en="x",
        label_ar="س",
        subject=Subject.MATH,
        grade=4,
        difficulty_prior=1200.0,
        status=CompetencyStatus.ACTIVE,
    )


def test_ac2_duplicate_code_rejected():
    # AC2 : code dupliqué => violation contrainte unique
    s = _fresh_session()
    s.add(_competency("MATH.G4.NF.DUP"))
    s.commit()
    s.add(_competency("MATH.G4.NF.DUP"))
    try:
        s.commit()
        assert False, "le code dupliqué aurait dû être rejeté"
    except IntegrityError:
        s.rollback()


def test_ac3_self_loop_rejected():
    # AC3 : arête (A, A) => rejetée par le CheckConstraint ck_no_self_loop
    s = _fresh_session()
    a = _competency("MATH.G4.NF.A")
    s.add(a)
    s.commit()
    s.add(
        CompetencyPrerequisite(
            source_id=a.id, target_id=a.id,
            edge_type=EdgeType.HARD, correlation_strength=0.5,
        )
    )
    try:
        s.commit()
        assert False, "l'auto-référence aurait dû être rejetée"
    except IntegrityError:
        s.rollback()


def test_ac4_missing_source_fk_rejected():
    # AC4 : source_id inexistant => violation FK
    s = _fresh_session()
    b = _competency("MATH.G4.NF.B")
    s.add(b)
    s.commit()
    s.add(
        CompetencyPrerequisite(
            source_id=uuid.uuid4(),  # n'existe pas
            target_id=b.id,
            edge_type=EdgeType.HARD, correlation_strength=0.5,
        )
    )
    try:
        s.commit()
        assert False, "la FK manquante aurait dû être rejetée"
    except IntegrityError:
        s.rollback()


def test_ac5_soft_delete_hidden_by_default():
    # AC5 : deleted_at renseigné => ligne en base mais absente de la requête « par défaut »
    from datetime import datetime

    s = _fresh_session()
    c = _competency("MATH.G4.NF.SOFT")
    s.add(c)
    s.commit()

    c.deleted_at = datetime(2026, 1, 1)
    s.commit()

    total = s.execute(select(func.count()).select_from(Competency)).scalar_one()
    visible = s.execute(active(Competency)).scalars().all()
    assert total == 1, "la ligne soft-deleted doit rester en base"
    assert visible == [], "la requête par défaut ne doit pas retourner la ligne soft-deleted"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
