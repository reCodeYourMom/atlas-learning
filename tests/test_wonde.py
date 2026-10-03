"""Tests adapter Wonde — mapping per-school + pagination curseur + passage dans le moteur.

Transport factice : routes Wonde servies en mémoire, avec une 2ᵉ page via meta.pagination.next.
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
from src.models.org import AppUser, Organization
from src.rostering.wonde import WondeAdapter
from src.rostering.sync import sync_directory

SID = "SCH99"


def _routes():
    return {
        f"/schools/{SID}/students": {"data": [
            {"id": "stu-1", "forename": "Sara", "surname": "K", "email": "sara@sch.edu"},
            {"id": "stu-2", "forename": "Ali", "surname": "M",
             "contact_details": {"data": {"email": "ali@sch.edu"}}},
        ]},
        f"/schools/{SID}/employees": {"data": [
            {"id": "emp-1", "forename": "Omar", "surname": "B", "email": "omar@sch.edu"},
        ]},
        f"/schools/{SID}/classes": {"data": [
            {"id": "cls-1", "name": "Maths 4A",
             "students": {"data": [{"id": "stu-1"}, {"id": "stu-2"}]},
             "employees": {"data": [{"id": "emp-1"}]}},
        ]},
    }


def _transport(routes, paginate_students=False):
    def _get(path, params):
        # 2ᵉ page d'élèves via curseur next (test de pagination)
        if path == "__next_students__":
            return {"data": [{"id": "stu-3", "forename": "Z", "surname": "Z",
                              "email": "z@sch.edu"}]}
        body = dict(routes.get(path, {"data": []}))
        if paginate_students and path == f"/schools/{SID}/students":
            body = dict(body)
            body["meta"] = {"pagination": {"next": "__next_students__"}}
        return body
    return _get


def test_snapshot_maps_school_users_classes():
    snap = WondeAdapter(_transport(_routes()), SID, school_name="École A").snapshot()
    assert [o.external_id for o in snap.org_units] == [SID]
    roles = {u.external_id: u.role for u in snap.users}
    assert roles == {"stu-1": Role.STUDENT, "stu-2": Role.STUDENT, "emp-1": Role.TEACHER}
    # email pris dans contact_details quand absent au niveau racine
    assert next(u.email for u in snap.users if u.external_id == "stu-2") == "ali@sch.edu"
    assert [g.external_id for g in snap.groups] == ["cls-1"]
    assert len(snap.memberships) == 3      # 2 élèves + 1 prof dans la classe


def test_fallback_email_is_stable():
    routes = _routes()
    routes[f"/schools/{SID}/students"]["data"].append(
        {"id": "stu-noemail", "forename": "N", "surname": "E"})   # aucun email
    snap = WondeAdapter(_transport(routes), SID).snapshot()
    u = next(u for u in snap.users if u.external_id == "stu-noemail")
    assert u.email == "stu-noemail@wonde.local"   # déterministe, ancré sur l'id Wonde


def test_pagination_follows_next_cursor():
    snap = WondeAdapter(_transport(_routes(), paginate_students=True), SID).snapshot()
    assert {u.external_id for u in snap.users if u.role == Role.STUDENT} == {"stu-1", "stu-2", "stu-3"}


def test_engine_provisions_from_wonde():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    org = Organization(name="École A", domain="sch.edu"); s.add(org); s.flush()
    snap = WondeAdapter(_transport(_routes()), SID, school_name="École A").snapshot()
    run = sync_directory(s, org, snap); s.commit()
    assert run.status == "ok"
    assert s.execute(select(School).where(School.external_ref == SID)).scalar_one()
    assert s.execute(select(AppUser).where(AppUser.email == "omar@sch.edu")).scalar_one()
    assert s.execute(select(Student).where(Student.external_ref == "stu-1")).scalar_one()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
