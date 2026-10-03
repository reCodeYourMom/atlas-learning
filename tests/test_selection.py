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


def test_ac3_competence_epuisee_ne_resert_jamais_un_item_vu():
    """Tout vu dans la compétence → None, jamais une répétition.

    Ce test encodait le contrat inverse (« tout vu → on autorise la répétition »). Il
    contredisait `session_service.submit_response`, qui refuse une seconde réponse au même
    (session, item) — contrainte d'unicité en base. L'API re-servait donc un item déjà
    répondu puis rejetait la réponse par un 409 en pleine session (reproduit : session
    interrompue au 2e item). `select_next` écarte désormais les compétences épuisées et
    passe à la cible suivante ; la session ne se clôt que si PLUS AUCUNE n'est servable.
    """
    seen = {"i1", "i2", "i3", "i4"}
    assert pick_item("C", 1610.0, _items(), seen) is None


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


# --- revue 2026-07-07 : compétence sans item actif → skip, jamais ValueError/500 ---

def test_review_competency_without_items_is_skipped():
    # X serait prioritaire (confiance plus basse) mais n'a AUCUN item actif → skippée, on sert Y
    x = CompetencyState("X", 1500, 0.1, 0)
    y = CompetencyState("Y", 1500, 0.5, 5)
    comp, item = select_next([x, y], _items("Y"), seen_item_ids=set())
    assert comp == "Y" and item is not None


def test_review_no_items_anywhere_returns_none_none():
    # aucune cible servable → (None, None) pour une fin de session propre (avant : min([]) → 500)
    cand = [CompetencyState("X", 1500, 0.1, 0)]
    assert select_next(cand, [], seen_item_ids=set()) == (None, None)


def test_review_pick_competency_empty_candidates_returns_none():
    assert pick_competency([]) is None  # avant : ValueError sur min([])


def test_review_quarantined_only_competency_is_skipped():
    # X n'a que des items quarantined → non servable → on passe à Y
    x = CompetencyState("X", 1500, 0.1, 0)
    y = CompetencyState("Y", 1500, 0.5, 5)
    items = [ItemRef("iq", "X", 1500.0, "quarantined")] + _items("Y")
    comp, item = select_next([x, y], items, seen_item_ids=set())
    assert comp == "Y" and item != "iq"


def test_review_redirect_to_itemless_prereq_falls_back_to_target():
    # prérequis HARD clairement échoué mais SANS item actif → on retombe sur la cible
    # d'origine (mieux vaut la mesurer directement que clore la session à tort)
    target = CompetencyState("B", 1500, 0.1, 0)
    prereq = CompetencyState("A", 1100, 0.8, 15)  # échoué (< FAIL_ELO) mais banque vide
    comp, item = select_next([target], _items("B"), set(),
                             hard_prereqs={"B": ["A"]},
                             states_by_id={"B": target, "A": prereq})
    assert comp == "B" and item is not None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
