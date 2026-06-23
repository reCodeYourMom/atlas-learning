"""Tests adapter OneRoster CSV — parse dossier + ZIP, réutilise le mapping REST.

Vérifie : colonnes CSV → snapshot identique au REST, orgSourcedIds multi-séparateurs,
lecture ZIP (avec sous-dossier), et passage dans le moteur de sync.
"""
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import make_engine
from src.models.base import Base, Role
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401,E501
from src.models.measurement import School, Student
from src.models.org import AppUser, Organization
from src.rostering import oneroster_csv

_ORGS = "sourcedId,status,type,name,parentSourcedId\ndist-1,active,district,District,\nsch-1,active,school,École A,dist-1\n"
_USERS = (
    "sourcedId,status,role,givenName,familyName,email,orgSourcedIds\n"
    "u-stud,active,student,Sara,K,sara@sch.edu,sch-1\n"
    "u-teach,active,teacher,Omar,B,omar@sch.edu,sch-1\n"
    "u-par,active,parent,P,P,p@x.io,sch-1\n"
)
_CLASSES = "sourcedId,status,title,schoolSourcedId\ncls-1,active,Maths 4A,sch-1\n"
_ENR = (
    "sourcedId,status,role,classSourcedId,schoolSourcedId,userSourcedId\n"
    "e1,active,student,cls-1,sch-1,u-stud\n"
    "e2,active,teacher,cls-1,sch-1,u-teach\n"
)


def _write_bundle(d):
    for name, content in [("orgs.csv", _ORGS), ("users.csv", _USERS),
                          ("classes.csv", _CLASSES), ("enrollments.csv", _ENR)]:
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(content)


def test_from_dir_maps_to_snapshot():
    d = tempfile.mkdtemp()
    _write_bundle(d)
    snap = oneroster_csv.from_dir(d).snapshot()
    assert [o.external_id for o in snap.org_units] == ["sch-1"]
    refs = {u.external_id: u.role for u in snap.users}
    assert refs == {"u-stud": Role.STUDENT, "u-teach": Role.TEACHER}   # parent exclu
    assert [g.external_id for g in snap.groups] == ["cls-1"]
    assert len(snap.memberships) == 2


def test_orgsourcedids_space_separated():
    d = tempfile.mkdtemp()
    _write_bundle(d)
    with open(os.path.join(d, "users.csv"), "w", encoding="utf-8") as f:
        f.write("sourcedId,status,role,givenName,familyName,email,orgSourcedIds\n"
                "u1,active,student,A,B,a@s.edu,sch-9 sch-1\n")   # séparé par espace
    snap = oneroster_csv.from_dir(d).snapshot()
    # sch-1 est la seule école connue → c'est elle qui est retenue malgré l'ordre
    assert snap.users[0].org_unit_external_id == "sch-1"


def test_from_zip_with_subfolder():
    d = tempfile.mkdtemp()
    zp = os.path.join(d, "bundle.zip")
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("export/orgs.csv", _ORGS)       # sous-dossier dans le zip
        z.writestr("export/users.csv", _USERS)
        z.writestr("export/classes.csv", _CLASSES)
        z.writestr("export/enrollments.csv", _ENR)
    snap = oneroster_csv.from_zip(zp).snapshot()
    assert {u.external_id for u in snap.users} == {"u-stud", "u-teach"}


def test_engine_provisions_from_csv():
    from src.rostering.sync import sync_directory
    d = tempfile.mkdtemp(); _write_bundle(d)
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    org = Organization(name="District", domain="sch.edu"); s.add(org); s.flush()
    run = sync_directory(s, org, oneroster_csv.from_dir(d).snapshot()); s.commit()
    assert run.status == "ok"
    assert s.execute(select(School).where(School.external_ref == "sch-1")).scalar_one()
    assert s.execute(select(AppUser).where(AppUser.email == "sara@sch.edu")).scalar_one()
    assert s.execute(select(Student).where(Student.external_ref == "u-stud")).scalar_one()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
