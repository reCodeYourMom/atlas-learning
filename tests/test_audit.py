"""Tests audit log (must-have V1 sécu) : journalisation accès & actions."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.audit import log_action
from src.models import competency, item, measurement, org, session as _se, audit  # noqa: F401
from src.models.audit import AuditLog
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Classroom, Membership, TeacherClassroom
from src.rbac.auth import make_token

ANSWER = "3/4"
CONTENT = {"stem": "1/4 + 2/4 = ?", "options": ["1/4", "3/4"], "answer": ANSWER}


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    school = School(name="A"); s.add(school); s.flush()
    cls = Classroom(school_id=school.id, name="4A"); s.add(cls); s.flush()
    student = Student(school_id=school.id, classroom_id=cls.id); s.add(student)
    comp = Competency(code="M.C", label_en="c", label_ar="ج", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE); s.add(comp); s.flush()
    it = Item(competency_id=comp.id, content_en=dict(CONTENT), content_ar=None,
              answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0, difficulty_elo=1500.0,
              status=ItemStatus.ACTIVE); s.add(it)
    teacher = AppUser(email="t@x.io"); su = AppUser(email="su@x.io"); s.add_all([teacher, su]); s.flush()
    s.add_all([Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id),
               Membership(user_id=su.id, role=Role.SUPER_ADMIN),
               TeacherClassroom(user_id=teacher.id, classroom_id=cls.id),
               StudentCompetencyAbility(student_id=student.id, competency_id=comp.id,
                                        school_id=school.id, ability_elo=1200, n_direct=3, confidence=0.3)])
    s.commit()
    ids = dict(engine=engine, school=school.id, student=student.id, item=it.id,
               cls=cls.id, teacher=teacher.id,
               token=make_token(str(su.id)))
    app.dependency_overrides[get_db] = lambda: s
    return TestClient(app), s, ids


def _h(ids):
    return {"Authorization": f"Bearer {ids['token']}"}


def test_log_action_unit():
    _, s, ids = _setup()
    log_action(s, action="test.ping", school_id=ids["school"], details={"k": "v"})
    s.commit()
    e = s.execute(select(AuditLog).where(AuditLog.action == "test.ping")).scalar_one()
    assert e.school_id == ids["school"] and e.details == {"k": "v"}
    app.dependency_overrides.clear()


def test_session_create_is_audited():
    client, s, ids = _setup()
    client.post("/sessions", json={"student_id": str(ids["student"])}, headers=_h(ids))
    e = s.execute(select(AuditLog).where(AuditLog.action == "session.create")).scalar_one()
    assert e.school_id == ids["school"] and e.resource_type == "session"
    app.dependency_overrides.clear()


def test_response_submit_is_audited():
    client, s, ids = _setup()
    sid = client.post("/sessions", json={"student_id": str(ids["student"])},
                      headers=_h(ids)).json()["session_id"]
    item_id = client.get(f"/sessions/{sid}/next-item", headers=_h(ids)).json()["item_id"]
    client.post(f"/sessions/{sid}/responses", json={"item_id": item_id, "selected": ANSWER}, headers=_h(ids))
    n = s.execute(select(func.count()).select_from(AuditLog).where(AuditLog.action == "response.submit")).scalar_one()
    assert n == 1
    app.dependency_overrides.clear()


def test_data_access_is_audited_with_user():
    client, s, ids = _setup()
    headers = {"Authorization": f"Bearer {make_token(str(ids['teacher']))}"}
    client.get(f"/classrooms/{ids['cls']}/gaps", headers=headers)
    e = s.execute(select(AuditLog).where(AuditLog.action == "classroom.view_gaps")).scalar_one()
    assert e.user_id == ids["teacher"] and e.school_id == ids["school"]
    app.dependency_overrides.clear()


def test_audit_entries_carry_tenant():
    client, s, ids = _setup()
    client.post("/sessions", json={"student_id": str(ids["student"])}, headers=_h(ids))
    for e in s.execute(select(AuditLog)).scalars():
        assert e.school_id is not None        # traçabilité tenant
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
