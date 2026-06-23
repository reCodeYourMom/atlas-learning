"""Tests T1.2 — validateur DAG. Chaque test = un AC du backlog."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graph.validator import find_orphans, has_cycle, would_create_cycle


def test_ac1_cycle_detected():
    # AC1 : A->B->C, ajouter C->A => True (cycle)
    edges = [("A", "B"), ("B", "C")]
    assert would_create_cycle(edges, ("C", "A")) is True


def test_ac2_diamond_is_valid():
    # AC2 : A->B, A->C, ajouter B->C => False (DAG valide, diamant OK)
    edges = [("A", "B"), ("A", "C")]
    assert would_create_cycle(edges, ("B", "C")) is False


def test_ac3_first_edge_empty_graph():
    # AC3 : graphe vide, première arête A->B => False
    assert would_create_cycle([], ("A", "B")) is False


def test_ac4_self_loop():
    # AC4 : auto-boucle A->A => True
    assert would_create_cycle([("A", "B")], ("A", "A")) is True


def test_has_cycle_on_clean_dag():
    edges = [("A", "B"), ("B", "C"), ("A", "C")]
    assert has_cycle(edges) is False


def test_has_cycle_on_cyclic():
    edges = [("A", "B"), ("B", "C"), ("C", "A")]
    assert has_cycle(edges) is True


def test_orphans():
    edges = [("A", "B"), ("B", "C")]
    codes = {"A", "B", "C"}
    assert find_orphans(edges, codes) == {"A"}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
