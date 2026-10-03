"""scripts/review_items.py — la revue EN et l'activation exigent une IDENTITÉ et laissent une
trace d'audit (revue 2026-09-20 : `--reviewer` était un texte libre, sans compte ni audit ;
`promote_to_active` n'avait aucun point d'entrée de production ; la sortie de quarantaine
n'avait ni commande ni critère).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from scripts import review_items as cli
from src.models import audit, competency, item, measurement, org, session as _se  # noqa: F401
from src.models.audit import AuditLog
from src.models.base import AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject
from src.models.competency import Competency
from src.models.item import Item
from src.models.org import AppUser, Membership

AR = {"stem": "ما هو 1/2 + 1/4؟", "options": ["3/4", "2/6"], "answer": "3/4"}
EN = {"stem": "What is 1/2 + 1/4?", "options": ["3/4", "2/6"], "answer": "3/4"}


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    comp = Competency(code="M.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add(comp); s.flush()
    rev = AppUser(email="reviewer@atlas.io"); ling = AppUser(email="ling@atlas.io")
    teacher = AppUser(email="t@school.io"); s.add_all([rev, ling, teacher]); s.flush()
    s.add_all([Membership(user_id=rev.id, role=Role.CONTENT_REVIEWER),
               Membership(user_id=ling.id, role=Role.LINGUIST),
               Membership(user_id=teacher.id, role=Role.TEACHER)])
    s.commit()
    return s, comp


def _item(s, comp, status, **kw):
    it = Item(competency_id=comp.id, answer_format=AnswerFormat.MCQ, difficulty_prior=1400.0,
              status=status, content_en=dict(EN), **kw)
    s.add(it); s.commit()
    return it


def _actions(s):
    return [(a.action, a.user_id) for a in s.execute(select(AuditLog)).scalars()]


def test_free_text_reviewer_is_refused():
    s, comp = _db()
    it = _item(s, comp, ItemStatus.AI_GENERATED)
    with pytest.raises(SystemExit):
        cli.cmd_approve(s, SimpleNamespace(id=str(it.id), reviewer="demo-provision"))
    assert it.status == ItemStatus.AI_GENERATED
    with pytest.raises(SystemExit):   # compte existant mais sans le rôle
        cli.cmd_approve(s, SimpleNamespace(id=str(it.id), reviewer="t@school.io"))


def test_approve_then_validate_then_activate_is_audited_with_identity():
    s, comp = _db()
    it = _item(s, comp, ItemStatus.AI_GENERATED, content_ar=dict(AR))
    cli.cmd_approve(s, SimpleNamespace(id=str(it.id), reviewer="reviewer@atlas.io"))
    assert it.status == ItemStatus.HUMAN_REVIEWED and it.provenance["reviewer"] == "reviewer@atlas.io"
    # un content_reviewer ne valide PAS l'arabe
    with pytest.raises(SystemExit):
        cli.cmd_validate_ar(s, SimpleNamespace(id=str(it.id), linguist="reviewer@atlas.io"))
    cli.cmd_validate_ar(s, SimpleNamespace(id=str(it.id), linguist="ling@atlas.io"))
    assert it.status == ItemStatus.LINGUIST_VALIDATED
    # …et un linguiste n'active pas : l'activation est l'acte du content_reviewer
    with pytest.raises(SystemExit):
        cli.cmd_activate(s, SimpleNamespace(id=str(it.id), all_validated=False, reviewer="ling@atlas.io"))
    cli.cmd_activate(s, SimpleNamespace(id=None, all_validated=True, reviewer="reviewer@atlas.io"))
    assert it.status == ItemStatus.ACTIVE
    rev_id = s.execute(select(AppUser.id).where(AppUser.email == "reviewer@atlas.io")).scalar_one()
    ling_id = s.execute(select(AppUser.id).where(AppUser.email == "ling@atlas.io")).scalar_one()
    acts = _actions(s)
    assert ("item.approve", rev_id) in acts
    assert ("item.ar_validated", ling_id) in acts
    assert ("item.activate", rev_id) in acts


def test_release_from_quarantine_requires_reason_and_is_audited():
    s, comp = _db()
    it = _item(s, comp, ItemStatus.QUARANTINED, content_ar=dict(AR), ar_validated=True)
    cli.cmd_release(s, SimpleNamespace(id=str(it.id), reviewer="reviewer@atlas.io",
                                       reason="item_fit S3 : courbe conforme après 60 réponses"))
    assert it.status == ItemStatus.ACTIVE
    assert it.provenance["released"] is True and "item_fit" in it.provenance["release_reason"]
    assert any(a == "item.release" for a, _ in _actions(s))
    # un item actif ne se « réhabilite » pas
    with pytest.raises(SystemExit):
        cli.cmd_release(s, SimpleNamespace(id=str(it.id), reviewer="reviewer@atlas.io", reason="x"))
