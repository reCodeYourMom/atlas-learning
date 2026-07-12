"""Provision PROD idempotent : tenant + comptes (alignés Keycloak) + données des 4 mouvements.

Différences avec seed_demo_movements (qui recrée une SQLite locale) :
  - utilise la base configurée (`DATABASE_URL`), schéma déjà migré par Alembic (pas de create_all) ;
  - idempotent : si admin@demo.atlas existe déjà, on ne refait rien ;
  - emails = ceux du realm Keycloak (admin@/prof@/parent@demo.atlas) → le login OIDC retrouve l'user.

Lancé au boot du backend si PROVISION_ON_BOOT=1 (cf. entrypoint-backend.sh).
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.models.base import (
    AnswerFormat, CompetencyStatus, EdgeType, ItemStatus, Role, Subject, WeightSource,
    utcnow,
)
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import (
    AppUser, Classroom, Membership, Organization, ParentStudent, StudentClassroom, TeacherClassroom,
)

ADMIN, TEACHER, PARENT = "admin@demo.atlas", "prof@demo.atlas", "parent@demo.atlas"

COMPS = [
    ("FRAC.NAME",       "Name a fraction",            "تسمية الكسر",            2, 1200),
    ("FRAC.EQUIV",      "Equivalent fractions",       "الكسور المكافئة",        3, 1400),
    ("FRAC.SIMPLIFY",   "Simplify fractions",         "تبسيط الكسور",           4, 1500),
    ("FRAC.COMPARE",    "Compare fractions",          "مقارنة الكسور",          4, 1500),
    ("FRAC.ADD_SAME",   "Add (same denominator)",     "الجمع (مقام مشترك)",     4, 1500),
    ("FRAC.ADD_UNLIKE", "Add (unlike denominators)",  "الجمع (مقامات مختلفة)",  5, 1700),
]
HARD = [
    ("FRAC.NAME", "FRAC.EQUIV"), ("FRAC.EQUIV", "FRAC.SIMPLIFY"), ("FRAC.EQUIV", "FRAC.COMPARE"),
    ("FRAC.NAME", "FRAC.ADD_SAME"), ("FRAC.SIMPLIFY", "FRAC.ADD_UNLIKE"), ("FRAC.ADD_SAME", "FRAC.ADD_UNLIKE"),
]


def _item(comp_id, en, ar, status=ItemStatus.ACTIVE, ar_validated=True):
    it = Item(competency_id=comp_id, answer_format=AnswerFormat.MCQ, difficulty_prior=1400.0,
              status=status,
              content_en={"stem": en, "options": ["3/4", "2/6", "1/2"], "answer": "3/4"})
    if status == ItemStatus.ACTIVE or ar_validated:
        it.content_ar = {"stem": ar, "options": ["3/4", "2/6", "1/2"], "answer": "3/4"}
        it.ar_validated = True
    return it


def main():
    engine = make_engine()
    now = utcnow()
    old, recent = now - timedelta(days=40), now - timedelta(days=3)
    with SessionLocal(bind=engine) as s:
        if s.execute(select(AppUser).where(AppUser.email == ADMIN)).scalar_one_or_none():
            print("[provision] déjà en place — rien à faire (idempotent).")
            return

        org = Organization(name="Demo Org", domain="demo.atlas"); s.add(org); s.flush()
        school = School(name="Demo School", organization_id=org.id); s.add(school); s.flush()
        cls = Classroom(school_id=school.id, name="Grade 4 — A"); s.add(cls); s.flush()

        comp = {}
        for code, en, ar, grade, diff in COMPS:
            c = Competency(code=code, label_en=en, label_ar=ar, subject=Subject.MATH, grade=grade,
                           difficulty_prior=float(diff), status=CompetencyStatus.ACTIVE)
            s.add(c); s.flush(); comp[code] = c
        for sc, tc in HARD:
            s.add(CompetencyPrerequisite(source_id=comp[sc].id, target_id=comp[tc].id,
                                         edge_type=EdgeType.HARD, correlation_strength=0.8,
                                         weight_source=WeightSource.EXPERT))

        items_by_comp = {}
        for code, c in comp.items():
            it = _item(c.id, f"[{c.label_en}] Which is correct?", f"[{c.label_ar}] أيّها صحيح؟")
            s.add(it); s.flush(); items_by_comp[code] = it
        for code in ("FRAC.SIMPLIFY", "FRAC.COMPARE", "FRAC.ADD_UNLIKE"):
            s.add(_item(comp[code].id, f"Pending-AR item for {code}", "",
                        status=ItemStatus.HUMAN_REVIEWED, ar_validated=False))

        admin = AppUser(email=ADMIN); teacher = AppUser(email=TEACHER); parent = AppUser(email=PARENT)
        s.add_all([admin, teacher, parent]); s.flush()
        s.add_all([
            Membership(user_id=admin.id, role=Role.PED_ADMIN, school_id=school.id),
            Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id),
            TeacherClassroom(user_id=teacher.id, classroom_id=cls.id),
            Membership(user_id=parent.id, role=Role.PARENT, school_id=school.id),
        ])

        students = []
        for i in range(8):
            u = AppUser(email=f"eleve{i+1}@demo.atlas"); s.add(u); s.flush()
            st = Student(school_id=school.id, classroom_id=cls.id, user_id=u.id, external_ref=f"S{i+1}")
            s.add(st); s.flush()
            s.add(StudentClassroom(student_id=st.id, classroom_id=cls.id))
            s.add(Membership(user_id=u.id, role=Role.STUDENT))
            students.append(st)
            gap = i < 6
            plan = {
                "FRAC.NAME": (1750, old), "FRAC.ADD_SAME": (1650, old),
                "FRAC.EQUIV": (1250 if gap else 1600, recent),
                "FRAC.SIMPLIFY": (1300 if gap else 1650, recent),
                "FRAC.COMPARE": (1450 if gap else 1700, recent),
                "FRAC.ADD_UNLIKE": (1200 if gap else 1620, recent),
            }
            for code, (elo, when) in plan.items():
                s.add(StudentCompetencyAbility(student_id=st.id, competency_id=comp[code].id,
                                               school_id=school.id, ability_elo=float(elo),
                                               n_direct=6, confidence=0.62, last_measured_at=when))
            for code in ("FRAC.EQUIV", "FRAC.SIMPLIFY", "FRAC.ADD_UNLIKE"):
                it = items_by_comp[code]
                for k in range(3):
                    s.add(Response(school_id=school.id, student_id=st.id, item_id=it.id,
                                   competency_id=comp[code].id, is_correct=(k == 0), created_at=old))
                for k in range(3):
                    s.add(Response(school_id=school.id, student_id=st.id, item_id=it.id,
                                   competency_id=comp[code].id, is_correct=(k != 0), created_at=recent))

        s.add(ParentStudent(user_id=parent.id, student_id=students[0].id, source="staff"))
        s.commit()
        print(f"[provision] tenant créé — école={school.id} classe={cls.id} enfant={students[0].id}")
        print(f"[provision] comptes Keycloak attendus : {ADMIN} / {TEACHER} / {PARENT}")


if __name__ == "__main__":
    main()
