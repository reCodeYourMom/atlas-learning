"""Tests conformité PDPL (Phase E) — audit, export, droit à l'oubli, purge, RBAC."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.audit import log_action
from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School, Student
from src.models.org import (
    AppUser, Classroom, Membership, Organization, StudentClassroom, TenantIntegration,
)
from src.rbac.auth import make_token
import src.api.app as appmod


def _make_student(s, school, cls, org, email, ref):
    u = AppUser(email=email, external_ref=ref); s.add(u); s.flush()
    st = Student(school_id=school.id, classroom_id=cls.id, user_id=u.id, external_ref=ref)
    s.add(st); s.flush()
    s.add(StudentClassroom(student_id=st.id, classroom_id=cls.id))
    s.add(Membership(user_id=u.id, role=Role.STUDENT, organization_id=org.id))
    return u, st


def _client(admin=True):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    ids = {}
    with Session(bind=engine) as s:
        org = Organization(name="School", domain="school.edu"); s.add(org); s.flush()
        admin_user = AppUser(email="it@school.edu"); s.add(admin_user); s.flush()
        s.add(Membership(user_id=admin_user.id,
                         role=Role.IT_ADMIN if admin else Role.STUDENT,
                         organization_id=org.id if admin else None))
        school = School(name="S1", organization_id=org.id); s.add(school); s.flush()
        cls = Classroom(school_id=school.id, name="4A"); s.add(cls); s.flush()
        _, st1 = _make_student(s, school, cls, org, "alice@school.edu", "S1")
        _make_student(s, school, cls, org, "bob@school.edu", "S2")
        s.add(TenantIntegration(organization_id=org.id, admin_email="it@school.edu"))
        # quelques entrées d'audit (par user et par école)
        log_action(s, action="auth.login", user_id=admin_user.id)
        log_action(s, action="classroom.view_gaps", school_id=school.id, user_id=admin_user.id)

        # second tenant (pour tester l'isolation de l'effacement)
        org2 = Organization(name="Other", domain="other.edu"); s.add(org2); s.flush()
        sch2 = School(name="S2", organization_id=org2.id); s.add(sch2); s.flush()
        cls2 = Classroom(school_id=sch2.id, name="X"); s.add(cls2); s.flush()
        _, other_st = _make_student(s, sch2, cls2, org2, "ext@other.edu", "X1")

        s.commit()
        ids["student1"] = str(st1.id)
        ids["other_student"] = str(other_st.id)
        token = make_token(str(admin_user.id))

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    client = TestClient(appmod.app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, engine, ids


def _clear():
    appmod.app.dependency_overrides.clear()


def test_audit_view_scoped_to_tenant():
    client, _, _ = _client()
    entries = client.get("/admin/audit").json()["entries"]
    actions = {e["action"] for e in entries}
    assert {"auth.login", "classroom.view_gaps"} <= actions
    _clear()


def test_export_bundles_tenant_data():
    client, _, _ = _client()
    exp = client.get("/admin/export").json()
    assert exp["organization"]["domain"] == "school.edu"
    assert len(exp["schools"]) == 1 and len(exp["classrooms"]) == 1
    emails = {u["email"] for u in exp["users"]}
    assert {"it@school.edu", "alice@school.edu", "bob@school.edu"} <= emails
    assert len(exp["students"]) == 2
    _clear()


def test_erase_student_removes_subject_and_cascades():
    client, engine, ids = _client()
    r = client.post(f"/admin/students/{ids['student1']}/erase")
    assert r.status_code == 200 and r.json()["erased_user"] is True
    with Session(bind=engine) as s:
        assert s.get(Student, __import__("uuid").UUID(ids["student1"])) is None
        assert s.execute(select(AppUser).where(AppUser.email == "alice@school.edu")
                         ).scalar_one_or_none() is None          # email (PII) effacé
        # inscriptions de l'élève effacées par cascade
        n = s.execute(select(func.count()).select_from(StudentClassroom)).scalar()
        assert n == 2   # restait alice+bob (2 lignes) → alice retirée ? bob (1) + other (1) = 2
    _clear()


def test_erase_student_isolation_other_tenant():
    client, _, ids = _client()
    r = client.post(f"/admin/students/{ids['other_student']}/erase")
    assert r.status_code == 404  # élève d'un autre tenant → refus
    _clear()


def test_erase_tenant_requires_domain_confirmation():
    client, engine, _ = _client()
    assert client.post("/admin/tenant/erase", json={"confirm_domain": "wrong.edu"}).status_code == 400
    r = client.post("/admin/tenant/erase", json={"confirm_domain": "school.edu"})
    assert r.status_code == 200
    with Session(bind=engine) as s:
        assert s.execute(select(Organization).where(Organization.domain == "school.edu")
                         ).scalar_one_or_none() is None
        # comptes du tenant effacés ; l'autre tenant intact
        assert s.execute(select(AppUser).where(AppUser.email == "it@school.edu")
                         ).scalar_one_or_none() is None
        assert s.execute(select(Organization).where(Organization.domain == "other.edu")
                         ).scalar_one_or_none() is not None
    _clear()


def test_compliance_endpoints_require_it_admin():
    client, _, ids = _client(admin=False)
    assert client.get("/admin/audit").status_code == 403
    assert client.get("/admin/export").status_code == 403
    assert client.post(f"/admin/students/{ids['student1']}/erase").status_code == 403
    _clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
