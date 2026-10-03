"""Mouvement 03 (bench Alef→Atlas) — surfaces de preuve (l'impact comme interface).

Avant/après cohorte dérivé du journal de réponses (append-only), gains par compétence,
projection de trajectoire. Honnêteté : fenêtre explicite, effectifs faibles écartés, zéro PII.
"""
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.restitution.proof import proof_surfaces
from src.models import competency, item, measurement, org, session as _se  # noqa: F401
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Classroom, Membership
from src.rbac.auth import make_token


def _comp(code):
    return Competency(code=code, label_en=code, label_ar=f"ع{code}", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)


def _setup(now=None):
    now = now or datetime(2026, 6, 1, 12, 0, 0)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    sa_, sb = School(name="A"), School(name="B"); s.add_all([sa_, sb]); s.flush()
    c1 = Classroom(school_id=sa_.id, name="4A"); s.add(c1); s.flush()
    A = _comp("M.A"); s.add(A); s.flush()
    it = Item(competency_id=A.id, answer_format=AnswerFormat.MCQ, difficulty_prior=1400.0,
              status=ItemStatus.ACTIVE,
              content_en={"stem": "q", "options": ["1", "2"], "answer": "1"})
    s.add(it); s.flush()

    old = now - timedelta(days=45)   # période AVANT (hors fenêtre 30j)
    recent = now - timedelta(days=5) # période APRÈS (dans la fenêtre)
    students = []
    for i in range(3):
        st = Student(school_id=sa_.id, classroom_id=c1.id, external_ref=f"S{i}")
        s.add(st); s.flush(); students.append(st)
        s.add(StudentCompetencyAbility(student_id=st.id, competency_id=A.id, school_id=sa_.id,
                                       ability_elo=1500.0, n_direct=5, confidence=0.6))
        # AVANT : 2 réponses, 1 correcte (50 %)
        s.add(Response(school_id=sa_.id, student_id=st.id, item_id=it.id, competency_id=A.id,
                       is_correct=True, created_at=old))
        s.add(Response(school_id=sa_.id, student_id=st.id, item_id=it.id, competency_id=A.id,
                       is_correct=False, created_at=old))
        # APRÈS : 2 réponses, 2 correctes (100 %) → gain net
        s.add(Response(school_id=sa_.id, student_id=st.id, item_id=it.id, competency_id=A.id,
                       is_correct=True, created_at=recent))
        s.add(Response(school_id=sa_.id, student_id=st.id, item_id=it.id, competency_id=A.id,
                       is_correct=True, created_at=recent))

    admin = AppUser(email="admin@a.io"); s.add(admin); s.flush()
    s.add(Membership(user_id=admin.id, role=Role.PED_ADMIN, school_id=sa_.id))
    s.commit()
    ids = dict(schoolA=sa_.id, schoolB=sb.id, admin=admin.id, now=now, comp="M.A")
    app.dependency_overrides[get_db] = lambda: s
    return TestClient(app), ids, s


def _auth(uid):
    return {"Authorization": f"Bearer {make_token(str(uid))}"}


def test_before_after_cohort_gain():
    client, ids, s = _setup()
    p = proof_surfaces(s, ids["schoolA"], now=ids["now"], window_days=30)
    assert p["cohort"]["before"] == 0.5   # 50 % avant
    assert p["cohort"]["after"] == 1.0     # 100 % après
    assert p["cohort"]["delta"] == 0.5     # +50 pts
    assert p["cohort"]["n_before"] == 6 and p["cohort"]["n_after"] == 6
    app.dependency_overrides.clear()


def test_gains_by_competency_sorted():
    client, ids, s = _setup()
    p = proof_surfaces(s, ids["schoolA"], now=ids["now"], window_days=30)
    assert p["gains"], "un gain par compétence attendu"
    g0 = p["gains"][0]
    assert g0["competency_code"] == ids["comp"]
    assert g0["before"] == 0.5 and g0["after"] == 1.0 and g0["delta"] == 0.5
    app.dependency_overrides.clear()


def test_low_n_competency_excluded():
    client, ids, s = _setup()
    # min_n élevé → la compétence (6 réponses/période) doit être écartée (honnêteté)
    p = proof_surfaces(s, ids["schoolA"], now=ids["now"], window_days=30, min_n=10)
    assert p["gains"] == []
    app.dependency_overrides.clear()


def test_trajectory_distribution():
    client, ids, s = _setup()
    p = proof_surfaces(s, ids["schoolA"], now=ids["now"], window_days=30)
    total = sum(b["n_students"] for b in p["trajectory"])
    assert total == 3                       # 3 élèves répartis par niveau
    assert any(b["level"] == "G4" for b in p["trajectory"])  # ability 1500 → G4
    app.dependency_overrides.clear()


def test_endpoint_rbac_and_no_pii():
    client, ids, s = _setup()
    r = client.get(f"/schools/{ids['schoolA']}/proof", headers=_auth(ids["admin"]))
    assert r.status_code == 200, r.text
    assert "student_id" not in json.dumps(r.json())   # aucune PII élève
    assert "S0" not in json.dumps(r.json())
    # isolation tenant : admin école A ne voit pas école B
    assert client.get(f"/schools/{ids['schoolB']}/proof", headers=_auth(ids["admin"])).status_code == 403
    assert client.get(f"/schools/{ids['schoolA']}/proof").status_code == 401
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
