"""Tests Lot B — B1 : la vue markdown du crosswalk est GÉNÉRÉE, jamais éditée.

Règle structurante du cadrage : le pivot JSON est la source de vérité, le markdown
une vue générée — le risque couvert ici est la dérive doc/produit (double entretien).
"""
import copy
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_crosswalk_md import OUT_PATH, generate, main
from scripts.validate_crosswalk import load_pivot


def test_generate_produit_un_markdown_non_vide_et_complet():
    text = generate(load_pivot())
    assert text.strip()
    assert "GÉNÉRÉ — ne pas éditer" in text            # bandeau anti-édition manuelle
    # 32 mappings × 2 tables (correspondance + MoE) = 64 lignes de données
    assert len(re.findall(r"^\| \d+ \|", text, flags=re.M)) == 64
    # la synthèse est CALCULÉE depuis les lignes (mêmes comptes que le validateur B6)
    assert "| **CCSS_M** | 32 / 32 | 18 | 6 |" in text
    assert "| **UK_NC** | 32 / 32 | 22 | 7 |" in text


def test_vue_generee_committee_synchronisee_avec_le_pivot():
    # anti-dérive B1 : si le pivot change sans régénération, ce test casse — c'est voulu
    assert generate(load_pivot()) == OUT_PATH.read_text(encoding="utf-8")


def test_main_ecrit_un_fichier_non_vide():
    out = Path(tempfile.mkdtemp()) / "crosswalk_vue.md"
    argv = sys.argv
    sys.argv = ["generate_crosswalk_md.py", "--out", str(out)]
    try:
        main()
    finally:
        sys.argv = argv
    assert out.exists() and out.stat().st_size > 0


def test_main_refuse_un_pivot_invalide():
    # même porte que le seed : jamais de vue générée depuis un pivot qui viole B6
    tmpdir = Path(tempfile.mkdtemp())
    pivot = copy.deepcopy(load_pivot())
    pivot["mappings"].pop()   # R1 violée : compétence active non mappée
    bad = tmpdir / "pivot_invalide.json"
    bad.write_text(json.dumps(pivot), encoding="utf-8")
    out = tmpdir / "ne_doit_pas_exister.md"
    argv = sys.argv
    sys.argv = ["generate_crosswalk_md.py", "--pivot", str(bad), "--out", str(out)]
    try:
        with pytest.raises(SystemExit) as exc:
            main()
    finally:
        sys.argv = argv
    assert exc.value.code == 1
    assert not out.exists()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
    print(f"\n{len(fns)} tests OK")
