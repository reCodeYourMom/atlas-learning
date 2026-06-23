"""Tests Epic 5 cœur — agrégation (T5.1), restitution (T5.2), diagnostic (T5.3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.restitution.aggregate import AbilityRecord, aggregate
from src.restitution.diagnosis import diagnose
from src.restitution.scale import Anchor, AnchorTable, DEFAULT_ANCHORS, restitute


# ---------- T5.1 aggregate ----------

def test_t51_ac1_uniform_strand_score():
    recs = [AbilityRecord("MATH.G4.NF.A", 1800, 0.8, 5),
            AbilityRecord("MATH.G4.NF.B", 1800, 0.8, 5)]
    agg = aggregate(recs)["strands"]["MATH.G4.NF"]
    assert abs(agg.score - 1800) < 1 and agg.measured is True


def test_t51_ac2_low_confidence_weighs_less():
    recs = [AbilityRecord("MATH.G4.NF.A", 1900, 0.9, 5),
            AbilityRecord("MATH.G4.NF.B", 1100, 0.1, 5)]
    score = aggregate(recs)["strands"]["MATH.G4.NF"].score
    assert score > 1700           # tiré vers la mesure sûre (1900), pas la moyenne brute (1500)


def test_t51_ac3_no_direct_measure_marked_estimated():
    recs = [AbilityRecord("MATH.G4.NF.A", 1600, 0.0, 0),
            AbilityRecord("MATH.G4.NF.B", 1600, 0.0, 0)]
    assert aggregate(recs)["strands"]["MATH.G4.NF"].measured is False


# ---------- T5.2 scale ----------

def test_t52_ac1_deterministic_percentile():
    r = restitute(1500, 0.9, DEFAULT_ANCHORS)
    assert r.percentile == 50.0 and r.level == "G4" and r.is_range is False


def test_t52_ac2_table_change_changes_output_not_engine():
    shifted = AnchorTable([Anchor(1000, 0, "A"), Anchor(1500, 10, "B"), Anchor(2000, 20, "C")])
    assert restitute(1500, 0.9, shifted).percentile == 10.0      # table différente → autre sortie
    assert restitute(1500, 0.9, DEFAULT_ANCHORS).percentile == 50.0


def test_t52_ac3_low_confidence_returns_range():
    r = restitute(1500, 0.2, DEFAULT_ANCHORS)
    assert r.is_range is True and r.percentile_range is not None
    lo, hi = r.percentile_range
    assert lo < r.percentile < hi


# ---------- T5.3 diagnostic causal ----------

HARD = {
    "ADD_UNLIKE": ["EQUIV"],
    "EQUIV": ["MULT_FACTS"],
    "MULT_FACTS": [],
}


def test_t53_ac1_points_to_root_prerequisite():
    abilities = {"ADD_UNLIKE": 1200, "EQUIV": 1200, "MULT_FACTS": 1800}  # MULT maîtrisé
    d = diagnose("ADD_UNLIKE", abilities, HARD)
    assert d.root_cause == "EQUIV" and d.is_self is False


def test_t53_ac2_walks_to_most_upstream():
    abilities = {"ADD_UNLIKE": 1200, "EQUIV": 1200, "MULT_FACTS": 1200}  # tout en amont manquant
    d = diagnose("ADD_UNLIKE", abilities, HARD)
    assert d.root_cause == "MULT_FACTS"            # la vraie racine, la plus en amont
    assert d.chain == ["ADD_UNLIKE", "EQUIV", "MULT_FACTS"]


def test_t53_ac3_self_gap_no_false_cause():
    abilities = {"ADD_UNLIKE": 1200, "EQUIV": 1800, "MULT_FACTS": 1800}  # prérequis OK
    d = diagnose("ADD_UNLIKE", abilities, HARD)
    assert d.is_self is True and d.root_cause == "ADD_UNLIKE"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
