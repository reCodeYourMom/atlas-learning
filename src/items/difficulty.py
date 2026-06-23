"""Couche de difficulté GÉNÉRIQUE — neutre de toute matière.

Contrat de scaling : chaque matière fournit un score de complexité d'item
dans [0, 1] (savoir-métier). Cette couche, partagée, le mappe sur l'échelle Elo
autour du prior de la compétence. Aucune notion de fraction/maths ici.

Pourquoi un score [0,1] centré : il situe l'item RELATIVEMENT à sa compétence.
0.5 = difficulté typique de la compétence ; 0 = le plus facile de la compétence ;
1 = le plus dur. Le moteur Elo affine ensuite `difficulty_elo` avec le trafic réel.
"""
from __future__ import annotations

DEFAULT_BAND = 250.0  # amplitude (points Elo) de modulation autour du prior de la compétence


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else float(x))


def difficulty_from_score(base_prior: float, complexity: float, *, band: float = DEFAULT_BAND) -> float:
    """Difficulté a priori d'un item (échelle Elo).

    complexity ∈ [0,1] (fourni par la matière) → prior ± band, centré sur 0.5.
    Borné à [base-band, base+band] : un item ne sort pas de la fourchette de sa compétence.
    """
    c = clamp01(complexity)
    return round(base_prior + (c - 0.5) * 2.0 * band, 1)


def weighted_score(features: dict, weights: dict) -> float:
    """Helper réutilisable : combine des features normalisées [0,1] en un score [0,1].

    Normalise sur les features RÉELLEMENT présentes (les familles d'items n'ont pas
    toutes les mêmes leviers). Booléens → 0/1. Clés absentes : ni numérateur ni dénominateur.
    """
    present = {k: w for k, w in weights.items() if features.get(k) is not None}
    total_w = sum(present.values()) or 1.0
    acc = 0.0
    for k, w in present.items():
        v = features[k]
        if isinstance(v, bool):
            v = 1.0 if v else 0.0
        acc += w * clamp01(float(v))
    return clamp01(acc / total_w)
