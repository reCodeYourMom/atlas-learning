"""Tests onboarding self-service (Phase C) — service pur + flux Google complet (mocké).

Sécurité vérifiée : un compte Workspace NON-admin est refusé (anti-escalade), un compte
perso (sans `hd`) aussi. Le service est idempotent et protège le compte bootstrap.
"""
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School
from src.models.org import AppUser, Membership, Organization, TenantIntegration
from src.onboarding.service import onboard_tenant
from src.rbac import oidc
from src.rostering import google as gdir
import src.api.app as appmod


# ---------- service pur ----------

def _mem_session():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    return Session(bind=engine)


def test_onboard_creates_tenant_and_bootstrap_admin():
    s = _mem_session()
    res = onboard_tenant(s, email="IT@school.edu", domain="school.edu", customer_id="C123")
    s.commit()
    assert res.created is True
    org = s.execute(select(Organization).where(Organization.domain == "school.edu")).scalar_one()
    assert org.external_ref == "C123"
    user = s.execute(select(AppUser).where(AppUser.email == "it@school.edu")).scalar_one()
    assert user.external_ref is None  # bootstrap → protégé du déprovisioning
    roles = set(s.execute(select(Membership.role).where(Membership.user_id == user.id)).scalars())
    assert Role.IT_ADMIN in roles
    integ = s.execute(select(TenantIntegration)).scalar_one()
    assert integ.status == "pending" and integ.admin_email == "it@school.edu"
    assert s.execute(select(School).where(School.external_ref == "__default__")).scalar_one() is not None


def test_onboard_is_idempotent_and_supports_multiple_admins():
    s = _mem_session()
    onboard_tenant(s, email="it@school.edu", domain="school.edu"); s.commit()
    r2 = onboard_tenant(s, email="it@school.edu", domain="school.edu"); s.commit()  # ré-onboard
    r3 = onboard_tenant(s, email="it2@school.edu", domain="school.edu"); s.commit()  # 2ᵉ admin
    assert r2.created is False and r3.created is False
    orgs = s.execute(select(Organization).where(Organization.domain == "school.edu")).scalars().all()
    assert len(orgs) == 1
    admins = s.execute(
        select(Membership).where(Membership.role == Role.IT_ADMIN, Membership.organization_id == orgs[0].id)
    ).scalars().all()
    assert len(admins) == 2


# ---------- flux HTTP complet ----------

# Les tests HTTP remplacent des fonctions du module oidc/gdir (stubs réseau). On capture
# les originaux pour les RESTAURER après chaque test : sans ça, les stubs fuient dans
# test_oidc.py (validate_id_token/discovery monkeypatchés) et le cassent. Isolation stricte.
_ORIG = {
    "exchange_code": oidc.exchange_code,
    "validate_id_token": oidc.validate_id_token,
    "discovery": oidc.discovery,
    "get_user_self": gdir.get_user_self,
}


def _restore_oidc():
    oidc.exchange_code = _ORIG["exchange_code"]
    oidc.validate_id_token = _ORIG["validate_id_token"]
    oidc.discovery = _ORIG["discovery"]
    gdir.get_user_self = _ORIG["get_user_self"]
    oidc._disco_cache.clear()
    appmod.app.dependency_overrides.clear()


def _enable_google():
    os.environ.update({
        "OIDC_GOOGLE_CLIENT_ID": "cid", "OIDC_GOOGLE_CLIENT_SECRET": "sec",
        "WEB_BASE_URL": "http://localhost:3000",
    })
    oidc._disco_cache.clear()
    oidc.discovery = lambda p: {
        "issuer": "https://accounts.google.com",
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    }


def _client():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    return TestClient(appmod.app), engine


def _state(client):
    r = client.get("/onboarding/google/start", follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert "admin.directory.user.readonly" in q["scope"][0]   # scope admin demandé
    return q["state"][0]


def test_onboarding_admin_creates_tenant():
    _enable_google()
    try:
        oidc.exchange_code = lambda p, code, ru: {"access_token": "at", "id_token": "idt"}
        oidc.validate_id_token = lambda p, tok, nonce=None: {"email": "admin@school.edu",
                                                             "email_verified": True, "hd": "school.edu"}
        gdir.get_user_self = lambda at: {"isAdmin": True, "customerId": "C9", "primaryEmail": "admin@school.edu"}
        client, engine = _client()
        state = _state(client)
        r = client.get(f"/onboarding/google/callback?code=x&state={state}", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("http://localhost:3000/oauth/callback#token=")
        with Session(bind=engine) as s:
            org = s.execute(select(Organization).where(Organization.domain == "school.edu")).scalar_one()
            assert org.external_ref == "C9"
    finally:
        _restore_oidc()


def test_onboarding_rejects_non_admin():
    _enable_google()
    try:
        oidc.exchange_code = lambda p, code, ru: {"access_token": "at", "id_token": "idt"}
        oidc.validate_id_token = lambda p, tok, nonce=None: {"email": "student@school.edu",
                                                             "email_verified": True, "hd": "school.edu"}
        gdir.get_user_self = lambda at: {"isAdmin": False}
        client, engine = _client()
        state = _state(client)
        r = client.get(f"/onboarding/google/callback?code=x&state={state}", follow_redirects=False)
        assert "onboarding_error=not_admin" in r.headers["location"]
        with Session(bind=engine) as s:
            assert s.execute(select(Organization)).scalar_one_or_none() is None  # aucun tenant créé
    finally:
        _restore_oidc()


def test_onboarding_rejects_personal_account():
    _enable_google()
    try:
        oidc.exchange_code = lambda p, code, ru: {"access_token": "at", "id_token": "idt"}
        oidc.validate_id_token = lambda p, tok, nonce=None: {"email": "someone@gmail.com",
                                                             "email_verified": True}  # pas de hd
        gdir.get_user_self = lambda at: {"isAdmin": True}
        client, engine = _client()
        state = _state(client)
        r = client.get(f"/onboarding/google/callback?code=x&state={state}", follow_redirects=False)
        assert "onboarding_error=workspace" in r.headers["location"]
    finally:
        _restore_oidc()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
