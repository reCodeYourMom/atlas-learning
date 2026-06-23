"""Diagnostic causal (Epic 5, T5.3) — le « waw ».

Pour une compétence en lacune, remonte la chaîne de prérequis HARD non maîtrisés
jusqu'à la cause racine la plus en amont. Fonction pure (le rendu UI est séparé).
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple

MASTERY_ELO = 1500.0  # seuil de maîtrise (échelle Elo) — configurable


class Diagnosis(NamedTuple):
    gap: str                 # compétence en lacune analysée
    root_cause: str          # cause racine (peut être gap lui-même)
    is_self: bool            # True = lacune propre, pas de prérequis manquant
    chain: List[str]         # chemin gap → ... → root_cause
    explanation: str


def _mastered(abilities: Dict[str, float], code: str, threshold: float) -> bool:
    # compétence non mesurée → considérée non maîtrisée (conservateur)
    return abilities.get(code, float("-inf")) >= threshold


def diagnose(
    gap: str,
    abilities: Dict[str, float],
    hard_prereqs: Dict[str, List[str]],
    *,
    threshold: float = MASTERY_ELO,
) -> Diagnosis:
    """Remonte les prérequis HARD non maîtrisés depuis `gap` jusqu'à la racine."""
    chain = [gap]
    cur = gap
    visited = {gap}
    while True:
        unmastered = [p for p in hard_prereqs.get(cur, [])
                      if not _mastered(abilities, p, threshold) and p not in visited]
        if not unmastered:
            break
        cur = unmastered[0]          # on descend dans le prérequis manquant le plus amont
        visited.add(cur)
        chain.append(cur)

    is_self = cur == gap
    if is_self:
        explanation = f"Lacune sur {gap} elle-même : aucun prérequis HARD manquant."
    else:
        explanation = (f"Bloque sur {gap} parce que {cur}, prérequis "
                       f"{'direct' if len(chain) == 2 else 'en amont'} de {gap}, n'est pas maîtrisé.")
    return Diagnosis(gap, cur, is_self, chain, explanation)


def find_gaps(abilities: Dict[str, float], *, threshold: float = MASTERY_ELO) -> List[str]:
    """Compétences mesurées non maîtrisées (candidates au diagnostic)."""
    return [c for c, a in abilities.items() if a < threshold]


def diagnose_all(
    abilities: Dict[str, float],
    hard_prereqs: Dict[str, List[str]],
    *,
    threshold: float = MASTERY_ELO,
) -> List[Diagnosis]:
    """Diagnostique toutes les lacunes ; pratique pour la vue enseignant (T5.4)."""
    return [diagnose(g, abilities, hard_prereqs, threshold=threshold)
            for g in find_gaps(abilities, threshold=threshold)]
