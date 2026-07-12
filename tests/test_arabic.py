"""Tests T2.4 — version arabe + validation linguiste. 1 test = 1 AC."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from src.db import make_engine
from src.items.arabic import (
    TranslationError,
    ar_fidelity_errors,
    ar_math_preserved,
    ar_mcq_structure_ok,
    ar_stem_numbers_preserved,
    translate_to_arabic,
)
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


# --- CRIT-1 (revue 2026-07-12) : le gate de fidélité était aveugle au stem ---

def test_stem_numbers_preserved_true_when_digits_kept():
    en = {"stem": "A set has 12 objects. 3/4 are red. How many?", "options": ["9"], "answer": "9"}
    ar = {"stem": "مجموعة تحتوي على 12 جسم. 3/4 منها حمراء. كم؟", "options": ["9"], "answer": "9"}
    assert ar_stem_numbers_preserved(en, ar) is True


def test_stem_numbers_preserved_arabic_indic_digits_ok():
    en = {"stem": "1/8 + 3/8 = ?", "options": ["4/8"], "answer": "4/8"}
    ar = {"stem": "١/٨ + ٣/٨ = ؟", "options": ["4/8"], "answer": "4/8"}
    assert ar_stem_numbers_preserved(en, ar) is True


def test_stem_numbers_lost_when_fraction_written_as_word():
    # le cas réel CRIT-1 : « 3/4 » remplacé par « ثلث » (un tiers)
    en = {"stem": "A set has 12 objects. 3/4 are red.", "options": ["9"], "answer": "9"}
    ar = {"stem": "مجموعة تحتوي على 12 جسم. ثلث هذه الأجسام حمراء.", "options": ["9"], "answer": "9"}
    assert ar_stem_numbers_preserved(en, ar) is False
    assert ar_stem_numbers_preserved(en, None) is False


def test_mcq_structure_ok_and_misaligned():
    en = {"stem": "x", "options": ["2/8", "4/8", "1/4"], "answer": "4/8"}   # idx 1
    ok = {"stem": "س", "options": ["2/8", "4/8", "1/4"], "answer": "4/8"}   # idx 1
    misaligned = {"stem": "س", "options": ["4/8", "2/8", "1/4"], "answer": "4/8"}  # idx 0 ≠ 1
    not_in = {"stem": "س", "options": ["2/8", "1/4"], "answer": "9/9"}
    assert ar_mcq_structure_ok(en, ok) is True
    assert ar_mcq_structure_ok(en, misaligned) is False
    assert ar_mcq_structure_ok(en, not_in) is False


def test_fidelity_errors_aggregates_and_is_empty_when_clean():
    en = {"stem": "1/8 + 3/8 = ?", "options": ["2/8", "4/8"], "answer": "4/8"}
    clean = {"stem": "١/٨ + ٣/٨ = ؟", "options": ["2/8", "4/8"], "answer": "4/8"}
    broken = {"stem": "جمع الكسور", "options": ["2/8", "4/8"], "answer": "4/8"}  # stem sans nombres
    assert ar_fidelity_errors(en, clean) == []
    assert ar_fidelity_errors(en, broken)  # non vide : stem perd 1/8 et 3/8


def test_validate_arabic_gate_rejects_wrong_stem():
    # le gate G3 aurait empêché les 5 items CRIT-1 de devenir active
    from src.items.review import InvalidTransition, set_arabic, validate_arabic
    s = _session()
    it = _human_reviewed_item(s)
    set_arabic(s, it, {"stem": "جمع الكسور", "options": ["2/8", "4/8", "1/4"], "answer": "4/8"}, by="l")
    try:
        validate_arabic(s, it, linguist="l")
        assert False, "validate_arabic aurait dû refuser un stem qui perd les nombres"
    except InvalidTransition as e:
        assert "énoncé AR" in str(e) or "fidélité" in str(e)
    assert it.ar_validated is False


def test_validate_arabic_gate_accepts_faithful_translation():
    from src.items.review import set_arabic, validate_arabic
    from src.models.base import ItemStatus
    s = _session()
    it = _human_reviewed_item(s)
    set_arabic(s, it, dict(AR), by="l")  # AR fidèle défini en tête de fichier
    validate_arabic(s, it, linguist="l")
    assert it.ar_validated is True
    assert it.status == ItemStatus.LINGUIST_VALIDATED


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
