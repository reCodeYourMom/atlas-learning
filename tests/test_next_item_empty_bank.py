"""Tests revue 2026-07-07 — GET next-item avec banque vide sur la cible.

Avant : pick_competency faisait min([]) → ValueError → HTTP 500. Après : la compétence
sans item actif est skippée ; si AUCUNE cible n'a d'item, la session se termine
proprement par le mécanisme d'arrêt standard (done=True, reason="no_items").
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
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, EdgeType, ItemStatus, Role, Subject, WeightSource,
)
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Membership
from src.models.session import AssessmentSession
from src.rbac.auth import make_token

CONTENT = {"stem": "1/4 + 2/4 = ?", "options": ["1/4", "3/4"], "answer": "3/4"}


def _client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    seed = Session(bind=engine)
    school = School(name="S"); seed.add(school); seed.flush()
    student = Student(school_id=school.id); seed.add(student)
    su = AppUser(email="su@x.io"); seed.add(su); seed.flush()
    seed.add(Membership(user_id=su.id, role=Role.SUPER_ADMIN))
    # a : compétence SANS item ; b : compétence avec item actif ; a prérequis HARD de b
    a = Competency(code="X.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                   difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    b = Competency(code="X.B", label_en="b", label_ar="ب", subject=Subject.MATH, grade=4,
                   difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    seed.add_all([a, b]); seed.flush()
    seed.add(CompetencyPrerequisite(source_id=a.id, target_id=b.id, edge_type=EdgeType.HARD,
                                    correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    active = Item(competency_id=b.id, content_en=dict(CONTENT), content_ar=None,
                  answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0, difficulty_elo=1500.0,
                  status=ItemStatus.ACTIVE)
    seed.add(active); seed.commit()
    ids = dict(school=school.id, student=student.id, comp_a=a.id, comp_b=b.id,
               active=active.id, token=make_token(str(su.id)))
    seed.close()
    app.dependency_overrides[get_db] = lambda: Session(bind=engine)
    return TestClient(app), engine, ids


def _h(ids):
    return {"Authorization": f"Bearer {ids['token']}"}


def _start(client, ids, targets=None) -> str:
    body = {"student_id": str(ids["student"])}
    if targets:
        body["target_competency_ids"] = [str(t) for t in targets]
    return client.post("/sessions", json=body, headers=_h(ids)).json()["session_id"]


def test_next_item_target_without_items_ends_cleanly():
    # cible = X.A (banque vide) → pas de 500 : fin de session standard "no_items"
    client, engine, ids = _client()
    sid = _start(client, ids, targets=[ids["comp_a"]])
    r = client.get(f"/sessions/{sid}/next-item", headers=_h(ids))
    assert r.status_code == 200                       # avant la revue : ValueError → 500
    assert r.json() == {"done": True, "reason": "no_items"}
    with Session(bind=engine) as s:
        sess = s.get(AssessmentSession, uuid.UUID(sid))
        assert sess.status == "completed" and sess.stop_reason == "no_items"
    app.dependency_overrides.clear()


def test_next_item_after_no_items_finish_stays_done():
    # rappeler next-item sur la session close → même réponse de fin, toujours pas d'erreur
    client, engine, ids = _client()
    sid = _start(client, ids, targets=[ids["comp_a"]])
    client.get(f"/sessions/{sid}/next-item", headers=_h(ids))
    again = client.get(f"/sessions/{sid}/next-item", headers=_h(ids))
    assert again.status_code == 200 and again.json() == {"done": True, "reason": "no_items"}
    app.dependency_overrides.clear()


def test_redirect_hard_prereq_without_items_serves_target():
    # prérequis HARD X.A clairement échoué (1100) mais SANS item → on sert la cible X.B
    # au lieu de clore la session (ou de planter) : la mesure continue
    client, engine, ids = _client()
    with Session(bind=engine) as s:
        s.add(StudentCompetencyAbility(student_id=ids["student"], competency_id=ids["comp_a"],
                                       school_id=ids["school"], ability_elo=1100.0,
                                       n_direct=5, confidence=0.8))
        s.commit()
    sid = _start(client, ids)
    data = client.get(f"/sessions/{sid}/next-item", headers=_h(ids)).json()
    assert data["done"] is False
    assert data["competency_id"] == str(ids["comp_b"])
    assert data["item_id"] == str(ids["active"])
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
