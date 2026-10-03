"""Tests Epic 6 — RBAC (T6.2) + auth minimal (T6.3)."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from src.db import make_engine
from src.models.base import Base, Role
# importe tous les modules de modèles pour enregistrer les tables (FK cross-module)
from src.models import competency as _c, item as _i, measurement as _m, session as _se, org as _o  # noqa: F401
from src.models.measurement import School, Student
from src.models.org import AppUser, Membership, ParentStudent, TeacherClassroom
from src.rbac.auth import make_token, parse_token
from src.rbac.authz import (
    UserContext,
    build_user_context,
    can_access_classroom,
    can_access_school,
    can_access_student,
)

SCHOOL_A, SCHOOL_B = uuid.uuid4(), uuid.uuid4()
CLASS_1, CLASS_2 = uuid.uuid4(), uuid.uuid4()
CHILD, OTHER = uuid.uuid4(), uuid.uuid4()


# ---------- T6.2 RBAC ----------

def test_ac1_parent_cannot_access_other_child():
    parent = UserContext(uuid.uuid4(), roles=frozenset({Role.PARENT}), child_student_ids=frozenset({CHILD}))
    assert can_access_student(parent, CHILD, SCHOOL_A, {CLASS_1}) is True
    assert can_access_student(parent, OTHER, SCHOOL_A, {CLASS_1}) is False   # autre enfant → refus


def test_ac2_teacher_cannot_access_other_class():
    teacher = UserContext(uuid.uuid4(), roles=frozenset({Role.TEACHER}), classroom_ids=frozenset({CLASS_1}))
    assert can_access_classroom(teacher, CLASS_1, SCHOOL_A) is True
    assert can_access_classroom(teacher, CLASS_2, SCHOOL_A) is False       # pas sa classe → refus


def test_ac3_student_only_own_activities():
    student = UserContext(uuid.uuid4(), roles=frozenset({Role.STUDENT}), own_student_id=CHILD)
    assert can_access_student(student, CHILD, SCHOOL_A, {CLASS_1}) is True
    assert can_access_student(student, OTHER, SCHOOL_A, {CLASS_1}) is False


def test_teacher_access_student_via_any_shared_class():
    """Élève multi-classes : le prof y accède s'il partage AU MOINS une classe."""
    teacher = UserContext(uuid.uuid4(), roles=frozenset({Role.TEACHER}),
                          classroom_ids=frozenset({CLASS_1}))
    # élève en CLASS_2 (principale) + CLASS_1 (spécialité du prof) → accès
    assert can_access_student(teacher, CHILD, SCHOOL_A, {CLASS_2, CLASS_1}) is True
    # élève seulement en CLASS_2 → refus
    assert can_access_student(teacher, CHILD, SCHOOL_A, {CLASS_2}) is False


def test_ac4_ped_admin_tenant_isolation():
    admin = UserContext(uuid.uuid4(), roles=frozenset({Role.PED_ADMIN}), school_ids=frozenset({SCHOOL_A}))
    assert can_access_school(admin, SCHOOL_A) is True
    assert can_access_school(admin, SCHOOL_B) is False                     # autre établissement → refus
    assert can_access_student(admin, CHILD, SCHOOL_A, {CLASS_1}) is True
    assert can_access_student(admin, CHILD, SCHOOL_B, {CLASS_1}) is False


def test_super_admin_sees_all():
    su = UserContext(uuid.uuid4(), roles=frozenset({Role.SUPER_ADMIN}))
    assert can_access_school(su, SCHOOL_B) is True
    assert can_access_student(su, OTHER, SCHOOL_B, {CLASS_2}) is True


def test_build_user_context_from_db():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = Session(engine)
    school = School(name="A"); s.add(school); s.flush()
    teacher = AppUser(email="t@x.io"); s.add(teacher); s.flush()
    from src.models.org import Classroom
    cls = Classroom(school_id=school.id, name="4A"); s.add(cls); s.flush()
    s.add(Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id))
    s.add(TeacherClassroom(user_id=teacher.id, classroom_id=cls.id))
    s.commit()
    ctx = build_user_context(s, teacher.id)
    assert Role.TEACHER in ctx.roles
    assert cls.id in ctx.classroom_ids
    assert school.id in ctx.school_ids


# ---------- T6.3 auth (jetons de session signés — SSO uniquement) ----------

def test_token_roundtrip_and_tamper():
    uid = str(uuid.uuid4())
    tok = make_token(uid, ttl_s=100, now=1000)
    assert parse_token(tok, now=1050) == uid
    # falsification de signature
    try:
        parse_token(tok[:-1] + ("0" if tok[-1] != "0" else "1"), now=1050)
        assert False
    except ValueError:
        pass


def test_token_expiry():
    tok = make_token("u", ttl_s=100, now=1000)
    try:
        parse_token(tok, now=2000)   # expiré
        assert False
    except ValueError:
        pass


def test_token_purpose_isolation():
    """Un lien magique (purpose dédié) ne doit pas passer pour un jeton de session."""
    magic = make_token("u", purpose="admin_login", ttl_s=100, now=1000)
    assert parse_token(magic, purpose="admin_login", now=1050) == "u"
    try:
        parse_token(magic, purpose="session", now=1050)   # mauvais usage
        assert False
    except ValueError:
        pass


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
