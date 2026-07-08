"""Tests du flux d'authentification — SSO uniquement (plus de mot de passe ni MFA TOTP).

Couvre :
  - simulateur SSO de dev (`/dev/login`) : ouvre une session pour un compte existant,
    et reste FERMÉ par défaut / en prod (défense en profondeur) ;
  - lien magique super-admin (`/admin/request-link` → `/admin/login`), réservé aux
    SUPER_ADMIN, sans mot de passe.
Utilise un SQLite temporaire + override get_db (aucun serveur requis).
"""
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School, Student
from src.models.org import AppUser, Classroom, Membership, TeacherClassroom
from src.notify.email import FakeEmailSender
import src.api.app as appmod

FAKE_EMAIL = FakeEmailSender()


def _client():
    os.environ["ATLAS_ENV"] = "dev"
    os.environ["OIDC_DEV_LOGIN"] = "1"   # active le simulateur SSO de dev
    FAKE_EMAIL.sent.clear()
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)

    with Session(bind=engine) as s:
        school = School(name="Demo"); s.add(school); s.flush()
        cls = Classroom(school_id=school.id, name="4A"); s.add(cls); s.flush()
        teacher = AppUser(email="prof@demo.atlas")
        eleve_user = AppUser(email="eleve1@demo.atlas")
        super_admin = AppUser(email="ops@atlas.io")
        s.add_all([teacher, eleve_user, super_admin]); s.flush()
        s.add_all([
            Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id),
            TeacherClassroom(user_id=teacher.id, classroom_id=cls.id),
            Membership(user_id=eleve_user.id, role=Role.STUDENT),
            Membership(user_id=super_admin.id, role=Role.SUPER_ADMIN),
        ])
        s.add(Student(school_id=school.id, classroom_id=cls.id,
                      user_id=eleve_user.id, external_ref="S1"))
        s.commit()

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    appmod.app.dependency_overrides[appmod.get_email_sender] = lambda: FAKE_EMAIL
    return TestClient(appmod.app)


# ---------- simulateur SSO de dev ----------

def test_dev_login_opens_session_for_existing_user():
    client = _client()
    r = client.post("/dev/login", json={"email": "eleve1@demo.atlas"})
    assert r.status_code == 200, r.text
    assert "token" in r.json()
    appmod.app.dependency_overrides.clear()


def test_dev_login_unknown_user_refused():
    client = _client()
    r = client.post("/dev/login", json={"email": "inconnu@demo.atlas"})
    assert r.status_code == 401
    appmod.app.dependency_overrides.clear()


def test_dev_login_disabled_without_flag():
    client = _client()
    os.environ.pop("OIDC_DEV_LOGIN", None)     # simulateur coupé
    r = client.post("/dev/login", json={"email": "eleve1@demo.atlas"})
    assert r.status_code == 404
    os.environ["OIDC_DEV_LOGIN"] = "1"
    appmod.app.dependency_overrides.clear()


def test_dev_login_disabled_in_prod():
    client = _client()
    os.environ["ATLAS_ENV"] = "prod"           # fermé en prod même avec le flag
    try:
        r = client.post("/dev/login", json={"email": "eleve1@demo.atlas"})
        assert r.status_code == 404
    finally:
        os.environ["ATLAS_ENV"] = "dev"
    appmod.app.dependency_overrides.clear()


# ---------- lien magique super-admin ----------

def _magic_link_token():
    return re.search(r"/api/admin/login\?token=([^\"\s]+)", FAKE_EMAIL.sent[-1]["html"]).group(1)


def test_super_admin_magic_link_signs_in():
    client = _client()
    r = client.post("/admin/request-link", json={"email": "ops@atlas.io"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert FAKE_EMAIL.sent, "un email de lien magique doit partir"
    # GET du lien email : validation SANS consommation (anti-préchargement) →
    # page de confirmation ; le POST (clic humain) consomme et ouvre la session.
    login = client.get(f"/admin/login?token={_magic_link_token()}", follow_redirects=False)
    assert login.status_code == 302
    link_token = login.headers["location"].split("/login/confirm#token=")[1]
    confirm = client.post("/admin/login/confirm", json={"token": link_token})
    assert confirm.status_code == 200 and confirm.json()["token"]   # session ouverte
    appmod.app.dependency_overrides.clear()


def test_magic_link_not_sent_to_non_super_admin():
    client = _client()
    r = client.post("/admin/request-link", json={"email": "prof@demo.atlas"})
    assert r.status_code == 200 and r.json() == {"ok": True}   # réponse constante (anti-énum)
    assert not FAKE_EMAIL.sent                                  # mais aucun email n'est envoyé
    appmod.app.dependency_overrides.clear()


def test_admin_login_rejects_bad_token():
    client = _client()
    r = client.get("/admin/login?token=forged.deadbeef", follow_redirects=False)
    assert r.status_code == 302 and "admin_error=invalid" in r.headers["location"]
    appmod.app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
