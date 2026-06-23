"""Tests T3.1/T3.2/T3.3 — moteur Elo pur. 1 test = 1 AC, au chiffre près."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine.elo import (
    Neighbor,
    confidence,
    expected_score,
    k_item,
    k_student,
    propagate,
    update_elo,
)


def approx(a, b, eps=1e-9):
    return abs(a - b) <= eps


# ---------- T3.1 update_elo ----------

def test_t31_ac1_correct_delta_plus16():
    new_ability, _ = update_elo(1500, 1500, True, 0, 0)
    assert approx(expected_score(1500, 1500), 0.5)
    assert approx(new_ability, 1516.0)


def test_t31_ac2_incorrect_delta_minus16():
    new_ability, _ = update_elo(1500, 1500, False, 0, 0)
    assert approx(new_ability, 1484.0)


def test_t31_ac3_stable_student_half_amplitude():
    new_new, _ = update_elo(1500, 1500, True, 20, 0)   # n_direct=20 → K=16
    assert k_student(20) == 16.0
    assert approx(new_new - 1500, 8.0)                 # moitié de +16


def test_t31_ac4_item_calibration_half_at_30():
    assert approx(k_item(30), 16.0)
    _, item0 = update_elo(1500, 1500, True, 0, 0)
    _, item30 = update_elo(1500, 1500, True, 0, 30)
    assert approx(1500 - item0, 16.0)                  # à 0 réponse : -16
    assert approx(1500 - item30, 8.0)                  # à 30 réponses : -8 (moitié)


def test_t31_ac5_strong_student_easy_item_near_zero():
    new_ability, _ = update_elo(2500, 1000, True, 0, 0)
    assert abs(new_ability - 2500) < 0.1


def test_t31_ac6_weighted_mass_invariant():
    cases = [(1500, 1500, True, 0, 0), (1700, 1300, False, 5, 12), (1200, 1800, True, 25, 50)]
    for ab, di, ok, nd, nr in cases:
        na, ni = update_elo(ab, di, ok, nd, nr)
        inv = (na - ab) / k_student(nd) + (ni - di) / k_item(nr)
        assert approx(inv, 0.0)


# ---------- T3.2 confidence ----------

def test_t32_ac1_zero():
    assert confidence(0) == 0.0


def test_t32_ac2_eight():
    assert abs(confidence(8) - 0.63) <= 0.01


def test_t32_ac3_ten():
    assert abs(confidence(10) - 0.71) <= 0.01


def test_t32_ac4_monotonic():
    for n in range(0, 60):
        assert confidence(n) < confidence(n + 1)


def test_t32_ac5_tends_to_one():
    assert confidence(100) > 0.99
    assert confidence(100) < 1.0


# ---------- T3.3 propagate ----------

def test_t33_ac1_basic_propagation():
    nb = Neighbor("B", ability=1400, confidence=0.2, correlation_strength=0.8, edge_type="HARD")
    [res] = propagate(16.0, source_confidence=0.7, neighbors=[nb])
    assert approx(res.propagated_delta, 5.12)
    assert approx(res.new_ability, 1405.12)


def test_t33_ac2_safer_neighbor_untouched():
    nb = Neighbor("B", ability=1400, confidence=0.9, correlation_strength=0.8, edge_type="HARD")
    assert propagate(16.0, source_confidence=0.7, neighbors=[nb]) == []


def test_t33_ac3_propagation_has_no_ndirect_effect():
    # la propagation ne renvoie qu'un ability ; aucun champ n_direct → ne peut pas l'incrémenter
    nb = Neighbor("B", 1400, 0.1, 0.5, "SOFT")
    [res] = propagate(10.0, 0.7, [nb])
    assert not hasattr(res, "n_direct")


def test_t33_ac4_no_neighbors_no_error():
    assert propagate(16.0, 0.7, []) == []


def test_t33_ac5_only_direct_eligible_neighbors():
    eligible = Neighbor("B", 1400, 0.2, 0.8, "HARD")
    safer = Neighbor("C", 1600, 0.95, 0.8, "SOFT")
    res = propagate(16.0, 0.7, [eligible, safer])
    assert [r.competency_id for r in res] == ["B"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
