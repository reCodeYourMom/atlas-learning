"""Tests T2.2 — pipeline de génération d'items. 1 test = 1 AC.

Aucun appel réseau : FakeLLMClient renvoie des sorties JSON déterministes.
"""
import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.llm.client import FakeLLMClient
from src.models.base import AnswerFormat, CognitiveLevel, ItemStatus
from src.models.item import ItemContent
from src.items.generation import GenerationError, generate_items


def _competency():
    return SimpleNamespace(
        id=uuid.uuid4(),
        code="MATH.G4.NF.ADD_LIKE",
        label_en="Add fractions with like denominators",
        cognitive_level=CognitiveLevel.APPLY,
        difficulty_prior=1200.0,
    )


def _mcq(stem="2/5 + 1/5 = ?", options=("1/5", "2/5", "3/5", "4/5"), answer="3/5") -> str:
    return json.dumps({"stem": stem, "options": list(options), "answer": answer})


def test_ac1_n_items_valid_content():
    # AC1 : génère N items, chacun parse en ItemContent valide
    comp = _competency()
    targets = [{"i": 1}, {"i": 2}, {"i": 3}]
    client = FakeLLMClient([_mcq(), _mcq(), _mcq()])
    items = generate_items(comp, targets, client)
    assert len(items) == 3
    for it in items:
        ItemContent.model_validate(it.content_en)  # ne lève pas
        assert it.status == ItemStatus.AI_GENERATED


def test_ac2_carries_competency_id():
    # AC2 : chaque item porte le competency_id demandé (1:1)
    comp = _competency()
    client = FakeLLMClient([_mcq(), _mcq()])
    items = generate_items(comp, [{"a": 1}, {"a": 2}], client)
    assert all(it.competency_id == comp.id for it in items)


def test_ac3_context_targets_covered():
    # AC3 : les context_tags demandés sont couverts (simplify true ET false)
    comp = _competency()
    targets = [{"simplify": True}, {"simplify": False}]
    client = FakeLLMClient([_mcq(), _mcq()])
    items = generate_items(comp, targets, client)
    covered = {it.context_tags.get("simplify") for it in items}
    assert covered == {True, False}


def test_ac4_mcq_well_formed():
    # AC4 : MCQ a >= 2 options et answer ∈ options
    comp = _competency()
    client = FakeLLMClient([_mcq()])
    [it] = generate_items(comp, [{"x": 1}], client)
    opts = it.content_en["options"]
    assert len(opts) >= 2 and it.content_en["answer"] in opts


def test_ac4_mcq_answer_not_in_options_rejected():
    # AC4 (négatif) : answer hors options => GenerationError
    comp = _competency()
    client = FakeLLMClient([_mcq(answer="9/5")])  # 9/5 absent des options
    try:
        generate_items(comp, [{"x": 1}], client)
        assert False, "un MCQ incohérent aurait dû être rejeté"
    except GenerationError:
        pass


def test_ac5_no_student_data_in_prompt():
    # AC5 : aucune fuite — le prompt ne contient aucun identifiant élève
    comp = _competency()
    client = FakeLLMClient([_mcq()])
    generate_items(comp, [{"simplify": True}], client)
    prompt = client.calls[0]["user"] + client.calls[0]["system"]
    for forbidden in ("student", "student_id", "eleve", "élève", "pupil"):
        assert forbidden.lower() not in prompt.lower(), f"fuite potentielle : {forbidden}"
    # sanity : le prompt référence bien la compétence + le contexte
    assert comp.code in prompt
    assert "simplify" in prompt


def test_invalid_json_rejected():
    comp = _competency()
    client = FakeLLMClient(["{not valid json"])
    try:
        generate_items(comp, [{"x": 1}], client)
        assert False, "JSON invalide aurait dû être rejeté"
    except GenerationError:
        pass


def test_provenance_records_model_and_prompt_id():
    comp = _competency()
    client = FakeLLMClient([_mcq()])
    [it] = generate_items(comp, [{"x": 1}], client)
    assert it.provenance["model"] == "fake-model"
    assert "prompt_id" in it.provenance


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
