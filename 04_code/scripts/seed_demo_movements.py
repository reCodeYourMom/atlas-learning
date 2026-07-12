"""Seed de démo pour VOIR les 4 mouvements du bench Alef→Atlas en vrai.

Construit une base SQLite fraîche (atlas_dev.db, la DB par défaut de l'app) avec exactement
ce que chaque mouvement a besoin d'afficher — déterministe, sans clé GROQ :

  M01  abilities à cause-racine (diagnostic) + lien parent (action 10 min) + réponses datées
       de cette semaine (digest + lacunes émergentes).
  M02  items ACTIFS bilingues + items en attente d'AR (worklist console linguiste).
  M03  réponses « avant » (>30j, ~50 %) vs « après » (<5j, ~85 %) → gains cohorte + projection.
  M04  chaînes de prérequis HARD → le tuteur causal a quelque chose à expliquer.

Usage :  .venv/bin/python scripts/seed_demo_movements.py
Comptes (auth dev sans mot de passe via /dev/login) :
  admin@demo.atlas (PED_ADMIN) · prof@demo.atlas (TEACHER) · parent@demo.atlas (PARENT)
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "atlas_dev.db"

from sqlalchemy import create_engine, event

from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, EdgeType, ItemStatus, Role, Subject, WeightSource,
    utcnow,
)
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import (
    AppUser, Classroom, Membership, Organization, ParentStudent, StudentClassroom, TeacherClassroom,
)
from sqlalchemy.orm import Session

NOW = utcnow()
OLD = NOW - timedelta(days=40)      # période « avant » (hors fenêtre 30j)
RECENT = NOW - timedelta(days=3)    # « cette semaine » (digest + après)

# Chaîne de compétences fractions, bilingue. (code, EN, AR, grade, difficulty)
COMPS = [
    ("FRAC.NAME",       "Name a fraction",            "تسمية الكسر",            2, 1200),
    ("FRAC.EQUIV",      "Equivalent fractions",       "الكسور المكافئة",        3, 1400),
    ("FRAC.SIMPLIFY",   "Simplify fractions",         "تبسيط الكسور",           4, 1500),
    ("FRAC.COMPARE",    "Compare fractions",          "مقارنة الكسور",          4, 1500),
    ("FRAC.ADD_SAME",   "Add (same denominator)",     "الجمع (مقام مشترك)",     4, 1500),
    ("FRAC.ADD_UNLIKE", "Add (unlike denominators)",  "الجمع (مقامات مختلفة)",  5, 1700),
]
# Arêtes HARD : (prérequis, dépendant)
HARD = [
    ("FRAC.NAME", "FRAC.EQUIV"),
    ("FRAC.EQUIV", "FRAC.SIMPLIFY"),
    ("FRAC.EQUIV", "FRAC.COMPARE"),
    ("FRAC.NAME", "FRAC.ADD_SAME"),
    ("FRAC.SIMPLIFY", "FRAC.ADD_UNLIKE"),
    ("FRAC.ADD_SAME", "FRAC.ADD_UNLIKE"),
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
    if DB_PATH.exists():
        DB_PATH.unlink()  # base de démo fraîche
    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    event.listen(engine, "connect", lambda c, r: c.cursor().execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)

    org = Organization(name="Demo Org", domain="demo.atlas"); s.add(org); s.flush()
    school = School(name="Demo School", organization_id=org.id); s.add(school); s.flush()
    cls = Classroom(school_id=school.id, name="Grade 4 — A"); s.add(cls); s.flush()

    comp = {}
    for code, en, ar, grade, diff in COMPS:
        c = Competency(code=code, label_en=en, label_ar=ar, subject=Subject.MATH, grade=grade,
                       difficulty_prior=float(diff), status=CompetencyStatus.ACTIVE)
        s.add(c); s.flush(); comp[code] = c
    for src_code, tgt_code in HARD:
        s.add(CompetencyPrerequisite(source_id=comp[src_code].id, target_id=comp[tgt_code].id,
                                     edge_type=EdgeType.HARD, correlation_strength=0.8,
                                     weight_source=WeightSource.EXPERT))

    # Items : 1 ACTIF bilingue par compétence (remédiation / activité maison / tuteur).
    items_by_comp = {}
    for code, c in comp.items():
        it = _item(c.id, f"[{c.label_en}] Which is correct?", f"[{c.label_ar}] أيّها صحيح؟")
        s.add(it); s.flush(); items_by_comp[code] = it
    # + items EN-only en attente d'AR (worklist console linguiste, M02).
    for code in ("FRAC.SIMPLIFY", "FRAC.COMPARE", "FRAC.ADD_UNLIKE"):
        s.add(_item(comp[code].id, f"Pending-AR item for {code}", "", status=ItemStatus.HUMAN_REVIEWED,
                    ar_validated=False))

    # Comptes staff + parent.
    admin = AppUser(email="admin@demo.atlas")
    teacher = AppUser(email="prof@demo.atlas")
    parent = AppUser(email="parent@demo.atlas")
    s.add_all([admin, teacher, parent]); s.flush()
    s.add_all([
        Membership(user_id=admin.id, role=Role.PED_ADMIN, school_id=school.id),
        Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id),
        TeacherClassroom(user_id=teacher.id, classroom_id=cls.id),
        Membership(user_id=parent.id, role=Role.PARENT, school_id=school.id),
    ])

    # 8 élèves. Profil type : NAME + ADD_SAME maîtrisés ; EQUIV/SIMPLIFY/ADD_UNLIKE en lacune
    # (re)mesurée cette semaine → cause racine EQUIV, chaîne ADD_UNLIKE→SIMPLIFY→EQUIV.
    students = []
    for i in range(8):
        u = AppUser(email=f"eleve{i+1}@demo.atlas"); s.add(u); s.flush()
        st = Student(school_id=school.id, classroom_id=cls.id, user_id=u.id, external_ref=f"S{i+1}")
        s.add(st); s.flush()
        s.add(StudentClassroom(student_id=st.id, classroom_id=cls.id))
        s.add(Membership(user_id=u.id, role=Role.STUDENT))
        students.append(st)

        gap = i < 6  # 6 élèves en lacune, 2 plutôt à l'aise (pour varier la projection)
        plan = {
            "FRAC.NAME":       (1750, OLD),
            "FRAC.ADD_SAME":   (1650, OLD),
            "FRAC.EQUIV":      (1250 if gap else 1600, RECENT),
            "FRAC.SIMPLIFY":   (1300 if gap else 1650, RECENT),
            "FRAC.COMPARE":    (1450 if gap else 1700, RECENT),
            "FRAC.ADD_UNLIKE": (1200 if gap else 1620, RECENT),
        }
        for code, (elo, when) in plan.items():
            s.add(StudentCompetencyAbility(student_id=st.id, competency_id=comp[code].id,
                                           school_id=school.id, ability_elo=float(elo),
                                           n_direct=6, confidence=0.62, last_measured_at=when))
        # Réponses datées : AVANT (~50 %) puis APRÈS (~85 %) → gain cohorte (M03) + activité (M01).
        for code in ("FRAC.EQUIV", "FRAC.SIMPLIFY", "FRAC.ADD_UNLIKE"):
            it = items_by_comp[code]
            for k in range(3):  # avant : 3 réponses, ~1/3 correctes
                s.add(Response(school_id=school.id, student_id=st.id, item_id=it.id,
                               competency_id=comp[code].id, is_correct=(k == 0), created_at=OLD))
            for k in range(3):  # après : 3 réponses, ~2.7/3 correctes
                s.add(Response(school_id=school.id, student_id=st.id, item_id=it.id,
                               competency_id=comp[code].id, is_correct=(k != 0), created_at=RECENT))

    # Lien parent → 1er élève (vue parent + action 10 min).
    s.add(ParentStudent(user_id=parent.id, student_id=students[0].id, source="staff"))
    s.commit()

    print("=" * 64)
    print("DÉMO 4 MOUVEMENTS — base atlas_dev.db prête")
    print("=" * 64)
    print(f"École={school.id}  Classe={cls.id}")
    print(f"Élève (enfant du parent) = {students[0].id}")
    print("Comptes (dev /dev/login, sans mot de passe) :")
    print("  PED_ADMIN : admin@demo.atlas   → /admin/<schoolId>  +  /admin/<schoolId>/report (preuve)")
    print("  TEACHER   : prof@demo.atlas    → /teacher/<classroomId> (digest)  + fiche élève (tuteur)")
    print("  PARENT    : parent@demo.atlas  → /parent/<studentId> (action 10 min)")
    print(f"\nRaccourcis : school_id={school.id}")
    print(f"            classroom_id={cls.id}")
    print(f"            child_student_id={students[0].id}")


if __name__ == "__main__":
    main()
