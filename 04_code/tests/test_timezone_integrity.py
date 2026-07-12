"""Tests d'intégrité temporelle (revue 2026-07-07 — mandat timestamptz UAE).

Verrouille la convention projet (src/models/base.py) :
  - `utcnow()` : SEULE source de « maintenant » — aware, UTC ;
  - TOUTE colonne timestamp est DateTime(timezone=True) (timestamptz sur Postgres) ;
  - SQLite (dev/CI) restitue des datetimes NAÏFS même sur colonne tz-aware : un naïf
    relu de la base est PAR CONVENTION de l'UTC — `ensure_utc()` normalise avant toute
    comparaison avec un datetime aware (sinon TypeError).

NB : sur une machine dont l'heure locale EST l'UTC, une régression `datetime.now()`
serait indétectable par les tests de valeurs — c'est pourquoi on verrouille AUSSI le
tzinfo des valeurs produites (machine-indépendant) et le type des colonnes (structurel).
"""
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import DateTime, create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from scripts.purge_retention import purge_retention
from src.api.session_service import next_item, start_session
from src.audit import log_action
from src.engine.service import on_response
from src.models import competency as _c, item as _i, measurement as _m, org as _o, session as _se  # noqa: F401,E501
from src.models.audit import AuditLog
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Subject, ensure_utc, utcnow,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import Response, School, Student
from src.models.org import AppUser
from src.models.session import AssessmentSession
from src.models.token import ConsumedToken
from src.rbac.auth import make_single_use_token
from src.rbac.single_use import consume_single_use_token
from src.restitution.proof import proof_surfaces


def _engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    return engine


def _seed_measurement(s):
    """École + élève + compétence + item actif (le minimum pour on_response/session)."""
    school = School(name="S"); s.add(school); s.flush()
    student = Student(school_id=school.id); s.add(student); s.flush()
    comp = Competency(code="X.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add(comp); s.flush()
    item = Item(competency_id=comp.id, content_en={"stem": "?", "answer": "1"},
                answer_format=AnswerFormat.NUMERIC, difficulty_prior=1500.0,
                difficulty_elo=1500.0, status=ItemStatus.ACTIVE)
    s.add(item); s.flush()
    return school, student, comp, item


# ---------- helpers de la convention ----------

def test_utcnow_is_aware_utc():
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_ensure_utc_normalizes_every_case():
    # None → None (colonnes nullable : deleted_at, ended_at…)
    assert ensure_utc(None) is None
    # naïf (relu de SQLite) → réinterprété UTC, même mur d'horloge
    naive = datetime(2026, 7, 7, 12, 0, 0)
    fixed = ensure_utc(naive)
    assert fixed.tzinfo == timezone.utc and fixed.replace(tzinfo=None) == naive
    # aware non-UTC → converti (l'instant est préservé, pas le mur d'horloge)
    gulf = datetime(2026, 7, 7, 16, 0, 0, tzinfo=timezone(timedelta(hours=4)))  # UAE
    assert ensure_utc(gulf) == datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
    # aware UTC → inchangé
    aware = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
    assert ensure_utc(aware) == aware


# ---------- verrou STRUCTUREL : toutes les colonnes timestamp sont tz-aware ----------

def test_all_datetime_columns_are_timezone_aware():
    """Machine-indépendant : aucune colonne DateTime sans timezone=True dans le schéma.

    Attrape toute nouvelle table/colonne ajoutée sans la convention timestamptz.
    """
    offenders = [
        f"{table.name}.{col.name}"
        for table in Base.metadata.tables.values()
        for col in table.columns
        if isinstance(col.type, DateTime) and not col.type.timezone
    ]
    assert offenders == [], f"colonnes TIMESTAMP sans timezone : {offenders}"


# ---------- verrou des VALEURS : tout ce qui est écrit est aware-UTC ----------

def test_written_timestamps_are_aware_utc_before_flush():
    """Les producteurs d'horodatage (audit, session, response) émettent de l'aware-UTC.

    Vérifié AVANT expiration/rechargement : le tzinfo est visible en mémoire, donc une
    régression `datetime.now()` naïf est détectée même sur une machine à l'heure UTC.
    """
    engine = _engine()
    with Session(bind=engine) as s:
        school, student, comp, item = _seed_measurement(s)
        entry = log_action(s, action="test.tz", school_id=school.id)
        sess = AssessmentSession(school_id=school.id, student_id=student.id)
        s.add(sess); s.flush()   # applique les defaults Python (utcnow)
        for value in (entry.created_at, sess.started_at):
            assert value.tzinfo is not None and value.utcoffset() == timedelta(0)


def test_persisted_timestamps_follow_utc_convention():
    """Relu de la base : naïf sur SQLite (convention documentée) mais mur d'horloge UTC."""
    engine = _engine()
    with Session(bind=engine) as s:
        school, student, comp, item = _seed_measurement(s)
        before = utcnow()
        on_response(s, student_id=student.id, item_id=item.id, is_correct=True,
                    school_id=school.id)
        after = utcnow()
    with Session(bind=engine) as s:
        resp = s.execute(select(Response)).scalar_one()
        # ensure_utc(valeur relue) retombe dans la fenêtre [before, after] mesurée en UTC :
        # si le code écrivait l'heure LOCALE naïve, l'écart serait l'offset de la machine.
        for value in (ensure_utc(resp.created_at),):
            assert before <= value <= after, value


def test_consumed_token_expiry_is_utc_epoch():
    """`expires_at` dérive de l'epoch du jeton via fromtimestamp(tz=UTC) — exact, pas local."""
    engine = _engine()
    issued_at = 1_780_000_000                      # epoch arbitraire, connu
    ttl = 3600
    token = make_single_use_token(str(uuid.uuid4()), purpose="parent_login",
                                  ttl_s=ttl, now=issued_at)
    with Session(bind=engine) as s:
        consume_single_use_token(s, token, purpose="parent_login", now=issued_at + 1)
    with Session(bind=engine) as s:
        row = s.execute(select(ConsumedToken)).scalar_one()
        expected = datetime.fromtimestamp(issued_at + ttl, tz=timezone.utc)
        assert ensure_utc(row.expires_at) == expected
        assert ensure_utc(row.consumed_at).utcoffset() == timedelta(0)


# ---------- pas de TypeError aware/naïf sur les chemins qui comparent ----------

def test_next_item_elapsed_survives_naive_reload():
    """Stopping temps de session : started_at relu de SQLite est naïf ; utcnow() est aware.

    Sans ensure_utc, la soustraction lèverait TypeError. Banque vide → fin propre
    « no_items » (le calcul d'elapsed a lieu AVANT la sélection).
    """
    engine = _engine()
    with Session(bind=engine) as s:
        school = School(name="S"); s.add(school); s.flush()
        student = Student(school_id=school.id); s.add(student); s.flush()
        sess = start_session(s, student_id=student.id, school_id=school.id)
        sid = sess.id
    with Session(bind=engine) as s:                     # session NEUVE → datetimes naïfs
        sess = s.get(AssessmentSession, sid)
        assert sess.started_at.tzinfo is None           # le piège SQLite est bien là
        out = next_item(s, sess)
        assert out == {"done": True, "reason": "no_items"}


def test_retention_and_proof_accept_aware_now_over_persisted_rows():
    """Rétention + preuve d'impact : now AWARE vs valeurs relues NAÏVES — pas de TypeError."""
    engine = _engine()
    now = utcnow()
    with Session(bind=engine) as s:
        school, student, comp, item = _seed_measurement(s)
        # élève + compte soft-deleted au-delà de la rétention → exerce ensure_utc(deleted_at)
        gone_user = AppUser(email="gone@school.edu", deleted_at=now - timedelta(days=45))
        s.add(gone_user); s.flush()
        gone = Student(school_id=school.id, user_id=gone_user.id,
                       deleted_at=now - timedelta(days=45))
        s.add(gone); s.flush()
        s.add(Response(school_id=school.id, student_id=student.id, item_id=item.id,
                       competency_id=comp.id, is_correct=True,
                       created_at=now - timedelta(days=45)))   # période « avant »
        s.commit()
        school_id, gone_id = school.id, gone.id
    with Session(bind=engine) as s:
        report = purge_retention(s, now=now, execute=True)     # now aware, base naïve
        assert [st["student_id"] for st in report["students"]] == [str(gone_id)]
    with Session(bind=engine) as s:
        surfaces = proof_surfaces(s, school_id, now=now)       # compare created_at relu
        assert surfaces["cohort"]["n_before"] == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
