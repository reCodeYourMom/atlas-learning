"""Tests anti-rejeu ET anti-préchargement des liens magiques (revues 2026-07-07).

Les liens magiques (parent, super-admin) sont RÉELLEMENT single-use : le `jti` du
jeton est consommé atomiquement (table consumed_token). Contrat en deux temps
(anti-préchargement — les scanners d'emails type Outlook SafeLinks suivent les
liens en GET et brûleraient le jti avant le clic humain) :
  - le GET du lien email VALIDE sans consommer (idempotent, lecture seule) et
    redirige vers une page de confirmation, jeton dans le fragment (#token=…) ;
  - le POST /…/login/confirm (bouton « Continuer », action humaine) CONSOMME le
    jti — le second usage (lien intercepté / rejoué) est refusé SANS session.
Un jeton déjà consommé revu au GET → redirection UI `error=used` (pas de 401 JSON
brut : le parent doit pouvoir redemander un lien depuis la page). Les jetons de
SESSION (Bearer) restent réutilisables par nature.
"""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School, Student
from src.models.org import AppUser, Membership, Organization, ParentStudent
from src.models.token import ConsumedToken
from src.rbac.auth import make_token
import src.api.app as appmod

FAKE_SENT = []


class _FakeSender:
    def send(self, *, to, subject, html, text):
        FAKE_SENT.append({"to": to, "subject": subject, "html": html, "text": text})


def _client():
    FAKE_SENT.clear()
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    with Session(bind=engine) as s:
        org = Organization(name="School", domain="school.edu"); s.add(org); s.flush()
        school = School(name="S1", organization_id=org.id); s.add(school); s.flush()
        st = Student(school_id=school.id, external_ref="S1"); s.add(st); s.flush()
        mom = AppUser(email="mom@home.com"); s.add(mom); s.flush()
        s.add(Membership(user_id=mom.id, role=Role.PARENT, organization_id=org.id))
        s.add(ParentStudent(user_id=mom.id, student_id=st.id))
        ops = AppUser(email="ops@atlas.io"); s.add(ops); s.flush()
        s.add(Membership(user_id=ops.id, role=Role.SUPER_ADMIN))
        s.commit()
        session_token = make_token(str(ops.id))

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    appmod.app.dependency_overrides[appmod.get_email_sender] = lambda: _FakeSender()
    return TestClient(appmod.app), engine, session_token


def _clear():
    appmod.app.dependency_overrides.clear()


def _link_token(pattern):
    return re.search(pattern, FAKE_SENT[-1]["html"]).group(1)


def _consumed_count(engine):
    with Session(bind=engine) as s:
        return len(s.execute(select(ConsumedToken)).scalars().all())


# ---------- lien magique parent : GET sans effet de bord (anti-préchargement) ----------

def test_parent_login_get_does_not_consume():
    client, engine, _ = _client()
    client.post("/parent/request-link", json={"email": "mom@home.com"})
    tok = _link_token(r"/api/parent/login\?token=([^\"]+)")
    # Deux GET successifs (scanner d'emails, prévisualisation) : tous deux OK, vers la
    # page de confirmation, jeton du LIEN dans le fragment — et rien n'est consommé.
    for _ in range(2):
        r = client.get(f"/parent/login?token={tok}", follow_redirects=False)
        assert r.status_code == 302
        assert "/parent/confirm#token=" in r.headers["location"]
    assert _consumed_count(engine) == 0     # GET idempotent : aucun jti consommé
    _clear()


# ---------- lien magique parent : le POST consomme, le rejeu est rejeté ----------

def test_parent_magic_link_replayed_is_rejected():
    client, engine, _ = _client()
    client.post("/parent/request-link", json={"email": "mom@home.com"})
    tok = _link_token(r"/api/parent/login\?token=([^\"]+)")
    # Clic humain : POST de confirmation → session ouverte, jti consommé.
    first = client.post("/parent/login/confirm", json={"token": tok})
    assert first.status_code == 200 and first.json()["token"]
    # REJEU du même lien (intercepté) → refus SANS session.
    replay = client.post("/parent/login/confirm", json={"token": tok})
    assert replay.status_code == 401 and replay.json()["detail"] == "used"
    # Rejeu via le GET (lien recliqué depuis l'email) → même redirection UI qu'avant :
    # pas de 401 JSON brut, le parent doit pouvoir redemander un lien depuis la page.
    get_replay = client.get(f"/parent/login?token={tok}", follow_redirects=False)
    assert get_replay.status_code == 302
    assert "error=used" in get_replay.headers["location"]
    assert "confirm" not in get_replay.headers["location"]   # aucune reprise du flux
    _clear()


def test_parent_scanner_prefetch_then_human_click_logs_in():
    # Simulation scanner : N GET (SafeLinks, préchargement) AVANT le clic humain —
    # le lien ne doit PAS être brûlé, le parent doit pouvoir se connecter.
    client, engine, _ = _client()
    client.post("/parent/request-link", json={"email": "mom@home.com"})
    tok = _link_token(r"/api/parent/login\?token=([^\"]+)")
    for _ in range(5):                                       # le scanner suit le lien
        r = client.get(f"/parent/login?token={tok}", follow_redirects=False)
        assert "/parent/confirm#token=" in r.headers["location"]
    human = client.post("/parent/login/confirm", json={"token": tok})
    assert human.status_code == 200
    session_token = human.json()["token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {session_token}"})
    assert me.status_code == 200                             # login OK malgré le scanner
    _clear()


def test_parent_magic_link_consumption_is_recorded():
    client, engine, _ = _client()
    client.post("/parent/request-link", json={"email": "mom@home.com"})
    tok = _link_token(r"/api/parent/login\?token=([^\"]+)")
    client.get(f"/parent/login?token={tok}", follow_redirects=False)
    assert _consumed_count(engine) == 0                      # le GET n'enregistre rien
    client.post("/parent/login/confirm", json={"token": tok})
    with Session(bind=engine) as s:
        rows = s.execute(select(ConsumedToken)).scalars().all()
        assert len(rows) == 1 and rows[0].purpose == "parent_login"
    _clear()


# ---------- lien magique super-admin : même patron ----------

def test_admin_login_get_does_not_consume():
    client, engine, _ = _client()
    client.post("/admin/request-link", json={"email": "ops@atlas.io"})
    tok = _link_token(r"/api/admin/login\?token=([^\"\s]+)")
    for _ in range(2):
        r = client.get(f"/admin/login?token={tok}", follow_redirects=False)
        assert r.status_code == 302
        assert "/login/confirm#token=" in r.headers["location"]
    assert _consumed_count(engine) == 0
    _clear()


def test_admin_magic_link_replayed_is_rejected():
    client, _, _ = _client()
    client.post("/admin/request-link", json={"email": "ops@atlas.io"})
    tok = _link_token(r"/api/admin/login\?token=([^\"\s]+)")
    first = client.post("/admin/login/confirm", json={"token": tok})
    assert first.status_code == 200 and first.json()["token"]
    replay = client.post("/admin/login/confirm", json={"token": tok})
    assert replay.status_code == 401 and replay.json()["detail"] == "used"
    get_replay = client.get(f"/admin/login?token={tok}", follow_redirects=False)
    assert get_replay.status_code == 302
    assert "admin_error=used" in get_replay.headers["location"]
    assert "confirm" not in get_replay.headers["location"]   # aucune reprise du flux
    _clear()


# ---------- les jetons de SESSION restent réutilisables (non cassés) ----------

def test_session_bearer_token_stays_reusable():
    client, _, session_token = _client()
    headers = {"Authorization": f"Bearer {session_token}"}
    assert client.get("/me", headers=headers).status_code == 200
    assert client.get("/me", headers=headers).status_code == 200  # 2e usage OK (Bearer)
    _clear()


def test_forged_magic_link_still_redirects_invalid():
    client, _, _ = _client()
    r = client.get("/parent/login?token=forged.deadbeef", follow_redirects=False)
    assert r.status_code == 302 and "error=invalid" in r.headers["location"]
    # Un jeton forgé POSTé directement à la confirmation est refusé aussi.
    p = client.post("/parent/login/confirm", json={"token": "forged.deadbeef"})
    assert p.status_code == 401 and p.json()["detail"] == "invalid"
    _clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
