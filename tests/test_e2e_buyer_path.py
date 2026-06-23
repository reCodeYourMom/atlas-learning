"""Test end-to-end du parcours d'achat (filet de sécurité).

Déroule le scénario réel via les VRAIS endpoints ; seules les frontières externes sont
mockées (OIDC Google, Directory Admin SDK, Classroom guardians, email) :

  1. L'IT admin s'onboarde via Sign-in Google (compte Workspace + admin vérifié) → tenant créé.
  2. Il déclenche le rostering : CompositeDirectory (annuaire + tuteurs Classroom) →
     élève créé, parent créé + lien parent↔enfant (source="roster").
  3. Le parent demande un lien magique → ouvre une session → voit l'espace de son enfant.
"""
import os
import re
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
from src.models.measurement import Student
from src.models.org import AppUser, Membership, Organization, ParentStudent
from src.rbac import oidc
from src.rbac.auth import parse_token
from src.rostering import google as gdir
from src.rostering.directory import (
    DirectorySnapshot, DirGroup, DirGuardian, DirMembership, DirOrgUnit, DirUser, FakeDirectory,
)
from src.rostering.google import CompositeDirectory
from src.notify.email import FakeEmailSender
import src.api.app as appmod

FAKE_EMAIL = FakeEmailSender()


def _composite():
    """Annuaire Admin SDK (1 élève) + tuteurs Classroom (la mère d'Alice)."""
    snap = DirectorySnapshot(
        [DirOrgUnit("ou_s", "Students")],
        [DirUser("u_alice", "alice@demo.edu", "Alice", "ou_s")],
        [DirGroup("g1", "Class 1")],
        [DirMembership("g1", "u_alice")],
    )

    class _Guardians:
        def guardians_for(self, ids):
            return [DirGuardian(i, "mom@home.com", "Mom", "grd1") for i in ids if i == "u_alice"]

    return CompositeDirectory(FakeDirectory(snap), _Guardians())


def _wire(engine):
    def _get_db():
        s = Session(bind=engine)
        try:
            yield s
        finally:
            s.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    appmod.app.dependency_overrides[appmod.get_email_sender] = lambda: FAKE_EMAIL
    appmod.app.dependency_overrides[appmod.get_directory_factory] = \
        lambda: (lambda integ: _composite())


# Originaux des fonctions oidc/gdir remplacées par des stubs réseau ci-dessous — restaurés
# en fin de test pour ne pas polluer test_oidc.py (isolation stricte des globals de module).
_ORIG = {
    "discovery": oidc.discovery,
    "exchange_code": oidc.exchange_code,
    "validate_id_token": oidc.validate_id_token,
    "get_user_self": gdir.get_user_self,
}


def _restore_oidc():
    oidc.discovery = _ORIG["discovery"]
    oidc.exchange_code = _ORIG["exchange_code"]
    oidc.validate_id_token = _ORIG["validate_id_token"]
    gdir.get_user_self = _ORIG["get_user_self"]
    oidc._disco_cache.clear()
    appmod.app.dependency_overrides.clear()


def test_buyer_path_end_to_end():
    FAKE_EMAIL.sent.clear()
    engine = make_engine(f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")
    Base.metadata.create_all(engine)
    _wire(engine)

    try:
        _run_buyer_path(engine)
    finally:
        _restore_oidc()


def _run_buyer_path(engine):
    # --- frontières Google mockées ---
    os.environ.update({"OIDC_GOOGLE_CLIENT_ID": "cid", "OIDC_GOOGLE_CLIENT_SECRET": "sec",
                       "WEB_BASE_URL": "http://localhost:3000"})
    oidc._disco_cache.clear()
    oidc.discovery = lambda p: {
        "issuer": "https://accounts.google.com",
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    }
    oidc.exchange_code = lambda p, code, ru: {"access_token": "at", "id_token": "idt"}
    # identité prouvée par le ID token validé (claims signés iss/aud/exp/nonce)
    oidc.validate_id_token = lambda p, tok, nonce=None: {"email": "it@demo.edu",
                                                         "email_verified": True, "hd": "demo.edu"}
    gdir.get_user_self = lambda at: {"isAdmin": True, "customerId": "C1"}

    client = TestClient(appmod.app)

    # === 1) Onboarding : l'IT admin crée son tenant via Google ===
    q = parse_qs(urlparse(client.get("/onboarding/google/start",
                                     follow_redirects=False).headers["location"]).query)
    cb = client.get(f"/onboarding/google/callback?code=x&state={q['state'][0]}",
                    follow_redirects=False)
    assert cb.status_code == 302
    admin_token = cb.headers["location"].split("#token=")[1]
    parse_token(admin_token, purpose="session")
    H = {"Authorization": f"Bearer {admin_token}"}

    with Session(bind=engine) as s:
        assert s.execute(select(Organization).where(Organization.domain == "demo.edu")
                         ).scalar_one() is not None

    # === 2) Rostering : sync composite (annuaire + tuteurs Classroom) ===
    run = client.post("/admin/rostering/sync", headers=H)
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "ok"

    with Session(bind=engine) as s:
        alice_user = s.execute(select(AppUser).where(AppUser.email == "alice@demo.edu")).scalar_one()
        alice = s.execute(select(Student).where(Student.user_id == alice_user.id)).scalar_one()
        mom = s.execute(select(AppUser).where(AppUser.email == "mom@home.com")).scalar_one()
        link = s.get(ParentStudent, (mom.id, alice.id))
        assert link is not None and link.source == "roster"          # lien vérifié par Classroom
        assert Role.PARENT in set(
            s.execute(select(Membership.role).where(Membership.user_id == mom.id)).scalars())

    # la console reflète l'effectif
    assert client.get("/admin/integration", headers=H).json()["organization"]["seats_used"] == 1

    # === 3) Accès parent : lien magique → espace de l'enfant ===
    assert client.post("/parent/request-link", json={"email": "mom@home.com"}).status_code == 200
    tok = re.search(r"/api/parent/login\?token=([^\"]+)", FAKE_EMAIL.sent[-1]["html"]).group(1)
    login = client.get(f"/parent/login?token={tok}", follow_redirects=False)
    parent_session = login.headers["location"].split("#token=")[1]

    PH = {"Authorization": f"Bearer {parent_session}"}
    children = client.get("/parent/children", headers=PH).json()["children"]
    assert len(children) == 1 and children[0]["label"] == "alice@demo.edu"

    # le parent voit la trajectoire de SON enfant, et rien d'autre (RBAC)
    assert client.get(f"/students/{alice.id}/trajectory", headers=PH).status_code == 200


if __name__ == "__main__":
    test_buyer_path_end_to_end()
    print("  PASS test_buyer_path_end_to_end\n\n1/1 tests OK")
