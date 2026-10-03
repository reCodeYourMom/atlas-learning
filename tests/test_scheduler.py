"""Tests planificateur rostering (Phase D) — tournée multi-tenants, filtre, isolation d'erreur."""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import make_engine
from src.models.base import Base
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.org import Organization, TenantIntegration
from src.rostering.directory import (
    DirectorySnapshot, DirGroup, DirMembership, DirOrgUnit, DirUser, FakeDirectory,
)
from src.rostering.scheduler import sync_all

NOW = datetime(2026, 1, 1, 2, 0, 0)


def _snap(prefix):
    return DirectorySnapshot(
        [DirOrgUnit("ou_s", "Students")],
        [DirUser(f"{prefix}_a", f"a@{prefix}.edu", "A", "ou_s")],
        [DirGroup(f"{prefix}_g", "Class")],
        [DirMembership(f"{prefix}_g", f"{prefix}_a")],
    )


def _setup(n=2):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    for i in range(n):
        org = Organization(name=f"org{i}", domain=f"d{i}.edu"); s.add(org); s.flush()
        s.add(TenantIntegration(organization_id=org.id, status="connected",
                                admin_email=f"it@d{i}.edu"))
    s.commit()
    return s


def _factory(integ):
    return FakeDirectory(_snap(f"t{integ.organization_id.int % 1000}"))


def test_sync_all_runs_every_connected_tenant():
    s = _setup(2)
    results = sync_all(s, _factory, now=NOW)
    assert len(results) == 2
    assert all(r.status == "ok" for r in results)
    # chaque intégration est passée à connected + horodatée
    for integ in s.execute(select(TenantIntegration)).scalars():
        assert integ.last_sync_at == NOW


def test_due_before_skips_recently_synced():
    s = _setup(1)
    sync_all(s, _factory, now=NOW)                         # 1re sync à NOW
    again = sync_all(s, _factory, now=NOW, due_before=NOW)  # déjà syncé à NOW → ignoré
    assert again == []


def test_error_on_one_tenant_does_not_stop_others():
    s = _setup(2)
    orgs = list(s.execute(select(Organization).order_by(Organization.name)).scalars())
    bad_org_id = orgs[0].id

    def _factory_one_bad(integ):
        if integ.organization_id == bad_org_id:
            raise RuntimeError("boom")
        return FakeDirectory(_snap("ok"))

    results = sync_all(s, _factory_one_bad, now=NOW)
    statuses = sorted(r.status for r in results)
    assert statuses == ["error", "ok"]                    # l'un échoue, l'autre passe
    bad = s.get(TenantIntegration, s.execute(
        select(TenantIntegration.id).where(TenantIntegration.organization_id == bad_org_id)
    ).scalar_one())
    assert bad.status == "error" and "boom" in (bad.last_error or "")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
