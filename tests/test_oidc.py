"""Tests SSO / OIDC (Epic 6) — config providers + flux Authorization Code + ID token.

Aucun réseau : discovery / échange de code / clé de signature JWKS sont monkeypatchés.
La validation du ID token (`validate_id_token`) tourne en CRYPTO RÉELLE : tokens signés
avec une clé RSA locale, clé publique injectée à la place du JWKS de l'IdP.
"""
import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School
from src.models.org import AppUser, Membership
from src.rbac import oidc
from src.rbac.auth import parse_token
import src.api.app as appmod

SSO_EMAIL = "prof.sso@demo.atlas"
_ISSUER = "https://idp.example.test"
_ORIG_DISCOVERY = oidc.discovery   # capturé avant tout monkeypatch (UAE PASS = endpoints fixes)

# Clés RSA de test (paire « IdP » légitime + une paire « pirate » pour les mauvaises signatures).
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_ROGUE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _enable_generic(monkeyish_env: dict = None):
    os.environ.update({
        "OIDC_GENERIC_CLIENT_ID": "cid-123",
        "OIDC_GENERIC_CLIENT_SECRET": "secret-xyz",
        "OIDC_GENERIC_ISSUER": _ISSUER,
        "WEB_BASE_URL": "http://localhost:3000",
        **(monkeyish_env or {}),
    })
    oidc._disco_cache.clear()
    oidc.discovery = lambda p: {
        "issuer": _ISSUER,
        "authorization_endpoint": f"{_ISSUER}/authorize",
        "token_endpoint": f"{_ISSUER}/token",
        "userinfo_endpoint": f"{_ISSUER}/userinfo",
        "jwks_uri": f"{_ISSUER}/jwks",
    }
    # Clé de signature résolue localement (pas de PyJWKClient ni de réseau).
    oidc._signing_key = lambda provider, id_token: _KEY.public_key()


def _id_token(*, aud="cid-123", iss=_ISSUER, nonce="n-1", email=SSO_EMAIL,
              exp_delta=300, key=_KEY, alg="RS256", extra=None):
    now = int(time.time())
    claims = {
        "iss": iss, "aud": aud, "sub": "idp-user-1",
        "iat": now, "exp": now + exp_delta,
        "email": email, "email_verified": True, "nonce": nonce,
    }
    if extra:
        claims.update(extra)
    if alg == "none":
        return jwt.encode(claims, None, algorithm="none")
    return jwt.encode(claims, key, algorithm=alg)


def _client(with_user_email=SSO_EMAIL):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    with Session(bind=engine) as s:
        school = School(name="Demo"); s.add(school); s.flush()
        if with_user_email:
            u = AppUser(email=with_user_email); s.add(u); s.flush()
            s.add(Membership(user_id=u.id, role=Role.TEACHER, school_id=school.id))
        s.commit()

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    return TestClient(appmod.app)


# ---------- config providers ----------

def test_provider_disabled_without_env():
    for k in ("OIDC_GENERIC_CLIENT_ID", "OIDC_GENERIC_CLIENT_SECRET", "OIDC_GENERIC_ISSUER"):
        os.environ.pop(k, None)
    assert oidc.get_provider("generic") is None
    assert "generic" not in oidc.enabled_providers()


def test_provider_enabled_with_env():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert p is not None and p.client_id == "cid-123"
    assert "generic" in oidc.enabled_providers()


# ---------- validation cryptographique du ID token (unitaire, crypto réelle) ----------

def test_validate_accepts_valid_token():
    _enable_generic()
    p = oidc.get_provider("generic")
    claims = oidc.validate_id_token(p, _id_token(nonce="abc"), nonce="abc")
    assert claims["email"] == SSO_EMAIL


def _expect_reject(p, token, *, nonce="n-1"):
    try:
        oidc.validate_id_token(p, token, nonce=nonce)
    except oidc.IdTokenError:
        return True
    raise AssertionError("ID token aurait dû être rejeté")


def test_validate_rejects_bad_signature():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert _expect_reject(p, _id_token(key=_ROGUE))   # signé par une autre clé


def test_validate_rejects_wrong_audience():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert _expect_reject(p, _id_token(aud="autre-client"))


def test_validate_rejects_wrong_issuer():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert _expect_reject(p, _id_token(iss="https://evil.test"))


def test_validate_rejects_expired():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert _expect_reject(p, _id_token(exp_delta=-1000))  # au-delà du leeway


def test_validate_rejects_nonce_mismatch():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert _expect_reject(p, _id_token(nonce="autre"), nonce="attendu")


def test_validate_rejects_alg_none():
    _enable_generic()
    p = oidc.get_provider("generic")
    assert _expect_reject(p, _id_token(alg="none"))   # token non signé refusé


# ---------- flux Authorization Code ----------

def _start_and_get_state(client):
    r = client.get("/oauth/generic/start", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith(f"{_ISSUER}/authorize")
    q = parse_qs(urlparse(loc).query)
    assert q["client_id"] == ["cid-123"]
    assert q["redirect_uri"] == ["http://localhost:3000/api/oauth/generic/callback"]
    assert q.get("nonce"), "le nonce doit être transmis à l'IdP"
    return q["state"][0]


def _nonce_of(state: str) -> str:
    return parse_token(state, purpose="oidc_state").split("|", 1)[1]


def test_start_redirects_to_idp_with_signed_state_and_nonce():
    _enable_generic()
    client = _client()
    _start_and_get_state(client)
    appmod.app.dependency_overrides.clear()


def test_callback_rejects_forged_state():
    _enable_generic()
    client = _client()
    r = client.get("/oauth/generic/callback?code=abc&state=forged.deadbeef",
                   follow_redirects=False)
    assert r.status_code == 400
    appmod.app.dependency_overrides.clear()


def test_callback_known_user_opens_session():
    _enable_generic()
    client = _client(with_user_email=SSO_EMAIL)
    state = _start_and_get_state(client)
    nonce = _nonce_of(state)
    # exchange_code renvoie un id_token signé portant LE nonce du state → chaîne réelle.
    oidc.exchange_code = lambda p, code, ru: {"id_token": _id_token(nonce=nonce),
                                              "access_token": "at-1"}
    r = client.get(f"/oauth/generic/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302, r.text
    loc = r.headers["location"]
    assert loc.startswith("http://localhost:3000/oauth/callback#token=")
    assert len(loc.split("#token=")[1]) > 10
    appmod.app.dependency_overrides.clear()


def test_callback_rejects_tampered_id_token():
    _enable_generic()
    client = _client(with_user_email=SSO_EMAIL)
    state = _start_and_get_state(client)
    # id_token signé par une clé pirate → validation échoue → sso_error=token.
    oidc.exchange_code = lambda p, code, ru: {"id_token": _id_token(key=_ROGUE),
                                              "access_token": "at-1"}
    r = client.get(f"/oauth/generic/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302
    assert "sso_error=token" in r.headers["location"]
    appmod.app.dependency_overrides.clear()


def test_callback_rejects_replayed_nonce():
    """Un id_token valide mais dont le nonce ne correspond pas au state est rejeté (rejeu)."""
    _enable_generic()
    client = _client(with_user_email=SSO_EMAIL)
    state = _start_and_get_state(client)
    oidc.exchange_code = lambda p, code, ru: {"id_token": _id_token(nonce="vieux-nonce"),
                                              "access_token": "at-1"}
    r = client.get(f"/oauth/generic/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302
    assert "sso_error=token" in r.headers["location"]
    appmod.app.dependency_overrides.clear()


def test_callback_unknown_user_is_refused():
    _enable_generic()
    client = _client(with_user_email=SSO_EMAIL)
    state = _start_and_get_state(client)
    nonce = _nonce_of(state)
    oidc.exchange_code = lambda p, code, ru: {"id_token": _id_token(nonce=nonce,
                                                                    email="inconnu@x.io"),
                                              "access_token": "at-1"}
    r = client.get(f"/oauth/generic/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302
    assert "sso_error=unknown" in r.headers["location"]
    appmod.app.dependency_overrides.clear()


# ---------- UAE PASS (SSO national EAU : public + privé, identité via userinfo) ----------

def _enable_uaepass(env_extra=None):
    for k in ("OIDC_UAEPASS_ISSUER",):
        os.environ.pop(k, None)
    os.environ.update({
        "OIDC_UAEPASS_CLIENT_ID": "sp-uae", "OIDC_UAEPASS_CLIENT_SECRET": "sp-secret",
        "OIDC_UAEPASS_ENV": "staging", "WEB_BASE_URL": "http://localhost:3000",
        **(env_extra or {}),
    })
    oidc.discovery = _ORIG_DISCOVERY   # restaure : UAE PASS utilise static_discovery, pas de réseau


def test_uaepass_provider_config():
    _enable_uaepass()
    p = oidc.get_provider("uaepass")
    assert p is not None
    assert p.identity_source == "userinfo"            # pas de id_token signé standard
    assert p.scopes == "urn:uae:digitalid:profile:general"
    assert p.acr_values and "level:low" in p.acr_values
    assert p.static_discovery["authorization_endpoint"] == "https://stg-id.uaepass.ae/idshub/authorize"
    assert "uaepass" in oidc.enabled_providers()


def test_uaepass_authorize_url_has_acr_and_scope():
    _enable_uaepass()
    p = oidc.get_provider("uaepass")
    url = oidc.authorize_url(p, "http://localhost:3000/api/oauth/uaepass/callback", "st", nonce="n")
    assert url.startswith("https://stg-id.uaepass.ae/idshub/authorize")
    q = parse_qs(urlparse(url).query)
    assert q["acr_values"] == ["urn:safelayer:tws:policies:authentication:level:low"]
    assert q["scope"] == ["urn:uae:digitalid:profile:general"]


def test_uaepass_resolve_identity_uses_userinfo():
    _enable_uaepass()
    p = oidc.get_provider("uaepass")
    oidc.fetch_userinfo = lambda prov, at: {"email": SSO_EMAIL, "sub": "uae-1"}
    claims = oidc.resolve_identity(p, {"access_token": "at-uae"}, nonce="ignored")
    assert claims["email"] == SSO_EMAIL          # nonce ignoré en mode userinfo


def test_uaepass_callback_opens_session():
    _enable_uaepass()
    client = _client(with_user_email=SSO_EMAIL)
    # start → state signé
    r = client.get("/oauth/uaepass/start", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith("https://stg-id.uaepass.ae/idshub/authorize")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    # callback : UAE PASS ne renvoie pas de id_token signé → identité via userinfo
    oidc.exchange_code = lambda prov, code, ru: {"access_token": "at-uae"}
    oidc.fetch_userinfo = lambda prov, at: {"email": SSO_EMAIL, "sub": "uae-1"}
    cb = client.get(f"/oauth/uaepass/callback?code=abc&state={state}", follow_redirects=False)
    assert cb.status_code == 302, cb.text
    assert cb.headers["location"].startswith("http://localhost:3000/oauth/callback#token=")
    appmod.app.dependency_overrides.clear()


def test_extract_email_rejects_unverified():
    assert oidc.extract_email({"email": "a@b.io", "email_verified": False}) is None
    assert oidc.extract_email({"email": "A@B.io"}) == "a@b.io"
    assert oidc.extract_email({"preferred_username": "u@b.io"}) == "u@b.io"
    assert oidc.extract_email({}) is None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
