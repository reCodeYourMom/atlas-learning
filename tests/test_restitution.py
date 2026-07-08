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


# ---------- T5.3 adversarial — clôture amont complète (revue 2026-07-07) ----------

def _assert_chain_is_path(chain, hard):
    """La chaîne doit suivre des arêtes HARD réelles : chain[i+1] prérequis de chain[i]."""
    for down, up in zip(chain, chain[1:]):
        assert up in hard.get(down, []), f"{up} n'est pas prérequis HARD de {down}"


def test_t53_adv_deep_branch_root_found_whatever_db_order():
    # Deux branches de profondeurs inégales : SHORT (terminale, profondeur 1) et
    # B1→B2→B3 (racine réelle B3, profondeur 3). L'ancien algo suivait unmastered[0]
    # et pouvait rester bloqué sur SHORT selon l'ordre DB.
    abilities = {"GAP": 1200, "SHORT": 1200, "B1": 1200, "B2": 1200, "B3": 1200}
    for direct in (["SHORT", "B1"], ["B1", "SHORT"]):   # les deux ordres d'insertion DB
        hard = {"GAP": list(direct), "B1": ["B2"], "B2": ["B3"], "B3": [], "SHORT": []}
        d = diagnose("GAP", abilities, hard)
        assert d.root_cause == "B3"                     # la plus profonde, quel que soit l'ordre
        assert d.is_self is False
        assert d.chain == ["GAP", "B1", "B2", "B3"]
        _assert_chain_is_path(d.chain, hard)


def test_t53_adv_transitive_ancestor_broken_behind_mastered_prereq():
    # Prérequis DIRECT maîtrisé mais ancêtre TRANSITIF cassé : la maîtrise n'est pas
    # monotone (Elo par nœud). L'ancien algo renvoyait un faux is_self=True.
    hard = {"GAP": ["MID"], "MID": ["ROOT"], "ROOT": []}
    abilities = {"GAP": 1200, "MID": 1800, "ROOT": 1200}  # MID maîtrisé, ROOT cassé
    d = diagnose("GAP", abilities, hard)
    assert d.is_self is False
    assert d.root_cause == "ROOT"
    assert d.chain == ["GAP", "MID", "ROOT"]              # chemin réel, via le maillon maîtrisé
    _assert_chain_is_path(d.chain, hard)


def test_t53_adv_diamond_single_root_no_duplicates():
    # Diamant : GAP → {X, Y} → ROOT. Une seule racine, pas de doublon dans la chaîne.
    abilities = {"GAP": 1200, "X": 1200, "Y": 1200, "ROOT": 1200}
    for direct in (["X", "Y"], ["Y", "X"]):
        hard = {"GAP": list(direct), "X": ["ROOT"], "Y": ["ROOT"], "ROOT": []}
        d = diagnose("GAP", abilities, hard)
        assert d.root_cause == "ROOT"
        assert len(d.chain) == len(set(d.chain))          # pas de doublon
        assert d.chain == ["GAP", "X", "ROOT"]            # déterministe (tri par code)
        _assert_chain_is_path(d.chain, hard)


def test_t53_adv_cycle_terminates_deterministic():
    # Cycle non maîtrisé C1 ↔ C2 en amont : pas de racine stricte (chacun est ancêtre
    # de l'autre) → repli documenté : la plus profonde depuis GAP, puis code.
    hard = {"GAP": ["C1"], "C1": ["C2"], "C2": ["C1"]}
    abilities = {"GAP": 1200, "C1": 1200, "C2": 1200}
    d = diagnose("GAP", abilities, hard)                  # doit terminer (pas de boucle infinie)
    assert d.root_cause == "C2" and d.is_self is False
    assert d.chain == ["GAP", "C1", "C2"]
    # cycle passant par la lacune elle-même : termine aussi, et clôture maîtrisée → is_self
    hard_self = {"GAP": ["A"], "A": ["GAP"]}
    d2 = diagnose("GAP", {"GAP": 1200, "A": 1800}, hard_self)
    assert d2.is_self is True and d2.root_cause == "GAP"


def test_t53_adv_is_self_requires_whole_closure_mastered():
    # Toute la clôture amont (profonde) est maîtrisée → lacune propre, et rien d'autre.
    hard = {"GAP": ["MID"], "MID": ["ROOT"], "ROOT": []}
    abilities = {"GAP": 1200, "MID": 1800, "ROOT": 1800}
    d = diagnose("GAP", abilities, hard)
    assert d.is_self is True and d.root_cause == "GAP" and d.chain == ["GAP"]


# ---------- T5.3 adversarial — ancêtres JAMAIS estimés (revue adversariale 2026-07-07) ----------

def test_t53_adv_unmeasured_ancestor_never_becomes_root():
    # Preuve du panel : P (prérequis direct) est maîtrisé, Q et R n'ont AUCUNE ligne
    # ability (jamais estimés). L'ancien code désignait R comme racine avec « R n'est
    # pas maîtrisé » sans aucune donnée. Attendu : lacune propre, explication dédiée.
    hard = {"GAP": ["P"], "P": ["Q"], "Q": ["R"]}
    abilities = {"GAP": 1200, "P": 1800}          # Q et R absents du dict
    d = diagnose("GAP", abilities, hard)
    assert d.root_cause == "GAP" and d.is_self is True and d.chain == ["GAP"]
    assert "pas encore" in d.explanation           # on ne certifie pas la maîtrise de Q/R


def test_t53_adv_measured_root_behind_unmeasured_intermediate_still_found():
    # Un ancêtre MESURÉ non maîtrisé derrière un maillon jamais estimé reste détecté :
    # la restriction aux nœuds estimés ne casse pas la clôture transitive.
    hard = {"GAP": ["MID"], "MID": ["ROOT"], "ROOT": []}
    abilities = {"GAP": 1200, "ROOT": 1200}       # MID jamais estimé
    d = diagnose("GAP", abilities, hard)
    assert d.root_cause == "ROOT" and d.is_self is False
    assert d.chain == ["GAP", "MID", "ROOT"]      # chemin réel via le maillon non estimé


def test_t53_adv_root_stops_at_deepest_measured_unmastered():
    # Racine = le nœud ESTIMÉ non maîtrisé le plus profond — jamais l'origine non
    # mesurée du référentiel (qui regroupait toute une classe sous un même nœud).
    hard = {"GAP": ["P"], "P": ["Q"], "Q": []}
    abilities = {"GAP": 1200, "P": 1200}          # Q (origine) jamais estimé
    d = diagnose("GAP", abilities, hard)
    assert d.root_cause == "P" and d.is_self is False
    assert d.chain == ["GAP", "P"]


# ---------- T5.3 adversarial — nits panel (revue adversariale 2026-07-08) ----------

def test_t53_adv_chain_prefers_all_unmastered_path_at_equal_length():
    # Deux chemins de MÊME longueur vers ROOT : via Mm (maîtrisé) ou via Uu (non
    # maîtrisé). Le parent d'un nœud partagé doit être choisi par clé (maîtrisé, code)
    # au moment de l'affectation — pas au premier arrivé du frontier (l'ordre
    # inter-parents reflétait l'ordre DB). L'ancien code renvoyait GAP→P1→Mm→ROOT.
    abilities = {"GAP": 1200, "P1": 1200, "P2": 1200, "Mm": 1800, "Uu": 1200, "ROOT": 1200}
    for direct in (["P1", "P2"], ["P2", "P1"]):     # les deux ordres d'insertion DB
        hard = {"GAP": list(direct), "P1": ["Mm"], "P2": ["Uu"],
                "Mm": ["ROOT"], "Uu": ["ROOT"]}
        d = diagnose("GAP", abilities, hard)
        assert d.root_cause == "ROOT"
        assert d.chain == ["GAP", "P2", "Uu", "ROOT"]   # chemin tout-non-maîtrisé
        _assert_chain_is_path(d.chain, hard)


def test_t53_adv_cycle_node_not_disqualified_by_self_ancestry():
    # A (non maîtrisé, profondeur 2) est en cycle avec Ym (maîtrisé) : A appartient à
    # sa propre clôture d'ancêtres. L'ancien filtre (_hard_ancestors(c) & unmastered)
    # le disqualifiait par auto-ancestralité au profit de B, racine plus superficielle
    # (profondeur 1). Attendu : clôture PROPRE → A reste candidate et gagne (plus profonde).
    hard = {"GAP": ["P", "B"], "P": ["A"], "A": ["Ym"], "Ym": ["A"], "B": []}
    abilities = {"GAP": 1200, "P": 1200, "A": 1200, "Ym": 1800, "B": 1200}
    d = diagnose("GAP", abilities, hard)
    assert d.root_cause == "A" and d.is_self is False
    assert d.chain == ["GAP", "P", "A"]
    _assert_chain_is_path(d.chain, hard)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
