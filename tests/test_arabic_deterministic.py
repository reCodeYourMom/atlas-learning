"""L'arabe déterministe couvre TOUTE la banque — sans LLM, sans réseau.

Ce test est le filet qui protège la démo : si quelqu'un ajoute un générateur d'items ou
reformule un énoncé sans ajouter le gabarit arabe correspondant, la couverture tombe sous
100 % et CI casse ICI, au lieu de casser en visio devant un directeur académique par une
banque vide (`promote_to_active` refuse sans `ar_validated` → 0 item servi).
"""
from __future__ import annotations

import pytest

from src.items.arabic import ar_fidelity_errors, ar_math_preserved
from src.items.arabic_deterministic import translate_content, translate_stem
from src.items.deterministic import GENERATORS


def _all_items():
    for code, gen in GENERATORS.items():
        for item in gen():
            yield code, item


def test_couverture_integrale_de_la_banque():
    """Chaque item déterministe a une version arabe. Aucun trou toléré."""
    manquants = [(code, it["stem"]) for code, it in _all_items()
                 if translate_content(it) is None]
    assert not manquants, (
        f"{len(manquants)} énoncés sans gabarit AR — ajouter la règle dans "
        f"items/arabic_deterministic. Premiers cas : {manquants[:3]}"
    )


def test_chaque_item_passe_le_gate_de_fidelite():
    """La traduction franchit le MÊME gate G3 que la voie ALLaM (validate_arabic)."""
    defauts = []
    for code, it in _all_items():
        ar = translate_content(it)
        erreurs = ar_fidelity_errors(it, ar)
        if erreurs:
            defauts.append((code, it["stem"], erreurs))
    assert not defauts, f"{len(defauts)} items refusés par le gate. Premiers : {defauts[:3]}"


def test_les_nombres_sont_recopies_a_l_identique():
    """Invariant central : l'arabe pose le MÊME problème mathématique que l'anglais."""
    for code, it in _all_items():
        assert ar_math_preserved(it, translate_content(it)), code


def test_la_cle_de_correction_reste_une_option():
    """`grade_answer` compare la réponse choisie à `answer` du contenu SERVI (AR en session
    arabe) : si la clé n'était plus l'une des options, aucune réponse ne serait juste."""
    for code, it in _all_items():
        ar = translate_content(it)
        if ar.get("options"):
            assert ar["answer"] in ar["options"], code
            # Position préservée → pas de décalage de la bonne réponse entre EN et AR.
            assert ar["options"].index(ar["answer"]) == it["options"].index(it["answer"]), code


def test_aucune_devinette_sur_un_enonce_inconnu():
    """Un énoncé hors gabarit renvoie None — jamais une traduction approximative."""
    assert translate_stem("Compute the eigenvalues of the matrix.") is None
    assert translate_stem("") is None


@pytest.mark.parametrize("stem, attendu", [
    # Accord du nom compté avec un chiffre : pluriel jusqu'à 10, singulier accusatif au-delà.
    ("A whole is split into 4 equal parts. What fraction is ONE part?", "4 أجزاء متساوية"),
    ("A whole is split into 12 equal parts. What fraction is ONE part?", "12 جزءًا متساويًا"),
])
def test_accord_du_nom_compte(stem, attendu):
    assert attendu in translate_stem(stem)


def test_le_signe_moins_est_un_operateur_admis():
    """U+2212, écrit par nos propres générateurs EN, ne doit pas être vu comme une
    corruption d'encodage — sinon aucun item de soustraction ne peut être promu actif."""
    en = {"stem": "What is 4/5 − 1/5?", "options": ["3/5", "1/5", "5/5"], "answer": "3/5"}
    assert ar_fidelity_errors(en, translate_content(en)) == []
