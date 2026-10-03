"""/demo/login — le SEUL chemin d'authentification de la stack de démo, jusqu'ici sans test.

Trois verrous (secret posé, env non-prod, compte existant), message d'erreur unique,
audit de chaque tentative, et anti-bruteforce (10 échecs / 10 min par IP et par email → 429).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api import app as app_module
from src.api.app import app, get_db
from src.models import competency, item, measurement, org, session as _se, audit  # noqa: F401
from src.models.audit import AuditLog
from src.models.base import Base, Role
from src.models.org import AppUser, Membership
from src.rbac import auth as auth_module


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    u = AppUser(email="director@alnoor.demo"); s.add(u); s.flush()
    s.add(Membership(user_id=u.id, role=Role.PED_ADMIN))
    gone = AppUser(email="gone@alnoor.demo", is_active=False); s.add(gone)
    s.commit()
    app.dependency_overrides[get_db] = lambda: Session(bind=engine)
    monkeypatch.setenv("ATLAS_ENV", "demo")
    monkeypatch.setenv("DEMO_LOGIN_PASSWORD", "Atlas-secret")
    app_module._demo_login_failures.clear()
    yield TestClient(app), engine
    app.dependency_overrides.clear()
    app_module._demo_login_failures.clear()


def _login(c, email, pwd="Atlas-secret"):
    return c.post("/demo/login", json={"email": email, "password": pwd})


def test_happy_path_opens_session_and_audits(client):
    c, engine = client
    r = _login(c, "Director@alnoor.demo ")   # casse/espaces tolérés
    assert r.status_code == 200 and r.json()["token"]
    me = c.get("/me", headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert me.status_code == 200 and "ped_admin" in me.json()["roles"]
    with Session(bind=engine) as s:
        actions = [a.action for a in s.execute(select(AuditLog)).scalars()]
    assert "auth.demo_login" in actions


def test_single_error_message_for_unknown_email_or_bad_password(client):
    c, _ = client
    a = _login(c, "nobody@alnoor.demo")
    b = _login(c, "director@alnoor.demo", "wrong")
    d = _login(c, "gone@alnoor.demo")           # compte désactivé
    assert a.status_code == b.status_code == d.status_code == 401
    assert a.json()["detail"] == b.json()["detail"] == d.json()["detail"]


def test_closed_in_prod_and_without_secret(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv("ATLAS_ENV", "prod")
    monkeypatch.setenv("AUTH_SECRET", "x" * 32)
    assert _login(c, "director@alnoor.demo").status_code == 404
    monkeypatch.setenv("ATLAS_ENV", "demo")
    monkeypatch.delenv("DEMO_LOGIN_PASSWORD")
    assert _login(c, "director@alnoor.demo").status_code == 404
    # et /auth/providers n'annonce plus le formulaire
    assert c.get("/auth/providers").json()["demo_login"] is False


def test_bruteforce_is_throttled(client):
    c, engine = client
    for _ in range(app_module.DEMO_LOGIN_MAX_FAILURES):
        assert _login(c, "director@alnoor.demo", "wrong").status_code == 401
    # 11e tentative : refusée AVANT toute comparaison, même avec le bon mot de passe
    r = _login(c, "director@alnoor.demo")
    assert r.status_code == 429
    with Session(bind=engine) as s:
        actions = [a.action for a in s.execute(select(AuditLog)).scalars()]
    assert "auth.demo_login_throttled" in actions
    # la fenêtre expirée libère l'accès
    now = 10_000_000.0
    for k in list(app_module._demo_login_failures):
        app_module._demo_login_failures[k] = [now - app_module.DEMO_LOGIN_WINDOW_S - 1]
    assert _login(c, "director@alnoor.demo").status_code == 200


def test_session_ttl_is_configurable(monkeypatch):
    monkeypatch.delenv("AUTH_SESSION_TTL_S", raising=False)
    assert auth_module.session_ttl_s() == 3600
    monkeypatch.setenv("AUTH_SESSION_TTL_S", "14400")
    assert auth_module.session_ttl_s() == 14400
    monkeypatch.setenv("AUTH_SESSION_TTL_S", "999999999")   # borné à 12 h
    assert auth_module.session_ttl_s() == 12 * 3600
    monkeypatch.setenv("AUTH_SESSION_TTL_S", "abc")
    assert auth_module.session_ttl_s() == 3600
