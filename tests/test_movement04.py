"""Mouvement 04 (bench Alef→Atlas) — tuteur causal interrogeable, sous garde-fous.

Le moteur « parle » : il explique « pourquoi cet exercice » via le diagnostic cause-racine.
Garde-fous vérifiés : sortie déterministe et structurée, bilingue, AUCUNE PII (libellés seulement).
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.api.views_service import tutor_explanation
from src.models import competency, item, measurement, org, session as _se  # noqa: F401
from src.models.base import Base, CompetencyStatus, EdgeType, Role, Subject, WeightSource
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.measurement import School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Classroom, Membership, ParentStudent, TeacherClassroom
from src.rbac.auth import make_token


def _comp(code):
    return Competency(code=code, label_en=code, label_ar=f"ع{code}", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)


def _ab(student_id, comp_id, school_id, elo):
    return StudentCompetencyAbility(student_id=student_id, competency_id=comp_id, school_id=school_id,
                                    ability_elo=elo, n_direct=5, confidence=0.6)


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    sa_ = School(name="A"); s.add(sa_); s.flush()
    c1 = Classroom(school_id=sa_.id, name="4A"); s.add(c1); s.flush()
    A, B, C = _comp("M.A"), _comp("M.B"), _comp("M.C")  # A(root) <- B <- C
    s.add_all([A, B, C]); s.flush()
    s.add(CompetencyPrerequisite(source_id=B.id, target_id=C.id, edge_type=EdgeType.HARD,
                                 correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    s.add(CompetencyPrerequisite(source_id=A.id, target_id=B.id, edge_type=EdgeType.HARD,
                                 correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    st = Student(school_id=sa_.id, classroom_id=c1.id, external_ref="S0"); s.add(st); s.flush()
    s.add(_ab(st.id, A.id, sa_.id, 1800))   # racine maîtrisée
    s.add(_ab(st.id, B.id, sa_.id, 1200))   # lacune (sera la racine du diagnostic de C)
    s.add(_ab(st.id, C.id, sa_.id, 1200))   # lacune analysée

    parent = AppUser(email="p@a.io"); teacher = AppUser(email="t@a.io"); other = AppUser(email="o@a.io")
    s.add_all([parent, teacher, other]); s.flush()
    s.add_all([
        Membership(user_id=parent.id, role=Role.PARENT, school_id=sa_.id),
        ParentStudent(user_id=parent.id, student_id=st.id, source="staff"),
        Membership(user_id=teacher.id, role=Role.TEACHER, school_id=sa_.id),
        TeacherClassroom(user_id=teacher.id, classroom_id=c1.id),
        Membership(user_id=other.id, role=Role.PARENT, school_id=sa_.id),  # parent SANS lien
    ])
    s.commit()
    ids = dict(child=st.id, parent=parent.id, teacher=teacher.id, other=other.id)
    app.dependency_overrides[get_db] = lambda: s
    return TestClient(app), ids, s


def _auth(uid):
    return {"Authorization": f"Bearer {make_token(str(uid))}"}


def test_explains_root_cause_chain_bilingual():
    client, ids, s = _setup()
    out = tutor_explanation(s, ids["child"], "M.C")
    assert out["available"] is True
    assert out["is_self"] is False
    assert out["competency_code"] == "M.C"
    assert out["headline_en"] and out["headline_ar"]      # bilingue
    assert out["steps"], "au moins une étape causale"
    assert out["steps"][0]["from_code"] == "M.B"          # on part de la racine B
    assert out["steps"][-1]["to_code"] == "M.C"           # … jusqu'à la lacune C
    app.dependency_overrides.clear()


def test_self_gap_has_no_steps():
    client, ids, s = _setup()
    # B n'a qu'un prérequis A, maîtrisé → lacune « propre » (is_self)
    out = tutor_explanation(s, ids["child"], "M.B")
    assert out["available"] is True
    assert out["is_self"] is True
    assert out["steps"] == []
    app.dependency_overrides.clear()


def test_unavailable_when_mastered_or_unknown():
    client, ids, s = _setup()
    assert tutor_explanation(s, ids["child"], "M.A")["available"] is False   # maîtrisée
    assert tutor_explanation(s, ids["child"], "M.ZZ")["available"] is False  # inconnue
    app.dependency_overrides.clear()


def test_endpoint_no_pii_and_rbac():
    client, ids, s = _setup()
    r = client.get(f"/students/{ids['child']}/tutor?competency_code=M.C", headers=_auth(ids["parent"]))
    assert r.status_code == 200, r.text
    blob = json.dumps(r.json())
    assert "S0" not in blob and str(ids["child"]) not in blob  # zéro PII dans la sortie
    # le prof de la classe y a accès ; un parent non lié, non
    assert client.get(f"/students/{ids['child']}/tutor?competency_code=M.C",
                      headers=_auth(ids["teacher"])).status_code == 200
    assert client.get(f"/students/{ids['child']}/tutor?competency_code=M.C",
                      headers=_auth(ids["other"])).status_code == 403
    assert client.get(f"/students/{ids['child']}/tutor?competency_code=M.C").status_code == 401
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
