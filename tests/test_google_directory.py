"""Tests de l'adapter Google Admin SDK (Phase B) — mapping + pagination, sans réseau.

Le transport est factice (JSON canned) : on teste la traduction JSON Directory →
DirectorySnapshot, la pagination, les flags admin/suspendu, et le branchement sur le
moteur Phase A. `google-auth` n'est jamais requis ici (transport injecté).
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School, Student
from src.models.org import AppUser, Classroom, Organization, StudentClassroom
from src.rostering.directory import (
    DirectorySnapshot, DirGuardian, DirOrgUnit, DirUser, FakeDirectory,
)
from src.rostering.google import (
    CompositeDirectory, GoogleClassroomGuardians, GoogleDirectoryAdapter,
)
from src.rostering.sync import sync_directory


def _fake_transport(responses):
    """responses : { path: [page1, page2, ...] } servis successivement (simule pageToken)."""
    calls = {}

    def _get(path, params):
        i = calls.get(path, 0)
        pages = responses.get(path, [{}])
        calls[path] = i + 1
        return pages[min(i, len(pages) - 1)]

    return _get


def _adapter():
    responses = {
        "/customer/my_customer/orgunits": [{
            "organizationUnits": [
                {"orgUnitPath": "/Students", "name": "Students", "parentOrgUnitPath": "/"},
                {"orgUnitPath": "/Staff", "name": "Staff"},
            ]
        }],
        "/users": [
            {"users": [{"id": "u1", "primaryEmail": "Alice@s.edu",
                        "name": {"fullName": "Alice"}, "orgUnitPath": "/Students"}],
             "nextPageToken": "t2"},                                   # page 1
            {"users": [
                {"id": "u2", "primaryEmail": "carol@s.edu", "name": {"fullName": "Carol"},
                 "orgUnitPath": "/Staff", "isAdmin": True},
                {"id": "u3", "primaryEmail": "sus@s.edu", "orgUnitPath": "/Students",
                 "suspended": True},
            ]},                                                        # page 2 (pas de token)
        ],
        "/groups": [{"groups": [{"id": "g1", "email": "4a@s.edu", "name": "Grade 4A"}]}],
        "/groups/g1/members": [{"members": [
            {"id": "u1", "email": "alice@s.edu", "type": "USER"},
            {"id": "gX", "type": "GROUP"},                             # imbriqué → ignoré
        ]}],
    }
    return GoogleDirectoryAdapter(_fake_transport(responses), customer="my_customer")


def test_snapshot_maps_and_paginates():
    snap = _adapter().snapshot()

    assert {o.external_id for o in snap.org_units} == {"/Students", "/Staff"}
    # pagination : les 3 users des 2 pages sont collectés
    by_id = {u.external_id: u for u in snap.users}
    assert set(by_id) == {"u1", "u2", "u3"}
    assert by_id["u1"].full_name == "Alice" and by_id["u1"].org_unit_external_id == "/Students"
    assert by_id["u2"].is_admin is True
    assert by_id["u3"].suspended is True

    assert len(snap.groups) == 1 and snap.groups[0].external_id == "g1"
    # seul l'utilisateur (pas le groupe imbriqué) est inscrit
    assert snap.memberships == [type(snap.memberships[0])("g1", "u1")]
    assert snap.members_of("g1") == ["u1"]


def test_adapter_feeds_sync_engine():
    """L'adapter Phase B se branche tel quel sur le moteur Phase A (classifieur par défaut)."""
    engine = make_engine(f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    org = Organization(name="S", domain="s.edu"); s.add(org); s.flush(); s.commit()

    run = sync_directory(s, org, _adapter().snapshot()); s.commit()

    # /Students + /Staff → 2 écoles ; alice + carol + u3 → 3 comptes ; alice + u3 → 2 élèves ; g1 → 1 classe
    assert run.created_count == 8, run.summary

    alice = s.execute(select(AppUser).where(AppUser.email == "alice@s.edu")).scalar_one()
    st = s.execute(select(Student).where(Student.user_id == alice.id)).scalar_one()
    g1 = s.execute(select(Classroom).where(Classroom.external_ref == "g1")).scalar_one()
    enrolled = set(s.execute(
        select(StudentClassroom.classroom_id).where(StudentClassroom.student_id == st.id)
    ).scalars())
    assert enrolled == {g1.id}

    carol = s.execute(select(AppUser).where(AppUser.email == "carol@s.edu")).scalar_one()
    from src.models.org import Membership
    roles = set(s.execute(select(Membership.role).where(Membership.user_id == carol.id)).scalars())
    assert Role.IT_ADMIN in roles

    # compte suspendu → AppUser inactif
    sus = s.execute(select(AppUser).where(AppUser.email == "sus@s.edu")).scalar_one()
    assert sus.is_active is False


def test_classroom_guardians_mapping():
    responses = {
        "/v1/userProfiles/u1/guardians": [{"guardians": [
            {"studentId": "u1", "guardianId": "g1",
             "guardianProfile": {"emailAddress": "Mom@home.com", "name": {"fullName": "Mom"}}}]}],
        "/v1/userProfiles/u2/guardians": [{"guardians": []}],   # aucun tuteur
    }
    out = GoogleClassroomGuardians(_fake_transport(responses)).guardians_for(["u1", "u2"])
    assert len(out) == 1
    assert out[0].student_external_id == "u1" and out[0].email == "Mom@home.com"
    assert out[0].external_id == "g1" and out[0].full_name == "Mom"


def test_composite_enriches_only_students():
    base = FakeDirectory(DirectorySnapshot(
        [DirOrgUnit("ou_s", "Students"), DirOrgUnit("ou_t", "Staff")],
        [DirUser("u1", "s@x.edu", "S", "ou_s"), DirUser("t1", "t@x.edu", "T", "ou_t")],
        [], []))
    requested = []

    class _Src:
        def guardians_for(self, ids):
            requested.extend(ids)
            return [DirGuardian("u1", "mom@home.com", "Mom", "g1")]

    snap = CompositeDirectory(base, _Src()).snapshot()
    assert requested == ["u1"]                       # seul l'élève est interrogé (pas le staff)
    assert snap.guardians == [DirGuardian("u1", "mom@home.com", "Mom", "g1")]


def test_composite_falls_back_when_guardians_unavailable():
    base = FakeDirectory(DirectorySnapshot(
        [DirOrgUnit("ou_s", "Students")], [DirUser("u1", "s@x.edu", "S", "ou_s")], [], []))

    class _Boom:
        def guardians_for(self, ids):
            raise RuntimeError("classroom indisponible")

    snap = CompositeDirectory(base, _Boom()).snapshot()
    assert snap.guardians is None                     # résilient : la sync ne touche pas aux parents


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
