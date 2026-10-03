"""Tests du générateur déterministe.

Garantie premium : on RE-PARSE l'énoncé arithmétique et on RECALCULE la réponse
avec Fraction → preuve que chaque item est mathématiquement correct (pas une
confiance aveugle dans le générateur).
"""
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.items.deterministic import (
    GENERATORS,
    bank_items,
    fraction_complexity,
    generate_for,
)
from src.models.item import ItemContent

REFERENTIEL = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "referentiel_fractions.json").read_text("utf-8")
)
ALL_CODES = [n["code"] for n in REFERENTIEL["nodes"]]

# stems où la réponse = résultat d'un calcul re-vérifiable
ARITHMETIC = {
    "MATH.G3.NF.ADD_SAME_NOSIMP", "MATH.G4.NF.ADD_SAME_SIMPLIFY", "MATH.G4.NF.ADD_SAME_IMPROPER",
    "MATH.G3.NF.SUB_SAME_NOSIMP", "MATH.G4.NF.SUB_SAME_SIMPLIFY",
    "MATH.G4.NF.ADD_UNLIKE_SIMPLE", "MATH.G4.NF.ADD_UNLIKE_LCM", "MATH.G5.NF.ADD_UNLIKE_FULL",
    "MATH.G5.NF.SUB_UNLIKE_LCM", "MATH.G5.NF.ADD_MIXED",
}
CONVERT = {"MATH.G5.NF.MIXED_TO_IMPROPER", "MATH.G5.NF.IMPROPER_TO_MIXED"}

_TOKEN = re.compile(r"(?:(\d+)\s+)?(\d+)/(\d+)")


def _to_fraction(s: str) -> Fraction:
    s = s.strip()
    m = re.fullmatch(r"(?:(\d+)\s+)?(\d+)/(\d+)", s)
    if m:
        w = int(m.group(1) or 0)
        return Fraction(w) + Fraction(int(m.group(2)), int(m.group(3)))
    return Fraction(int(s))


def _operands(stem: str):
    return [(int(w or 0), int(n), int(d)) for w, n, d in _TOKEN.findall(stem)]


def test_all_referentiel_codes_have_generator():
    missing = [c for c in ALL_CODES if c not in GENERATORS]
    assert not missing, f"compétences sans générateur : {missing}"


def test_min_items_per_competency():
    for code in ALL_CODES:
        items = generate_for(code)
        assert len(items) >= 5, f"{code}: seulement {len(items)} items"


def test_structure_valid_mcq():
    for code in ALL_CODES:
        for it in generate_for(code):
            ItemContent.model_validate(it)                     # stem + answer présents
            opts = it["options"]
            assert len(opts) == len(set(opts)), f"{code}: options en double {opts}"
            assert len(opts) >= 2, f"{code}: < 2 options"
            assert it["answer"] in opts, f"{code}: answer hors options"


def test_no_duplicate_stems_within_competency():
    for code in ALL_CODES:
        stems = [it["stem"] for it in generate_for(code)]
        assert len(stems) == len(set(stems)), f"{code}: énoncés en double"


def test_arithmetic_answers_are_mathematically_correct():
    for code in ARITHMETIC:
        for it in generate_for(code):
            ops = _operands(it["stem"])
            assert len(ops) >= 2, f"{code}: opérandes introuvables dans '{it['stem']}'"
            (w1, n1, d1), (w2, n2, d2) = ops[0], ops[1]
            x = Fraction(w1) + Fraction(n1, d1)
            y = Fraction(w2) + Fraction(n2, d2)
            expected = x - y if ("−" in it["stem"] or " - " in it["stem"]) else x + y
            assert _to_fraction(it["answer"]) == expected, \
                f"{code}: '{it['stem']}' réponse {it['answer']} ≠ {expected}"


def test_conversion_answers_correct():
    for code in CONVERT:
        for it in generate_for(code):
            (w, n, d) = _operands(it["stem"])[0]
            value = Fraction(w) + Fraction(n, d)
            assert _to_fraction(it["answer"]) == value, \
                f"{code}: '{it['stem']}' → {it['answer']} ≠ {value}"


def test_distractors_are_wrong():
    # aucun distracteur ne doit être (par malchance) une autre écriture de la bonne réponse
    for code in ARITHMETIC | CONVERT:
        for it in generate_for(code):
            ans = _to_fraction(it["answer"])
            for opt in it["options"]:
                if opt == it["answer"]:
                    continue
                try:
                    val = _to_fraction(opt)
                except (ValueError, ZeroDivisionError):
                    continue
                assert val != ans, f"{code}: distracteur {opt} == réponse {it['answer']}"


def test_per_item_difficulty_varies_within_competency():
    # l'adaptatif a besoin de discriminer les items D'UNE MÊME compétence
    for code in ("MATH.G4.NF.ADD_UNLIKE_LCM", "MATH.G5.NF.ADD_UNLIKE_FULL", "MATH.G4.NF.SIMPLIFY_FRACTION"):
        diffs = {it["difficulty_prior"] for it in bank_items(code, 1500.0)}
        assert len(diffs) >= 2, f"{code}: difficulté plate ({diffs})"


def test_context_tags_are_meaningful():
    # les items arithmétiques portent des tags exploitables (pas {gen, idx})
    for it in bank_items("MATH.G4.NF.ADD_UNLIKE_LCM", 1500.0):
        tags = it["context_tags"]
        assert "max_denominator" in tags and "operation" in tags
        assert "needs_lcm" in tags


def test_complexity_monotonic_in_hard_features():
    easy = fraction_complexity({"max_denominator": 4})
    harder = fraction_complexity({"max_denominator": 12, "needs_lcm": True,
                                  "simplify_required": True, "improper_result": True})
    assert harder > easy


def test_difficulty_within_band():
    for code in ("MATH.G4.NF.ADD_UNLIKE_LCM",):
        for it in bank_items(code, 1500.0):
            assert 1250.0 <= it["difficulty_prior"] <= 1750.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
