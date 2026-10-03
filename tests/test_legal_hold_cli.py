"""Tests de la CLI legal hold (scripts/legal_hold.py, avis juridique 2026-07-08).

Vérifie que set/clear posent/lèvent le hold, exigent une cible unique, écrivent un
AuditLog, et que la levée est bien un no-op journalisé-free si rien n'était posé.
"""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from scripts.legal_hold import clear_hold, set_hold
from src.models import competency as _c, item as _i, measurement as _m, org as _o, session as _se  # noqa: F401,E501
from src.models.audit import AuditLog
from src.models.base import Base
from src.models.measurement import School, Student


def _engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    return engine


def _seed(engine):
    s = Session(bind=engine)
    school = School(name="S"); s.add(school); s.flush()
    st = Student(school_id=school.id, external_ref="A"); s.add(st); s.commit()
    ids = dict(school=school.id, student=st.id)
    s.close()
    return ids


def _args(**kw):
    base = dict(student=None, school=None, reason=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_set_hold_on_student_and_audit():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        set_hold(s, _args(student=str(ids["student"]), reason="litige #7"))
    with Session(bind=engine) as s:
        st = s.get(Student, ids["student"])
        assert st.legal_hold is not None and st.legal_hold_reason == "litige #7"
        a = s.execute(select(AuditLog).where(AuditLog.action == "legal_hold.set")).scalar_one()
        assert a.details["reason"] == "litige #7"


def test_clear_hold_on_school():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        set_hold(s, _args(school=str(ids["school"]), reason="instruction controller"))
    with Session(bind=engine) as s:
        clear_hold(s, _args(school=str(ids["school"])))
    with Session(bind=engine) as s:
        assert s.get(School, ids["school"]).legal_hold is None
        actions = {a.action for a in s.execute(select(AuditLog)).scalars()}
        assert {"legal_hold.set", "legal_hold.clear"} <= actions


def test_requires_exactly_one_target():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        with pytest.raises(SystemExit):                          # ni --student ni --school
            set_hold(s, _args(reason="x"))
        with pytest.raises(SystemExit):                          # les deux à la fois
            set_hold(s, _args(student=str(ids["student"]),
                              school=str(ids["school"]), reason="x"))


def test_clear_is_noop_when_not_held():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        clear_hold(s, _args(student=str(ids["student"])))        # rien posé
    with Session(bind=engine) as s:
        assert s.execute(select(AuditLog)).scalars().all() == []  # aucun audit pour un no-op
