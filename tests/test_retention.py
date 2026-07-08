"""Tests de la purge de rétention (scripts/purge_retention.py, revue sécurité 2026-07-07).

Garanties vérifiées :
  - dry-run PAR DÉFAUT : rapporte sans rien supprimer ni journaliser ;
  - ne touche JAMAIS un élève actif, ni un soft delete plus récent que la rétention ;
  - purge dure l'élève soft-deleted ancien ET ses données liées (réponses, abilities,
    sessions, liens parent) + son compte s'il est lui-même soft-deleted ancien ;
  - purge les jti de liens magiques expirés, garde les jti encore valides ;
  - journalise dans AuditLog (append-only).
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from scripts.purge_retention import purge_retention
from src.models import competency as _c, item as _i, measurement as _m, org as _o, session as _se  # noqa: F401,E501
from src.models.audit import AuditLog
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import AppUser, Membership, ParentStudent
from src.models.session import AssessmentSession
from src.models.token import ConsumedToken

NOW = datetime(2026, 7, 7, 12, 0, 0)


def _engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    return engine


def _add_student_data(s, school, comp, item, parent, student):
    """Réponse + ability + session + lien parent pour `student`."""
    s.add_all([
        Response(school_id=school.id, student_id=student.id, item_id=item.id,
                 competency_id=comp.id, is_correct=True),
        StudentCompetencyAbility(student_id=student.id, competency_id=comp.id,
                                 school_id=school.id, ability_elo=1500.0),
        AssessmentSession(school_id=school.id, student_id=student.id),
        ParentStudent(user_id=parent.id, student_id=student.id),
    ])


def _seed(engine):
    """1 élève actif, 1 soft-deleted récent (5 j), 1 soft-deleted ancien (45 j) + 2 jti."""
    s = Session(bind=engine)
    school = School(name="S"); s.add(school); s.flush()
    comp = Competency(code="X.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add(comp); s.flush()
    item = Item(competency_id=comp.id, content_en={"stem": "?", "answer": "1"},
                answer_format=AnswerFormat.NUMERIC, difficulty_prior=1500.0,
                difficulty_elo=1500.0, status=ItemStatus.ACTIVE)
    parent = AppUser(email="mom@home.com")
    s.add_all([item, parent]); s.flush()
    s.add(Membership(user_id=parent.id, role=Role.PARENT))

    old_user = AppUser(email="gone@school.edu", deleted_at=NOW - timedelta(days=45))
    s.add(old_user); s.flush()
    active = Student(school_id=school.id, external_ref="ACTIVE")
    recent = Student(school_id=school.id, external_ref="RECENT",
                     deleted_at=NOW - timedelta(days=5))
    old = Student(school_id=school.id, external_ref="OLD", user_id=old_user.id,
                  deleted_at=NOW - timedelta(days=45))
    s.add_all([active, recent, old]); s.flush()
    for st in (active, recent, old):
        _add_student_data(s, school, comp, item, parent, st)

    s.add_all([
        ConsumedToken(jti="jti-expired", purpose="parent_login",
                      expires_at=NOW - timedelta(days=1), consumed_at=NOW - timedelta(days=15)),
        ConsumedToken(jti="jti-valid", purpose="admin_login",
                      expires_at=NOW + timedelta(days=1), consumed_at=NOW),
    ])
    s.commit()
    ids = dict(active=active.id, recent=recent.id, old=old.id, old_user=old_user.id)
    s.close()
    return ids


def _students(s):
    return {st.external_ref for st in s.execute(select(Student)).scalars()}


# ---------- dry-run par défaut : rien n'est supprimé ----------

def test_dry_run_reports_without_deleting():
    engine = _engine(); _seed(engine)
    with Session(bind=engine) as s:
        report = purge_retention(s, now=NOW)                     # execute=False par défaut
        assert report["dry_run"] is True
        assert len(report["students"]) == 1                      # seul OLD est éligible
        assert report["consumed_tokens_purged"] == 1
    with Session(bind=engine) as s:
        assert _students(s) == {"ACTIVE", "RECENT", "OLD"}       # rien supprimé
        assert len(s.execute(select(ConsumedToken)).scalars().all()) == 2
        assert s.execute(select(AuditLog)).scalars().all() == [] # rien journalisé



def test_execute_purges_only_old_soft_deleted():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        report = purge_retention(s, now=NOW, execute=True)
        assert report["dry_run"] is False and len(report["students"]) == 1
    with Session(bind=engine) as s:
        assert _students(s) == {"ACTIVE", "RECENT"}              # OLD purgé, les autres intacts
        # Données liées de OLD purgées (cascade) ; celles des survivants intactes.
        assert set(s.execute(select(Response.student_id)).scalars()) == {ids["active"], ids["recent"]}
        assert set(s.execute(select(StudentCompetencyAbility.student_id)).scalars()) \
            == {ids["active"], ids["recent"]}
        assert set(s.execute(select(AssessmentSession.student_id)).scalars()) \
            == {ids["active"], ids["recent"]}
        assert set(s.execute(select(ParentStudent.student_id)).scalars()) \
            == {ids["active"], ids["recent"]}
        # Compte élève (PII) soft-deleted ancien : purgé aussi. Le parent, lui, reste.
        assert s.get(AppUser, ids["old_user"]) is None
        emails = {u.email for u in s.execute(select(AppUser)).scalars()}
        assert emails == {"mom@home.com"}


def test_execute_purges_expired_jti_only():
    engine = _engine(); _seed(engine)
    with Session(bind=engine) as s:
        purge_retention(s, now=NOW, execute=True)
    with Session(bind=engine) as s:
        jtis = {t.jti for t in s.execute(select(ConsumedToken)).scalars()}
        assert jtis == {"jti-valid"}                             # l'expiré est purgé


def test_execute_writes_audit_trail():
    engine = _engine(); _seed(engine)
    with Session(bind=engine) as s:
        purge_retention(s, now=NOW, execute=True)
    with Session(bind=engine) as s:
        actions = [a.action for a in s.execute(select(AuditLog)).scalars()]
        assert actions.count("retention.purge_student") == 1
        assert actions.count("retention.purge") == 1
        summary = s.execute(select(AuditLog).where(AuditLog.action == "retention.purge")
                            ).scalar_one()
        assert summary.details["students"] == 1 and summary.details["consumed_tokens"] == 1


def test_never_touches_active_students_even_with_zero_retention():
    engine = _engine(); _seed(engine)
    with Session(bind=engine) as s:
        # rétention 0 jour : TOUS les soft-deleted partent... mais jamais un élève actif.
        report = purge_retention(s, retention_days=0, now=NOW + timedelta(seconds=1),
                                 execute=True)
        assert len(report["students"]) == 2
    with Session(bind=engine) as s:
        assert _students(s) == {"ACTIVE"}


def test_retention_days_capped_at_max(monkeypatch):
    # Avis juridique 2026-07-08 : RETENTION_DAYS est PLAFONNÉ à 30. Poser 60 dans l'env
    # ne doit PAS étendre la fenêtre : la valeur effective reste 30, donc OLD (45 j) est
    # bien éligible à la purge (le plafond ne peut pas servir à retarder l'effacement).
    engine = _engine(); _seed(engine)
    monkeypatch.setenv("RETENTION_DAYS", "60")
    with Session(bind=engine) as s:
        report = purge_retention(s, now=NOW)
        assert report["retention_days"] == 30                    # ramené au plafond
        assert len(report["students"]) == 1                      # OLD reste purgeable


# ---------- legal hold : suspend la purge (avis juridique 2026-07-08) ----------

def test_legal_hold_on_student_blocks_purge():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        s.get(Student, ids["old"]).legal_hold = NOW               # hold individuel
        s.commit()
    with Session(bind=engine) as s:
        report = purge_retention(s, now=NOW, execute=True)
        assert report["students"] == [] and report["held_skipped"] == 1
    with Session(bind=engine) as s:
        assert _students(s) == {"ACTIVE", "RECENT", "OLD"}        # OLD conservé malgré 45 j


def test_legal_hold_on_school_blocks_all_its_students():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        old = s.get(Student, ids["old"])
        s.get(School, old.school_id).legal_hold = NOW             # hold tenant-large
        s.commit()
    with Session(bind=engine) as s:
        report = purge_retention(s, now=NOW, execute=True)
        assert report["students"] == [] and report["held_skipped"] == 1
    with Session(bind=engine) as s:
        assert "OLD" in _students(s)                              # protégé par le hold école


def test_purge_resumes_after_hold_cleared():
    engine = _engine(); ids = _seed(engine)
    with Session(bind=engine) as s:
        s.get(Student, ids["old"]).legal_hold = NOW; s.commit()
    with Session(bind=engine) as s:                               # hold posé → épargné
        assert purge_retention(s, now=NOW, execute=True)["students"] == []
    with Session(bind=engine) as s:                               # hold levé → purgé
        s.get(Student, ids["old"]).legal_hold = None; s.commit()
    with Session(bind=engine) as s:
        assert len(purge_retention(s, now=NOW, execute=True)["students"]) == 1
    with Session(bind=engine) as s:
        assert _students(s) == {"ACTIVE", "RECENT"}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and "monkeypatch" not in v.__code__.co_varnames]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
