"""Périmètre d'ÉCRITURE (revue 2026-09-20).

Le contrôle `can_access_student` sert à VOIR un élève. Il incluait le parent — et les
endpoints de session (ouvrir, répondre) ne vérifiaient rien de plus : un parent pouvait
répondre à la place de son enfant et déplacer son Elo, contre le PRD (« Parent — lecture
seule : ne réalise aucune activité »). Idem pour la gestion des tuteurs, et pour le
référentiel (priors, poids) exposé à tout compte connecté.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.models import competency, item, measurement, org, session as _se, audit  # noqa: F401
from src.models.base import AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import School, Student
from src.models.org import AppUser, Classroom, Membership, ParentStudent, StudentClassroom, TeacherClassroom
from src.rbac.auth import make_token

CONTENT = {"stem": "1/4 + 2/4 = ?", "options": ["1/4", "3/4"], "answer": "3/4"}


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    school = School(name="S"); s.add(school); s.flush()
    cls = Classroom(school_id=school.id, name="4A"); s.add(cls); s.flush()
    su = AppUser(email="student@x.io"); pu = AppUser(email="parent@x.io")
    tu = AppUser(email="teacher@x.io"); s.add_all([su, pu, tu]); s.flush()
    st = Student(school_id=school.id, classroom_id=cls.id, user_id=su.id); s.add(st); s.flush()
    s.add_all([
        StudentClassroom(student_id=st.id, classroom_id=cls.id),
        Membership(user_id=su.id, role=Role.STUDENT),
        Membership(user_id=pu.id, role=Role.PARENT, organization_id=None),
        ParentStudent(user_id=pu.id, student_id=st.id, source="staff"),
        Membership(user_id=tu.id, role=Role.TEACHER, school_id=school.id),
        TeacherClassroom(user_id=tu.id, classroom_id=cls.id),
    ])
    comp = Competency(code="X.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add(comp); s.flush()
    s.add(Item(competency_id=comp.id, content_en=dict(CONTENT), content_ar=None,
               answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0, difficulty_elo=1500.0,
               status=ItemStatus.ACTIVE))
    s.commit()
    ids = dict(student=st.id, tok_student=make_token(str(su.id)),
               tok_parent=make_token(str(pu.id)), tok_teacher=make_token(str(tu.id)))
    app.dependency_overrides[get_db] = lambda: Session(bind=engine)
    return TestClient(app), ids


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_parent_reads_but_never_acts():
    client, ids = _setup()
    sid = str(ids["student"])
    # lecture : OK
    assert client.get(f"/students/{sid}/profile", headers=_h(ids["tok_parent"])).status_code == 200
    # écriture de mesure : refusée
    r = client.post("/sessions", json={"student_id": sid}, headers=_h(ids["tok_parent"]))
    assert r.status_code == 403, r.text
    # session ouverte par l'élève : le parent ne peut ni tirer l'item ni répondre
    sess = client.post("/sessions", json={"student_id": sid}, headers=_h(ids["tok_student"])).json()
    assert client.get(f"/sessions/{sess['session_id']}/next-item",
                      headers=_h(ids["tok_parent"])).status_code == 403
    assert client.post(f"/sessions/{sess['session_id']}/responses",
                       json={"item_id": str(uuid.uuid4()), "selected": "3/4"},
                       headers=_h(ids["tok_parent"])).status_code == 403
    app.dependency_overrides.clear()


def test_student_and_teacher_can_act():
    client, ids = _setup()
    sid = str(ids["student"])
    assert client.post("/sessions", json={"student_id": sid}, headers=_h(ids["tok_student"])).status_code == 200
    # le prof lance une session live en classe
    assert client.post("/sessions", json={"student_id": sid}, headers=_h(ids["tok_teacher"])).status_code == 200
    app.dependency_overrides.clear()


def test_guardians_are_staff_only():
    client, ids = _setup()
    sid = str(ids["student"])
    for tok in (ids["tok_parent"], ids["tok_student"]):
        assert client.get(f"/students/{sid}/guardians", headers=_h(tok)).status_code == 403
        assert client.post(f"/students/{sid}/guardians", json={"email": "x@y.io", "send_invite": False},
                           headers=_h(tok)).status_code == 403
    assert client.get(f"/students/{sid}/guardians", headers=_h(ids["tok_teacher"])).status_code == 200
    app.dependency_overrides.clear()


def test_referentiel_is_staff_only():
    client, ids = _setup()
    assert client.get("/competencies", headers=_h(ids["tok_student"])).status_code == 403
    assert client.get("/competencies", headers=_h(ids["tok_parent"])).status_code == 403
    assert client.get("/competencies", headers=_h(ids["tok_teacher"])).status_code == 200
    app.dependency_overrides.clear()
