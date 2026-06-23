"""Sélection d'item adaptative (Epic 4, T4.1).

Logique de CHOIX pure (l'accès DB est séparé) :
- viser l'item dont `difficulty_elo` est le plus proche de l'ability (max d'information) ;
- prioriser les compétences à faible confiance (à n_direct égal, la moins testée) ;
- ne jamais servir un item `quarantined` ni un item déjà vu (s'il reste des alternatives) ;
- rediriger vers un prérequis HARD clairement échoué.

Neutre matière : on n'opère que sur des nombres + statuts.
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional

FAIL_ELO = 1300.0  # ability en-dessous → prérequis "clairement échoué" (ability très basse)


class CompetencyState(NamedTuple):
    competency_id: object
    ability: float
    confidence: float
    n_direct: int


class ItemRef(NamedTuple):
    item_id: object
    competency_id: object
    difficulty_elo: float
    status: str  # "active" | "quarantined" | ...


def pick_competency(
    candidates: List[CompetencyState],
    *,
    hard_prereqs: Optional[Dict[object, List[object]]] = None,
    states_by_id: Optional[Dict[object, CompetencyState]] = None,
    fail_elo: float = FAIL_ELO,
) -> object:
    """Choisit la compétence à mesurer. Redirige vers un prérequis HARD échoué si besoin.

    `hard_prereqs` : competency_id → liste de prérequis HARD. `states_by_id` : états de
    toutes les compétences (candidats + prérequis) pour évaluer la redirection.
    Priorité : confiance la plus basse, puis n_direct le plus bas.
    """
    hard_prereqs = hard_prereqs or {}
    states_by_id = states_by_id or {c.competency_id: c for c in candidates}

    targets: List[CompetencyState] = []
    for c in candidates:
        redirect = None
        for pid in hard_prereqs.get(c.competency_id, []):
            ps = states_by_id.get(pid)
            if ps is not None and ps.ability < fail_elo:
                redirect = ps
                break
        targets.append(redirect or c)

    uniq = {t.competency_id: t for t in targets}  # dédoublonne
    best = min(uniq.values(), key=lambda s: (s.confidence, s.n_direct))
    return best.competency_id


def pick_item(
    competency_id: object,
    ability: float,
    items: List[ItemRef],
    seen_item_ids,
) -> Optional[object]:
    """Item actif de la compétence dont la difficulté est la plus proche de l'ability.

    Exclut quarantined ; évite les déjà-vus tant qu'il reste des alternatives.
    """
    pool = [it for it in items if it.competency_id == competency_id and it.status == "active"]
    if not pool:
        return None
    fresh = [it for it in pool if it.item_id not in set(seen_item_ids)]
    chosen = fresh or pool  # tout vu → on autorise la répétition
    return min(chosen, key=lambda it: abs(it.difficulty_elo - ability)).item_id


def select_next(
    candidates: List[CompetencyState],
    items: List[ItemRef],
    seen_item_ids,
    *,
    hard_prereqs: Optional[Dict[object, List[object]]] = None,
    states_by_id: Optional[Dict[object, CompetencyState]] = None,
) -> tuple:
    """Retourne (competency_id, item_id|None) du prochain item à servir."""
    states_by_id = states_by_id or {c.competency_id: c for c in candidates}
    comp = pick_competency(candidates, hard_prereqs=hard_prereqs, states_by_id=states_by_id)
    state = states_by_id.get(comp)
    ability = state.ability if state else 1500.0
    return comp, pick_item(comp, ability, items, seen_item_ids)
