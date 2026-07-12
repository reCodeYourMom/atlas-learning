"""Tests console IT admin (Phase D) — statut intégration, sync déclenchée, historique, RBAC.

Annuaire factice injecté via get_directory_factory (zéro Google, zéro réseau).
"""
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
from src.models.org import AppUser, Membership, Organization, RosterRun, TenantIntegration
from src.rbac.auth import make_token
from src.rostering.directory import (
    DirectorySnapshot, DirGroup, DirMembership, DirOrgUnit, DirUser,
)
from src.rostering.directory import FakeDirectory
import src.api.app as appmod


def _snapshot():
    return DirectorySnapshot(
        [DirOrgUnit("ou_s", "Students")],
        [DirUser("u_a", "alice@school.edu", "Alice", "ou_s"),
         DirUser("u_b", "bob@school.edu", "Bob", "ou_s")],
        [DirGroup("g1", "Class 1")],
        [DirMembership("g1", "u_a"), DirMembership("g1", "u_b")],
    )


def _client(admin=True, with_integration=True):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    with Session(bind=engine) as s:
        org = Organization(name="School", domain="school.edu"); s.add(org); s.flush()
        user = AppUser(email="it@school.edu"); s.add(user); s.flush()
        role = Role.IT_ADMIN if admin else Role.STUDENT
        # IT admin : membership scopée à l'org ; étudiant : pas d'org (RBAC doit refuser)
        s.add(Membership(user_id=user.id, role=role,
                         organization_id=org.id if admin else None))
        if with_integration:
            s.add(TenantIntegration(organization_id=org.id, admin_email="it@school.edu"))
        s.commit()
        token = make_token(str(user.id))

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    appmod.app.dependency_overrides[appmod.get_directory_factory] = \
        lambda: (lambda integ: FakeDirectory(_snapshot()))
    client = TestClient(appmod.app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, engine


def _clear():
    appmod.app.dependency_overrides.clear()


def test_integration_status_before_sync():
    client, _ = _client()
    r = client.get("/admin/integration")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organization"]["domain"] == "school.edu"
    assert body["integration"]["status"] == "pending"
    assert body["organization"]["seats_used"] == 0
    _clear()


def test_trigger_sync_then_history_and_status():
    client, _ = _client()
    r = client.post("/admin/rostering/sync")
    assert r.status_code == 200, r.text
    run = r.json()
    # 1 école + 2 comptes + 2 élèves + 1 classe = 6
    assert run["created"] == 6 and run["status"] == "ok"

    # statut passe à connected + seats_used reflète les élèves
    status = client.get("/admin/integration").json()
    assert status["integration"]["status"] == "connected"
    assert status["organization"]["seats_used"] == 2

    # historique
    runs = client.get("/admin/rostering/runs").json()["runs"]
    assert len(runs) == 1 and runs[0]["created"] == 6
    _clear()


def test_sync_without_integration_is_rejected():
    client, _ = _client(with_integration=False)
    r = client.post("/admin/rostering/sync")
    assert r.status_code == 400
    _clear()


def test_non_admin_is_forbidden():
    client, _ = _client(admin=False)
    assert client.get("/admin/integration").status_code == 403
    assert client.post("/admin/rostering/sync").status_code == 403
    assert client.get("/admin/rostering/runs").status_code == 403
    _clear()


def test_sync_failure_is_traced():
    client, engine = _client()

    def _boom_factory():
        def _f(integ):
            raise RuntimeError("google indisponible")
        return _f

    appmod.app.dependency_overrides[appmod.get_directory_factory] = _boom_factory
    r = client.post("/admin/rostering/sync")
    assert r.status_code == 502
    # l'échec est tracé sur l'intégration
    with Session(bind=engine) as s:
        integ = s.execute(select(TenantIntegration)).scalar_one()
        assert integ.status == "error" and "indisponible" in (integ.last_error or "")
    _clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
