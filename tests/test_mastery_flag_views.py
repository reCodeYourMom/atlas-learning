"""Tests revue 2026-07-07 — maîtrise affichée : propagation ≠ mesure.

MASTERY_ELO == ELO_START (1500) : une compétence JAMAIS répondue mais poussée à ~1504
par simple propagation ne doit JAMAIS s'afficher « maîtrisée » dans les vues
enseignant (fiche élève), admin (overview) et parent (trajectoire).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.views_service import school_overview, student_profile, student_trajectory
from src.models import competency, item, measurement, org, session as _se  # noqa: F401  (register tables)
from src.models.base import Base, CompetencyStatus, Subject
from src.models.competency import Competency
from src.models.measurement import School, Student, StudentCompetencyAbility


def _comp(code):
    return Competency(code=code, label_en=code, label_ar="x", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    school = School(name="S"); s.add(school); s.flush()
    st = Student(school_id=school.id); s.add(st); s.flush()
    prop, meas = _comp("M.PROP"), _comp("M.MEAS")
    s.add_all([prop, meas]); s.flush()
    # M.PROP : ~1504 par PROPAGATION seulement (n_direct=0, jamais répondue)
    s.add(StudentCompetencyAbility(student_id=st.id, competency_id=prop.id, school_id=school.id,
                                   ability_elo=1504.0, n_direct=0, confidence=0.2))
    # M.MEAS : 1650 MESURÉE directement (6 réponses) → au-dessus du seuil
    s.add(StudentCompetencyAbility(student_id=st.id, competency_id=meas.id, school_id=school.id,
                                   ability_elo=1650.0, n_direct=6, confidence=0.8))
    s.commit()
    return s, school, st


def test_profile_propagated_above_threshold_not_mastered():
    # vue enseignant : ~1504 sans réponse directe → measured=False ET mastered=False
    s, school, st = _setup()
    by_code = {c["code"]: c for c in student_profile(s, st.id)["competencies"]}
    assert by_code["M.PROP"]["measured"] is False
    assert by_code["M.PROP"]["mastered"] is False   # avant la revue : True (≥ seuil)


def test_profile_measured_above_threshold_mastered():
    # la garde ne casse pas le cas nominal : mesurée ET ≥ seuil → maîtrisée
    s, school, st = _setup()
    by_code = {c["code"]: c for c in student_profile(s, st.id)["competencies"]}
    assert by_code["M.MEAS"]["measured"] is True
    assert by_code["M.MEAS"]["mastered"] is True


def test_parent_trajectory_excludes_propagated_from_mastered():
    # vue parent : seule la compétence MESURÉE apparaît dans « maîtrisées »
    s, school, st = _setup()
    traj = student_trajectory(s, st.id)
    labels = [m["label_en"] for m in traj["mastered"]]
    assert labels == ["M.MEAS"] and traj["n_mastered"] == 1
    # et la propagée n'est pas non plus une « lacune en comblement » (non mesurée)
    assert all(c["label_en"] != "M.PROP" for c in traj["closing_gaps"])


def test_school_overview_mastery_rate_measured_only():
    # vue admin : l'ability seulement propagée n'entre ni dans la liste ni dans le taux
    s, school, st = _setup()
    data = school_overview(s, school.id)
    codes = {c["code"]: c for c in data["competencies"]}
    assert "M.PROP" not in codes                     # propagation ≠ mesure
    assert codes["M.MEAS"]["mastery_rate"] == 1.0
    assert codes["M.MEAS"]["n_measured"] == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
