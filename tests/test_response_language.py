"""Tests C-0 — langue servie (Response.language / AssessmentSession.locale).

Chaque réponse doit porter la langue de SA session ('en' hors session) : c'est le
prérequis des analyses DIF EN/AR du pilote (journal append-only, pas de backfill).
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.api.session_service import start_session
from src.engine.service import on_response
from src.models import competency, curriculum, item, measurement, org, session as _se, audit  # noqa: F401
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, ResponseLanguage, Role, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import Response, School, Student
from src.models.org import AppUser, Membership
from src.models.session import AssessmentSession
from src.rbac.auth import make_token

ANSWER = "3/4"
CONTENT = {"stem": "1/4 + 2/4 = ?", "options": ["1/4", "3/4"], "answer": ANSWER}
CONTENT_AR = {"stem": "١/٤ + ٢/٤ = ؟", "options": ["1/4", "3/4"], "answer": ANSWER}


def _client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    seed = Session(bind=engine)
    school = School(name="S"); seed.add(school); seed.flush()
    student = Student(school_id=school.id); seed.add(student)
    su = AppUser(email="su@x.io"); seed.add(su); seed.flush()
    seed.add(Membership(user_id=su.id, role=Role.SUPER_ADMIN))
    comp = Competency(code="X.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    seed.add(comp); seed.flush()
    it = Item(competency_id=comp.id, content_en=dict(CONTENT), content_ar=dict(CONTENT_AR),
              answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0, difficulty_elo=1500.0,
              status=ItemStatus.ACTIVE)
    seed.add(it); seed.commit()
    ids = dict(school=school.id, student=student.id, item=it.id, token=make_token(str(su.id)))
    seed.close()
    app.dependency_overrides[get_db] = lambda: Session(bind=engine)
    return TestClient(app), engine, ids


def _h(ids):
    return {"Authorization": f"Bearer {ids['token']}"}


def test_response_porte_la_locale_de_sa_session():
    # Session démarrée en 'ar' → la session stocke la locale ET chaque réponse en hérite.
    client, engine, ids = _client()
    r = client.post("/sessions", json={"student_id": str(ids["student"]), "locale": "ar"},
                    headers=_h(ids))
    assert r.status_code == 200 and r.json()["locale"] == "ar"
    sid = r.json()["session_id"]
    item_id = client.get(f"/sessions/{sid}/next-item", headers=_h(ids)).json()["item_id"]
    r = client.post(f"/sessions/{sid}/responses",
                    json={"item_id": item_id, "selected": ANSWER, "lang": "ar"}, headers=_h(ids))
    assert r.status_code == 200
    with Session(bind=engine) as s:
        assert s.get(AssessmentSession, uuid.UUID(sid)).locale == ResponseLanguage.AR
        resp = s.execute(select(Response)).scalar_one()
        assert resp.language == ResponseLanguage.AR
    app.dependency_overrides.clear()


def test_locale_absente_defaut_en():
    # Rétrocompat : sans `locale` dans le POST, session et réponses restent 'en'.
    client, engine, ids = _client()
    sid = client.post("/sessions", json={"student_id": str(ids["student"])},
                      headers=_h(ids)).json()["session_id"]
    item_id = client.get(f"/sessions/{sid}/next-item", headers=_h(ids)).json()["item_id"]
    client.post(f"/sessions/{sid}/responses",
                json={"item_id": item_id, "selected": ANSWER}, headers=_h(ids))
    with Session(bind=engine) as s:
        assert s.get(AssessmentSession, uuid.UUID(sid)).locale == ResponseLanguage.EN
        assert s.execute(select(Response)).scalar_one().language == ResponseLanguage.EN
    app.dependency_overrides.clear()


def test_hors_session_defaut_en():
    # Moteur appelé directement (seeds, scripts) sans session : la réponse porte 'en'.
    client, engine, ids = _client()
    with Session(bind=engine) as s:
        resp = on_response(s, student_id=ids["student"], item_id=ids["item"],
                           is_correct=True, school_id=ids["school"])
        assert resp.session_id is None and resp.language == ResponseLanguage.EN
    app.dependency_overrides.clear()


def test_locale_invalide_rejetee_au_demarrage():
    # API : 422 pydantic (Literal) — et la validation vit AUSSI dans start_session
    # (appelable hors HTTP) : ValueError, jamais une écriture silencieuse.
    client, engine, ids = _client()
    r = client.post("/sessions", json={"student_id": str(ids["student"]), "locale": "fr"},
                    headers=_h(ids))
    assert r.status_code == 422
    with Session(bind=engine) as s:
        with pytest.raises(ValueError):
            start_session(s, student_id=ids["student"], school_id=ids["school"], locale="fr")
        s.rollback()
        assert s.execute(select(AssessmentSession)).first() is None  # rien n'a été créé
    app.dependency_overrides.clear()
