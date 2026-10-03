"""Tests sièges / licence (Phase F) — usage, dépassement (alerte), quota vendeur, RBAC."""
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
from src.models.org import AppUser, Membership, Organization, TenantIntegration
from src.licensing.service import flag_overage, seat_usage, set_seats
from src.rbac.auth import make_token
import src.api.app as appmod


def _seed(s, seats=None, n_students=2):
    org = Organization(name="School", domain="school.edu", seats=seats); s.add(org); s.flush()
    school = School(name="S1", organization_id=org.id); s.add(school); s.flush()
    for i in range(n_students):
        s.add(Student(school_id=school.id, external_ref=f"S{i}"))
    s.add(TenantIntegration(organization_id=org.id, status="connected", admin_email="it@school.edu"))
    s.flush()
    return org


def _mem():
    engine = make_engine(f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")
    Base.metadata.create_all(engine)
    return Session(bind=engine)


# ---------- service pur ----------

def test_seat_usage_counts_active_students():
    s = _mem(); org = _seed(s, seats=10, n_students=3); s.commit()
    u = seat_usage(s, org)
    assert u == {"seats": 10, "used": 3, "over_by": 0, "over": False}


def test_overage_flags_integration():
    s = _mem(); org = _seed(s, seats=2, n_students=5); s.commit()
    u = flag_overage(s, org); s.commit()
    assert u["over"] is True and u["over_by"] == 3
    integ = s.execute(select(TenantIntegration)).scalar_one()
    assert integ.status == "over_capacity" and "Dépassement" in integ.last_error


def test_raising_quota_clears_overage():
    s = _mem(); org = _seed(s, seats=2, n_students=5); s.commit()
    flag_overage(s, org); s.commit()
    set_seats(s, org, 100); flag_overage(s, org); s.commit()
    integ = s.execute(select(TenantIntegration)).scalar_one()
    assert integ.status == "connected" and integ.last_error is None


def test_unlimited_when_seats_none():
    s = _mem(); org = _seed(s, seats=None, n_students=9); s.commit()
    assert seat_usage(s, org)["over"] is False


# ---------- endpoint vendeur (SUPER_ADMIN) ----------

def _client(role=Role.SUPER_ADMIN):
    engine = make_engine(f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")
    Base.metadata.create_all(engine)
    with Session(bind=engine) as s:
        org = _seed(s, seats=None, n_students=5)
        user = AppUser(email="vendor@atlas.io"); s.add(user); s.flush()
        s.add(Membership(user_id=user.id, role=role, organization_id=org.id))
        s.commit()
        token = make_token(str(user.id)); org_id = str(org.id)

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    client = TestClient(appmod.app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, engine, org_id


def test_vendor_sets_quota_and_detects_overage():
    client, engine, org_id = _client(Role.SUPER_ADMIN)
    r = client.post(f"/admin/organizations/{org_id}/seats", json={"seats": 3})
    assert r.status_code == 200, r.text
    assert r.json() == {"seats": 3, "used": 5, "over_by": 2, "over": True}
    with Session(bind=engine) as s:
        assert s.execute(select(TenantIntegration)).scalar_one().status == "over_capacity"
    appmod.app.dependency_overrides.clear()


def test_non_super_admin_cannot_set_seats():
    client, _, org_id = _client(Role.IT_ADMIN)
    assert client.post(f"/admin/organizations/{org_id}/seats", json={"seats": 3}).status_code == 403
    appmod.app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
