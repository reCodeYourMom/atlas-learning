"""Tests T5.6 — remédiation ciblée. 1 test = 1 AC."""
import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.items.generation import GeneratedItem
from src.llm.client import FakeLLMClient
from src.models.base import CognitiveLevel
from src.models.item import ItemContent
from src.restitution.diagnosis import diagnose
from src.restitution.remediation import generate_remediation, remediation_target_code

HARD = {"ADD_UNLIKE": ["EQUIV"], "EQUIV": ["MULT"], "MULT": []}
MCQ = json.dumps({"stem": "2/4 = ? /8", "options": ["3/8", "4/8", "1/8"], "answer": "4/8"})


def _competency(code="EQUIV"):
    return SimpleNamespace(id=uuid.uuid4(), code=code, label_en="Generate equivalent fractions",
                           cognitive_level=CognitiveLevel.APPLY, difficulty_prior=1500.0)


def test_ac1_targets_root_cause_competency():
    abilities = {"ADD_UNLIKE": 1200, "EQUIV": 1200, "MULT": 1800}
    d = diagnose("ADD_UNLIKE", abilities, HARD)
    assert remediation_target_code(d) == "EQUIV"          # racine, pas la lacune de surface
    target = _competency("EQUIV")
    item = generate_remediation(target, FakeLLMClient([MCQ]))
    assert item.competency_id == target.id


def test_ac2_no_student_id_in_prompt():
    client = FakeLLMClient([MCQ])
    generate_remediation(_competency(), client)
    prompt = client.calls[0]["user"] + client.calls[0]["system"]
    for forbidden in ("student", "eleve", "élève", "pupil"):
        assert forbidden.lower() not in prompt.lower()


def test_ac3_passes_itemcontent_validation():
    item = generate_remediation(_competency(), FakeLLMClient([MCQ]))
    assert isinstance(item, GeneratedItem)
    ItemContent.model_validate(item.content_en)            # ne lève pas


def test_self_gap_targets_itself():
    abilities = {"ADD_UNLIKE": 1200, "EQUIV": 1800, "MULT": 1800}
    d = diagnose("ADD_UNLIKE", abilities, HARD)
    assert remediation_target_code(d) == "ADD_UNLIKE"     # pas de fausse racine


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
