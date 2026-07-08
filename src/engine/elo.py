"""Moteur de mesure Elo + propagation (Epic 3, T3.1–T3.3).

Maths PURES, déterministes, NEUTRES de toute matière : on n'opère que sur des
nombres (ability, difficulté, deltas) et des arêtes pondérées. Aucun accès DB,
aucun LLM. Testable au chiffre près.

Échelle Elo [0–4000], centrée 1500.
"""
from __future__ import annotations

import math
from typing import List, NamedTuple

# --- constantes de réglage (ajustables via la simulation T3.5) ---
K_NEW = 32.0          # K élève tant que peu mesuré
K_STABLE = 16.0       # K élève une fois stabilisé
N_DIRECT_STABLE = 10  # seuil de stabilisation
K_ITEM_BASE = 32.0    # K item à la sortie du burn-in
ITEM_HALFLIFE = 30.0  # n_responses où K_item est divisé par 2
TAU = 8.0             # constante de la confiance
DAMPING = 0.4         # amortissement de la propagation 1-saut

# Bornes de l'échelle Elo (revue 2026-07-07) : sans clamp, une longue série de
# réponses (triche, bug client, boucle de rejeu) fait dériver ability/difficulté
# hors de l'échelle [0–4000] annoncée — et toute la sélection d'items avec.
ELO_MIN = 0.0
ELO_MAX = 4000.0

# Burn-in item (revue 2026-07-07) : difficulty_prior est calibré PAR ITEM par le
# générateur déterministe — signal plus fiable qu'une poignée de réponses bruitées.
# Tant que n_responses < ITEM_BURN_IN, la difficulté reste GELÉE au prior (K item = 0) :
# un K simplement réduit laisserait quand même dériver l'item sur une petite cohorte
# biaisée (ex. seuls les forts répondent), le gel est prévisible et testable.
# Surchargable par appelant via le paramètre `burn_in` de k_item/update_elo.
ITEM_BURN_IN = 20


def clamp_elo(value: float) -> float:
    """Borne une valeur Elo (ability ou difficulté) dans [ELO_MIN, ELO_MAX]. Pure."""
    return max(ELO_MIN, min(ELO_MAX, value))


def expected_score(ability: float, item_difficulty: float) -> float:
    """Probabilité Elo que l'élève réussisse l'item."""
    return 1.0 / (1.0 + 10.0 ** ((item_difficulty - ability) / 400.0))


def k_student(n_direct: int) -> float:
    return K_NEW if n_direct < N_DIRECT_STABLE else K_STABLE


def k_item(n_responses_item: int, *, burn_in: int = ITEM_BURN_IN) -> float:
    """K item : 0 pendant le burn-in (difficulté gelée au prior), puis décroissant."""
    if n_responses_item < burn_in:
        return 0.0
    return K_ITEM_BASE / (1.0 + n_responses_item / ITEM_HALFLIFE)


def update_elo(
    ability: float,
    item_difficulty: float,
    is_correct: bool,
    n_direct: int,
    n_responses_item: int,
    *,
    burn_in: int = ITEM_BURN_IN,
) -> tuple:
    """Met à jour (ability élève, difficulté item) pour une réponse. Fonction pure.

    L'item bouge en sens inverse de l'élève. Invariant pondéré :
    Δability / K_student + Δdifficulty / K_item == 0 — valable UNIQUEMENT hors
    saturation (aucun clamp déclenché) et hors burn-in (K_item > 0) : au clamp
    l'invariant est volontairement rompu (borner prime sur conserver la masse),
    pendant le burn-in la difficulté est gelée (l'ability élève bouge normalement).
    """
    expected = expected_score(ability, item_difficulty)
    score = 1.0 if is_correct else 0.0
    diff = score - expected
    ks, ki = k_student(n_direct), k_item(n_responses_item, burn_in=burn_in)
    new_ability = clamp_elo(ability + ks * diff)
    new_item_difficulty = clamp_elo(item_difficulty - ki * diff)
    return new_ability, new_item_difficulty


def confidence(n_direct: int) -> float:
    """Confiance [0,1] d'une ability selon le nb de réponses DIRECTES. Pure."""
    return max(0.0, min(1.0, 1.0 - math.exp(-n_direct / TAU)))


# --- propagation 1-saut ---

class Neighbor(NamedTuple):
    competency_id: object
    ability: float
    confidence: float
    correlation_strength: float   # [0..1] poids de l'arête
    edge_type: str                # "HARD" | "SOFT" (info, non utilisée dans le calcul)


class Propagation(NamedTuple):
    competency_id: object
    new_ability: float
    propagated_delta: float


def propagate(
    delta: float,
    source_confidence: float,
    neighbors: List[Neighbor],
    *,
    damping: float = DAMPING,
) -> List[Propagation]:
    """Propage un delta amorti aux voisins DIRECTS, pondéré par correlation_strength.

    - `propagated_delta = delta * correlation_strength * damping`.
    - N'écrase pas une mesure plus sûre : on ne touche un voisin que si
      `confidence(voisin) < source_confidence`.
    - N'incrémente PAS n_direct du voisin (c'est de l'inféré). 1 saut seulement.
    - L'asymétrie prérequis/dépendant est portée par `correlation_strength` (donnée),
      pas par cette fonction.
    - `new_ability` est clampée dans [ELO_MIN, ELO_MAX] (même règle qu'update_elo).
    """
    results: List[Propagation] = []
    for nb in neighbors:
        if nb.confidence < source_confidence:
            pd = delta * nb.correlation_strength * damping
            results.append(Propagation(nb.competency_id, clamp_elo(nb.ability + pd), pd))
    return results
