"""Tests accès parent (Phase H) — lien magique, auto-demande, invitation, checklist IT."""
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
from src.models.org import AppUser, Membership, Organization, ParentStudent, TenantIntegration
from src.rbac.auth import make_token, parse_token
from src.notify.email import FakeEmailSender
import src.api.app as appmod

FAKE = FakeEmailSender()


def _client(admin=True):
    FAKE.sent.clear()
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    with Session(bind=engine) as s:
        org = Organization(name="School", domain="school.edu"); s.add(org); s.flush()
        it = AppUser(email="it@school.edu"); s.add(it); s.flush()
        s.add(Membership(user_id=it.id, role=Role.IT_ADMIN if admin else Role.STUDENT,
                         organization_id=org.id if admin else None))
        school = School(name="S1", organization_id=org.id); s.add(school); s.flush()
        alice = AppUser(email="alice@school.edu", external_ref="u_alice"); s.add(alice); s.flush()
        st = Student(school_id=school.id, user_id=alice.id, external_ref="u_alice"); s.add(st); s.flush()
        mom = AppUser(email="mom@home.com", external_ref="grd1"); s.add(mom); s.flush()
        s.add(Membership(user_id=mom.id, role=Role.PARENT, organization_id=org.id))
        s.add(ParentStudent(user_id=mom.id, student_id=st.id))
        s.add(TenantIntegration(organization_id=org.id, admin_email="it@school.edu"))
        s.commit()
        token = make_token(str(it.id))

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    appmod.app.dependency_overrides[appmod.get_email_sender] = lambda: FAKE
    client = TestClient(appmod.app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _clear():
    appmod.app.dependency_overrides.clear()


def _link_token(html):
    return re.search(r"/api/parent/login\?token=([^\"]+)", html).group(1)


def test_parent_request_link_sends_magic_link():
    client = _client()
    r = client.post("/parent/request-link", json={"email": "MOM@home.com"})
    assert r.status_code == 200
    assert len(FAKE.sent) == 1 and FAKE.sent[0]["to"] == "mom@home.com"
    tok = _link_token(FAKE.sent[0]["html"])
    assert parse_token(tok, purpose="parent_login")          # jeton valide, bon usage
    _clear()


def test_request_link_no_enumeration_for_unknown():
    client = _client()
    assert client.post("/parent/request-link", json={"email": "ghost@x.io"}).status_code == 200
    assert FAKE.sent == []                                    # aucun email, aucune fuite
    _clear()


def test_request_link_ignores_non_parent():
    client = _client()
    client.post("/parent/request-link", json={"email": "alice@school.edu"})  # élève, pas parent
    assert FAKE.sent == []
    _clear()


def test_magic_link_opens_session():
    client = _client()
    client.post("/parent/request-link", json={"email": "mom@home.com"})
    tok = _link_token(FAKE.sent[0]["html"])
    r = client.get(f"/parent/login?token={tok}", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("http://localhost:3000/oauth/callback#token=")
    parse_token(loc.split("#token=")[1], purpose="session")  # session applicative valide
    _clear()


def test_invalid_magic_link_redirects_with_error():
    client = _client()
    r = client.get("/parent/login?token=bad.token", follow_redirects=False)
    assert r.status_code == 302 and "error=invalid" in r.headers["location"]
    _clear()


def test_admin_bulk_invites_parents():
    client = _client()
    r = client.post("/admin/parents/invite")
    assert r.status_code == 200 and r.json()["invited"] == 1
    assert FAKE.sent[0]["to"] == "mom@home.com"
    _clear()


def test_setup_checklist_reflects_state():
    client = _client()
    setup = client.get("/admin/setup").json()
    done = {st["key"]: st["done"] for st in setup["steps"]}
    assert done["connect"] is True            # intégration présente
    assert done["sync"] is False              # pas encore syncé
    assert done["verify"] is True             # 1 élève existe
    assert done["parents"] is False
    client.post("/admin/parents/invite")
    assert client.get("/admin/setup").json()["steps"][3]["done"] is True  # parents invités
    _clear()


def test_parent_endpoints_admin_only():
    client = _client(admin=False)
    assert client.post("/admin/parents/invite").status_code == 403
    assert client.get("/admin/setup").status_code == 403
    _clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
