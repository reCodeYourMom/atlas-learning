"""Mouvement 01 (bench Alef→Atlas) — profondeur parent/enseignant.

Couvre :
  - digest hebdomadaire enseignant (activité de la semaine + lacunes émergentes + priorité #1) ;
  - « prochaine étape » côté parent : cause racine + activité maison ~10 min, sans PII ni réponse.
Isolation RBAC réutilisée du flux existant (cf. test_views.py).
"""
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.api.views_service import class_digest
from src.models import competency, item, measurement, org, session as _se  # noqa: F401
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, EdgeType, ItemStatus, Role, Subject, WeightSource,
)
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Classroom, Membership, ParentStudent, TeacherClassroom
from src.notify.templates import teacher_digest_email
from src.rbac.auth import make_token


def _comp(code):
    return Competency(code=code, label_en=code, label_ar=f"ع{code}", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)


def _ability(student_id, comp_id, school_id, elo, *, when=None, n=5):
    return StudentCompetencyAbility(student_id=student_id, competency_id=comp_id, school_id=school_id,
                                    ability_elo=elo, n_direct=n, confidence=0.6, last_measured_at=when)


def _item(comp_id, stem_en="What is 1/2 + 1/4?", stem_ar="ما هو ١/٢ + ١/٤؟"):
    return Item(competency_id=comp_id, answer_format=AnswerFormat.MCQ, difficulty_prior=1400.0,
                status=ItemStatus.ACTIVE,
                content_en={"stem": stem_en, "options": ["3/4", "2/6"], "answer": "3/4"},
                content_ar={"stem": stem_ar, "options": ["٣/٤", "٢/٦"], "answer": "٣/٤"})


def _setup(now=None):
    now = now or datetime.now()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    sa_ = School(name="A"); s.add(sa_); s.flush()
    c1 = Classroom(school_id=sa_.id, name="4A"); s.add(c1); s.flush()
    # chaîne A(root) <- B <- C
    A, B, C = _comp("M.A"), _comp("M.B"), _comp("M.C")
    s.add_all([A, B, C]); s.flush()
    s.add(CompetencyPrerequisite(source_id=B.id, target_id=C.id, edge_type=EdgeType.HARD,
                                 correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    s.add(CompetencyPrerequisite(source_id=A.id, target_id=B.id, edge_type=EdgeType.HARD,
                                 correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    bx = _item(B.id); s.add(bx); s.flush()  # exercice servable pour l'activité maison (cause racine B)

    recent = now - timedelta(days=2)   # dans la fenêtre 7j
    old = now - timedelta(days=30)     # hors fenêtre
    students = []
    for i in range(3):
        st = Student(school_id=sa_.id, classroom_id=c1.id, external_ref=f"S{i}")
        s.add(st); s.flush(); students.append(st)
        s.add(_ability(st.id, A.id, sa_.id, 1800, when=old))    # racine maîtrisée
        s.add(_ability(st.id, B.id, sa_.id, 1200, when=recent)) # lacune (re)mesurée cette semaine → émergente
        s.add(_ability(st.id, C.id, sa_.id, 1200, when=old))    # lacune ancienne (non émergente)
        # activité : 1 réponse récente pour 2 élèves sur 3
        if i < 2:
            s.add(Response(school_id=sa_.id, student_id=st.id, item_id=bx.id,
                           competency_id=B.id, is_correct=(i == 0), created_at=recent))

    # parent du 1er élève + enseignant de la classe
    parent = AppUser(email="p@x.io"); teacher = AppUser(email="t@x.io")
    s.add_all([parent, teacher]); s.flush()
    s.add_all([
        Membership(user_id=teacher.id, role=Role.TEACHER, school_id=sa_.id),
        TeacherClassroom(user_id=teacher.id, classroom_id=c1.id),
        Membership(user_id=parent.id, role=Role.PARENT, school_id=sa_.id),
        ParentStudent(user_id=parent.id, student_id=students[0].id, source="staff"),
    ])
    s.commit()
    ids = dict(school=sa_.id, c1=c1.id, teacher=teacher.id, parent=parent.id,
               child=students[0].id, rootB="M.B", now=now)
    app.dependency_overrides[get_db] = lambda: s
    return TestClient(app), ids, s


def _auth(uid):
    return {"Authorization": f"Bearer {make_token(str(uid))}"}


def test_digest_activity_and_emerging_gaps():
    client, ids, s = _setup()
    d = class_digest(s, ids["c1"], now=ids["now"])
    assert d["n_students"] == 3
    assert d["n_active_students"] == 2          # 2 élèves ont répondu cette semaine
    assert d["n_responses"] == 2
    # B (re)mesurée cette semaine pour 3 élèves → lacune émergente #1 ; C ancienne → exclue
    assert d["emerging_gaps"], "au moins une lacune émergente attendue"
    assert d["emerging_gaps"][0]["root_cause"] == ids["rootB"]
    assert d["emerging_gaps"][0]["student_count"] == 3
    assert all(g["root_cause"] != "M.C" for g in d["emerging_gaps"])  # ancienne lacune non émergente
    assert d["top_priority"]["root_cause"] == ids["rootB"]
    app.dependency_overrides.clear()


def test_digest_endpoint_rbac():
    client, ids, s = _setup()
    assert client.get(f"/classrooms/{ids['c1']}/digest", headers=_auth(ids["teacher"])).status_code == 200
    assert client.get(f"/classrooms/{ids['c1']}/digest").status_code == 401  # sans jeton
    # un parent n'a pas accès à la vue classe enseignant
    assert client.get(f"/classrooms/{ids['c1']}/digest", headers=_auth(ids["parent"])).status_code == 403
    app.dependency_overrides.clear()


def test_parent_next_step_has_home_activity_no_pii():
    client, ids, s = _setup()
    data = client.get(f"/students/{ids['child']}/trajectory", headers=_auth(ids["parent"])).json()
    ns = data["next_step"]
    assert ns is not None
    assert ns["competency_code"] == ids["rootB"]      # cible la cause racine
    assert ns["minutes"] == 10
    assert ns["activity"] is not None
    assert ns["activity"]["example_en"] and ns["activity"]["example_ar"]  # bilingue
    # l'exercice ne fuit JAMAIS la réponse, ni aucune PII (id élève brut)
    blob = json.dumps(ns)
    assert "answer" not in ns["activity"]
    assert "3/4" not in blob and "٣/٤" not in blob
    app.dependency_overrides.clear()


def test_email_digest_is_bilingual_and_aggregate_only():
    client, ids, s = _setup()
    d = class_digest(s, ids["c1"], now=ids["now"])
    subject, html, text = teacher_digest_email("4A", d)
    assert "this week" in subject.lower()
    assert 'dir="rtl"' in html                 # bloc arabe présent
    assert "M.A" in html or "ع" in html        # libellé compétence (pas de PII élève)
    assert str(d["n_active_students"]) in text
    assert "S0" not in html and "S1" not in html  # aucune référence élève
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
