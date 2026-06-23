"""Tests de la couche difficulté GÉNÉRIQUE (neutre de toute matière)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.items.difficulty import clamp01, difficulty_from_score, weighted_score


def test_score_center_is_base():
    assert difficulty_from_score(1500, 0.5) == 1500.0


def test_score_extremes_hit_band():
    assert difficulty_from_score(1500, 0.0, band=250) == 1250.0
    assert difficulty_from_score(1500, 1.0, band=250) == 1750.0


def test_score_is_clamped():
    # complexité hors [0,1] bornée
    assert difficulty_from_score(1500, 5.0, band=250) == 1750.0
    assert difficulty_from_score(1500, -3.0, band=250) == 1250.0


def test_monotonic_in_complexity():
    vals = [difficulty_from_score(1500, c) for c in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert vals == sorted(vals) and len(set(vals)) == 5


def test_weighted_score_subject_agnostic():
    # noms de features arbitraires : la couche ne connaît AUCUNE matière
    w = {"alpha": 1.0, "beta": 1.0}
    assert weighted_score({"alpha": 1.0, "beta": 0.0}, w) == 0.5
    assert weighted_score({"alpha": 1.0, "beta": 1.0}, w) == 1.0


def test_weighted_score_normalizes_on_present_features():
    # une feature absente ne dilue pas le score
    w = {"a": 0.5, "b": 0.5}
    assert weighted_score({"a": True}, w) == 1.0   # seule 'a' présente → normalisé sur 'a'
    assert weighted_score({"a": True, "b": False}, w) == 0.5


def test_clamp01():
    assert clamp01(-1) == 0.0 and clamp01(2) == 1.0 and clamp01(0.3) == 0.3


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
