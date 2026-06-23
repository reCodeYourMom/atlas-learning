"""Tests T4.1 — sélection d'item adaptative. 1 test = 1 AC."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine.selection import (
    CompetencyState,
    ItemRef,
    pick_competency,
    pick_item,
    select_next,
)


def _items(comp="C"):
    return [
        ItemRef("i1", comp, 1300.0, "active"),
        ItemRef("i2", comp, 1580.0, "active"),
        ItemRef("i3", comp, 1620.0, "active"),
        ItemRef("i4", comp, 1900.0, "active"),
    ]


def test_ac1_closest_difficulty_to_ability():
    # ability 1600 → item le plus proche = i3 (1620) vs i2 (1580) : |20| < |20|? égal → premier rencontré
    chosen = pick_item("C", 1600.0, _items(), seen_item_ids=set())
    assert chosen in ("i2", "i3")  # les deux à 20 d'écart
    # cas non ambigu : ability 1610 → i3 (1620, écart 10)
    assert pick_item("C", 1610.0, _items(), set()) == "i3"


def test_ac2_quarantined_never_selected():
    items = _items() + [ItemRef("iq", "C", 1600.0, "quarantined")]  # pile à l'ability
    assert pick_item("C", 1600.0, items, set()) != "iq"


def test_ac3_seen_not_reselected_if_alternatives():
    # i3 (1620) serait choisi à ability 1610, mais déjà vu → on prend i2 (1580)
    assert pick_item("C", 1610.0, _items(), seen_item_ids={"i3"}) == "i2"


def test_ac3_repeat_allowed_if_all_seen():
    seen = {"i1", "i2", "i3", "i4"}
    assert pick_item("C", 1610.0, _items(), seen) == "i3"  # tout vu → on autorise


def test_ac4_redirect_to_failed_hard_prereq():
    target = CompetencyState("B", ability=1500, confidence=0.1, n_direct=0)
    prereq = CompetencyState("A", ability=1100, confidence=0.8, n_direct=15)  # échoué (très bas)
    chosen = pick_competency([target], hard_prereqs={"B": ["A"]},
                             states_by_id={"B": target, "A": prereq})
    assert chosen == "A"  # redirigé vers le prérequis HARD échoué


def test_ac4_no_redirect_if_prereq_ok():
    target = CompetencyState("B", 1500, 0.1, 0)
    prereq = CompetencyState("A", 1600, 0.8, 15)  # maîtrisé
    chosen = pick_competency([target], hard_prereqs={"B": ["A"]},
                             states_by_id={"B": target, "A": prereq})
    assert chosen == "B"


def test_ac5_tie_confidence_prefers_least_tested():
    c1 = CompetencyState("X", 1500, 0.3, n_direct=12)
    c2 = CompetencyState("Y", 1500, 0.3, n_direct=4)   # même confiance, moins testée
    assert pick_competency([c1, c2]) == "Y"


def test_priority_lowest_confidence_first():
    c1 = CompetencyState("X", 1500, 0.6, 5)
    c2 = CompetencyState("Y", 1500, 0.2, 5)   # confiance plus basse → prioritaire
    assert pick_competency([c1, c2]) == "Y"


def test_select_next_end_to_end():
    cand = [CompetencyState("C", 1610.0, 0.2, 3)]
    comp, item = select_next(cand, _items(), seen_item_ids=set())
    assert comp == "C" and item == "i3"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
