"""Tests soft delete filtré (revue sécurité 2026-07-07).

Un élève soft-deleted — ou dont l'école/la classe est soft-deleted — ne doit plus être
accessible par AUCUN endpoint : sessions, fiche/trajectoire, listes de classe, espace
parent, vues école. Avant le correctif, `_authorize_student` ignorait `deleted_at`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db
from src.models import competency as _c, item as _i, measurement as _m, org as _o, session as _se  # noqa: F401,E501
from src.models.base import Base, CompetencyStatus, Role, Subject, utcnow
from src.models.competency import Competency
from src.models.measurement import School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Classroom, Membership, ParentStudent, TeacherClassroom
from src.rbac.auth import make_token


def _client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    school = School(name="S"); s.add(school); s.flush()
    cls = Classroom(school_id=school.id, name="4A"); s.add(cls); s.flush()
    alive = Student(school_id=school.id, classroom_id=cls.id, external_ref="ALIVE")
    gone = Student(school_id=school.id, classroom_id=cls.id, external_ref="GONE",
                   deleted_at=utcnow())                           # élève soft-deleted
    s.add_all([alive, gone]); s.flush()
    teacher = AppUser(email="prof@s.io"); s.add(teacher); s.flush()
    s.add_all([Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id),
               TeacherClassroom(user_id=teacher.id, classroom_id=cls.id)])
    parent = AppUser(email="mom@home.com"); s.add(parent); s.flush()
    s.add_all([Membership(user_id=parent.id, role=Role.PARENT),
               ParentStudent(user_id=parent.id, student_id=gone.id)])
    ped = AppUser(email="ped@s.io"); s.add(ped); s.flush()
    s.add(Membership(user_id=ped.id, role=Role.PED_ADMIN, school_id=school.id))
    s.commit()
    ids = dict(school=school.id, cls=cls.id, alive=alive.id, gone=gone.id,
               teacher=make_token(str(teacher.id)), parent=make_token(str(parent.id)),
               ped=make_token(str(ped.id)))
    s.close()
    app.dependency_overrides[get_db] = lambda: Session(bind=engine)
    return TestClient(app), engine, ids


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- élève soft-deleted : plus AUCUN accès ----------

def test_soft_deleted_student_profile_and_trajectory_404():
    client, _, ids = _client()
    assert client.get(f"/students/{ids['gone']}/profile", headers=_h(ids["teacher"])).status_code == 404
    assert client.get(f"/students/{ids['gone']}/trajectory", headers=_h(ids["teacher"])).status_code == 404
    app.dependency_overrides.clear()


def test_soft_deleted_student_cannot_start_session():
    client, _, ids = _client()
    r = client.post("/sessions", json={"student_id": str(ids["gone"])}, headers=_h(ids["teacher"]))
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_soft_deleted_student_hidden_from_parent():
    client, _, ids = _client()
    r = client.get("/parent/children", headers=_h(ids["parent"]))
    assert r.status_code == 200 and r.json()["children"] == []          # enfant masqué
    assert client.get(f"/students/{ids['gone']}/trajectory",
                      headers=_h(ids["parent"])).status_code == 404     # accès direct refusé
    app.dependency_overrides.clear()


def test_soft_deleted_student_excluded_from_class_list():
    client, _, ids = _client()
    r = client.get(f"/classrooms/{ids['cls']}/students", headers=_h(ids["teacher"]))
    assert r.status_code == 200
    listed = {st["external_ref"] for st in r.json()["students"]}
    assert "ALIVE" in listed and "GONE" not in listed
    app.dependency_overrides.clear()


def test_alive_student_still_accessible():
    client, _, ids = _client()
    assert client.get(f"/students/{ids['alive']}/profile", headers=_h(ids["teacher"])).status_code == 200
    app.dependency_overrides.clear()


# ---------- compte utilisateur soft-deleted / désactivé : jeton refusé ----------

def test_bearer_of_deleted_or_inactive_user_401():
    # Revue 2026-07-08 : le jeton de session (TTL 1 h) survivait à l'offboarding —
    # get_context re-vérifie désormais l'état RÉEL du compte à CHAQUE requête.
    client, engine, ids = _client()
    with Session(bind=engine) as s:
        prof = s.execute(select(AppUser).where(AppUser.email == "prof@s.io")).scalar_one()
        prof.deleted_at = utcnow()                     # droit à l'oubli / départ
        ped = s.execute(select(AppUser).where(AppUser.email == "ped@s.io")).scalar_one()
        ped.is_active = False                          # désactivé (roster sync)
        s.commit()
    # jetons encore cryptographiquement valides → 401 quand même, immédiatement
    assert client.get(f"/students/{ids['alive']}/profile",
                      headers=_h(ids["teacher"])).status_code == 401
    assert client.get(f"/schools/{ids['school']}/overview",
                      headers=_h(ids["ped"])).status_code == 401
    app.dependency_overrides.clear()


# ---------- agrégats école : l'élève soft-deleted ne pèse plus ----------

def test_school_aggregates_exclude_soft_deleted_students():
    # Revue 2026-07-08 : overview et proof agrégeaient StudentCompetencyAbility par
    # school_id SEUL — les abilities d'un élève soft-deleted pesaient encore dans les
    # moyennes/taux de maîtrise (jointure Student.deleted_at IS NULL désormais).
    client, engine, ids = _client()
    with Session(bind=engine) as s:
        comp = Competency(code="M.X", label_en="x", label_ar="س", subject=Subject.MATH,
                          grade=4, difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
        s.add(comp); s.flush()
        s.add_all([  # deux abilities MESURÉES : vivant à 1600, soft-deleted à 900
            StudentCompetencyAbility(student_id=ids["alive"], competency_id=comp.id,
                                     school_id=ids["school"], ability_elo=1600.0,
                                     n_direct=5, confidence=0.5),
            StudentCompetencyAbility(student_id=ids["gone"], competency_id=comp.id,
                                     school_id=ids["school"], ability_elo=900.0,
                                     n_direct=5, confidence=0.5),
        ])
        s.commit()
    over = client.get(f"/schools/{ids['school']}/overview", headers=_h(ids["ped"])).json()
    row = next(c for c in over["competencies"] if c["code"] == "M.X")
    # avant le correctif : n_measured=2, mean=1250.0, mastery_rate=0.5
    assert row["n_measured"] == 1 and row["mean_ability"] == 1600.0
    assert row["mastery_rate"] == 1.0
    proof = client.get(f"/schools/{ids['school']}/proof", headers=_h(ids["ped"])).json()
    assert proof["n_students_measured"] == 1                      # le soft-deleted exclu
    assert proof["n_measured_skills"] == 1
    assert proof["n_mastered_skills"] == 1                        # 1600 ≥ seuil ; 900 exclu
    app.dependency_overrides.clear()


# ---------- classe / école soft-deleted ----------

def test_soft_deleted_classroom_404():
    client, engine, ids = _client()
    with Session(bind=engine) as s:
        s.get(Classroom, ids["cls"]).deleted_at = utcnow(); s.commit()
    assert client.get(f"/classrooms/{ids['cls']}/students", headers=_h(ids["teacher"])).status_code == 404
    assert client.get(f"/classrooms/{ids['cls']}/gaps", headers=_h(ids["teacher"])).status_code == 404
    assert client.get(f"/classrooms/{ids['cls']}/digest", headers=_h(ids["teacher"])).status_code == 404
    app.dependency_overrides.clear()


def test_soft_deleted_school_404_everywhere():
    client, engine, ids = _client()
    with Session(bind=engine) as s:
        s.get(School, ids["school"]).deleted_at = utcnow(); s.commit()
    # Vues école (admin pédagogique)
    assert client.get(f"/schools/{ids['school']}/overview", headers=_h(ids["ped"])).status_code == 404
    assert client.get(f"/schools/{ids['school']}/proof", headers=_h(ids["ped"])).status_code == 404
    # Les élèves d'une école supprimée deviennent inaccessibles aussi
    assert client.get(f"/students/{ids['alive']}/profile", headers=_h(ids["teacher"])).status_code == 404
    # ... et ses classes également
    assert client.get(f"/classrooms/{ids['cls']}/students", headers=_h(ids["teacher"])).status_code == 404
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
