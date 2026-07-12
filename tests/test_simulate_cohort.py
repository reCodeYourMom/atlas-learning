"""Tests Lot C / errata E10 — simulate_cohort paramétré (--referentiel répétable).

Contrat central : le DÉFAUT (fractions seules) est strictement le comportement
historique — même monde, même tirage RNG (la fusion ne réordonne rien quand un
seul fichier est fourni). La fusion sert au banc d'essai inter-domaines (gate G5).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.simulate_cohort import DEFAULT_REFERENTIEL, load_referentiels

ROOT = Path(__file__).resolve().parents[1]


def _write(tmpdir: Path, name: str, nodes, edges) -> Path:
    p = tmpdir / name
    p.write_text(json.dumps({"nodes": nodes, "edges": edges}), encoding="utf-8")
    return p


def _node(code, prior=1500.0):
    return {"code": code, "difficulty_prior": prior}


def test_defaut_identique_au_referentiel_brut():
    # un seul fichier = comportement historique : nodes/edges à l'IDENTIQUE, même ordre
    # (le tirage RNG dépend de l'ordre des nœuds — toute permutation changerait la simu)
    raw = json.loads(DEFAULT_REFERENTIEL.read_text("utf-8"))
    merged = load_referentiels([DEFAULT_REFERENTIEL])
    assert merged["nodes"] == raw["nodes"]
    assert merged["edges"] == raw["edges"]


def test_fusion_concatene_dans_l_ordre_et_resout_les_ponts():
    tmpdir = Path(tempfile.mkdtemp())
    a = _write(tmpdir, "a.json", [_node("A.1"), _node("A.2")],
               [["A.1", "A.2", "HARD", 0.8]])
    # pont inter-domaines : source dans a.json, cible dans b.json
    b = _write(tmpdir, "b.json", [_node("B.1")], [["A.2", "B.1", "HARD", 0.7]])
    merged = load_referentiels([a, b])
    assert [n["code"] for n in merged["nodes"]] == ["A.1", "A.2", "B.1"]
    assert merged["edges"] == [["A.1", "A.2", "HARD", 0.8], ["A.2", "B.1", "HARD", 0.7]]


def test_code_duplique_entre_referentiels_refuse():
    tmpdir = Path(tempfile.mkdtemp())
    a = _write(tmpdir, "a.json", [_node("X.1")], [])
    b = _write(tmpdir, "b.json", [_node("X.1")], [])
    with pytest.raises(SystemExit):
        load_referentiels([a, b])


def test_pont_non_resolu_refuse():
    # arête vers un nœud d'un référentiel NON fourni : refus explicite, pas de KeyError tardif
    tmpdir = Path(tempfile.mkdtemp())
    a = _write(tmpdir, "a.json", [_node("X.1")], [["X.1", "ABSENT.1", "HARD", 0.8]])
    with pytest.raises(SystemExit):
        load_referentiels([a])


def test_run_par_defaut_monde_inchange():
    # bout-en-bout sans argument : le monde historique (40×30, 32 comp × 6 items = 192)
    # et les AC déterministes (seed 42) — AC2 volontairement non figé ici : il échoue
    # depuis le burn-in item de la revue 2026-07-08 (préexistant, hors périmètre E10).
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate_cohort.py")],
                       capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert "Cohorte : 40 élèves × 30 réponses, 192 items" in r.stdout
    assert "PASS  AC1" in r.stdout
    assert "PASS  AC3" in r.stdout
    assert "PASS  AC4" in r.stdout


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
    print(f"\n{len(fns)} tests OK")
