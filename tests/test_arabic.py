"""Tests T2.4 — version arabe + validation linguiste. 1 test = 1 AC."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from src.db import make_engine
from src.items.arabic import TranslationError, ar_math_preserved, translate_to_arabic
from src.items.generation import GeneratedItem
from src.items.review import (
    InvalidTransition,
    approve,
    insert_generated_items,
    promote,
    set_arabic,
    validate_arabic,
)
from src.llm.client import FakeLLMClient
from src.models.base import AnswerFormat, Base, CompetencyStatus, ItemStatus, Subject
from src.models.competency import Competency
from src.models.item import Item

EN = {"stem": "1/8 + 3/8 = ?", "options": ["2/8", "4/8", "1/4"], "answer": "4/8"}
AR = {"stem": "١/٨ + ٣/٨ = ؟", "options": ["2/8", "4/8", "1/4"], "answer": "4/8"}


def _session() -> Session:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def _human_reviewed_item(s: Session) -> Item:
    c = Competency(code="MATH.G4.NF.ADD_LIKE", label_en="x", label_ar="س",
                   subject=Subject.MATH, grade=4, difficulty_prior=1200.0,
                   status=CompetencyStatus.ACTIVE)
    s.add(c); s.commit()
    g = GeneratedItem(competency_id=c.id, content_en=dict(EN), answer_format=AnswerFormat.MCQ,
                      difficulty_prior=1180.0, context_tags={}, provenance={"model": "m"})
    it = insert_generated_items(s, [g])[0]
    approve(s, it, reviewer="nassim")  # ai_generated → human_reviewed
    return it


def test_translate_to_arabic_ok():
    client = FakeLLMClient([json.dumps(AR)])
    out = translate_to_arabic(EN, client, answer_format=AnswerFormat.MCQ)
    assert out["stem"] == AR["stem"]
    assert out["answer"] in out["options"]


def test_translate_invalid_json_rejected():
    client = FakeLLMClient(["not json"])
    try:
        translate_to_arabic(EN, client)
        assert False
    except TranslationError:
        pass


def test_ac1_no_active_without_ar_validated():
    # AC1 : human_reviewed avec ar_validated=False ne peut PAS progresser vers active
    s = _session()
    it = _human_reviewed_item(s)
    assert it.ar_validated is False
    # franchir l'étape linguiste est bloqué (garde ar_validated)
    try:
        promote(s, it, ItemStatus.LINGUIST_VALIDATED, reviewer="x")
        assert False, "devrait être bloqué sans AR validée"
    except InvalidTransition:
        pass
    # et le saut direct vers active reste interdit
    try:
        promote(s, it, ItemStatus.ACTIVE, reviewer="x")
        assert False
    except InvalidTransition:
        pass


def test_ac2_validate_ar_then_active():
    # AC2 : après validation AR, ar_validated=True et l'item peut atteindre active
    s = _session()
    it = _human_reviewed_item(s)
    set_arabic(s, it, dict(AR), by="linguiste")
    validate_arabic(s, it, linguist="linguiste")
    assert it.ar_validated is True
    assert it.status == ItemStatus.LINGUIST_VALIDATED
    promote(s, it, ItemStatus.ACTIVE, reviewer="linguiste")  # ne lève pas
    assert it.status == ItemStatus.ACTIVE


def test_ac3_editing_ar_does_not_touch_en():
    # AC3 : éditer content_ar ne modifie pas content_en
    s = _session()
    it = _human_reviewed_item(s)
    before_en = dict(it.content_en)
    set_arabic(s, it, dict(AR), by="linguiste")
    assert it.content_ar == AR
    assert it.content_en == before_en


def test_reedit_ar_resets_validation():
    s = _session()
    it = _human_reviewed_item(s)
    set_arabic(s, it, dict(AR), by="l")
    validate_arabic(s, it, linguist="l")
    assert it.ar_validated is True
    # nouvelle correction AR → re-validation requise
    set_arabic(s, it, {**AR, "stem": "نسخة منقحة"}, by="l")
    assert it.ar_validated is False


def test_ar_fidelity_preserved():
    en = {"stem": "x", "options": ["2/8", "4/8"], "answer": "4/8"}
    ar = {"stem": "س", "options": ["4/8", "2/8"], "answer": "4/8"}  # ordre différent, mêmes nombres
    assert ar_math_preserved(en, ar) is True


def test_ar_fidelity_arabic_indic_digits_ok():
    en = {"stem": "x", "options": ["1/4", "3/4"], "answer": "3/4"}
    ar = {"stem": "س", "options": ["١/٤", "٣/٤"], "answer": "٣/٤"}  # chiffres arabes = mêmes valeurs
    assert ar_math_preserved(en, ar) is True


def test_ar_fidelity_altered_number_flagged():
    en = {"stem": "x", "options": ["2/8", "4/8"], "answer": "4/8"}
    ar = {"stem": "س", "options": ["2/8", "5/8"], "answer": "5/8"}  # nombre changé
    assert ar_math_preserved(en, ar) is False
    assert ar_math_preserved(en, None) is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
