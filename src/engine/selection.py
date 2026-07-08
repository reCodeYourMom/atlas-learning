"""Sélection d'item adaptative (Epic 4, T4.1).

Logique de CHOIX pure (l'accès DB est séparé) :
- viser l'item dont `difficulty_elo` est le plus proche de l'ability (max d'information) ;
- prioriser les compétences à faible confiance (à n_direct égal, la moins testée) ;
- ne jamais servir un item `quarantined` ni un item déjà vu (s'il reste des alternatives) ;
- rediriger vers un prérequis HARD clairement échoué ;
- SKIPPER toute compétence sans item actif servable (jamais d'exception : si aucune
  cible n'est servable, on renvoie None et l'appelant termine la session proprement).

Neutre matière : on n'opère que sur des nombres + statuts.
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Set, Tuple

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
    available_competency_ids: Optional[Set[object]] = None,
) -> Optional[object]:
    """Choisit la compétence à mesurer. Redirige vers un prérequis HARD échoué si besoin.

    `hard_prereqs` : competency_id → liste de prérequis HARD. `states_by_id` : états de
    toutes les compétences (candidats + prérequis) pour évaluer la redirection.
    `available_competency_ids` : compétences ayant AU MOINS un item actif servable
    (None = ne pas filtrer, rétro-compat). Une cible sans item actif est SKIPPÉE ;
    une redirection vers un prérequis sans item retombe sur la cible d'origine
    (mieux vaut la mesurer directement que bloquer la session).
    Priorité : confiance la plus basse, puis n_direct le plus bas.
    Retourne None si AUCUNE cible n'est servable — jamais d'exception (revue
    2026-07-07 : min([]) levait ValueError → HTTP 500 sur GET next-item).
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
        if (redirect is not None and available_competency_ids is not None
                and redirect.competency_id not in available_competency_ids):
            redirect = None  # prérequis échoué mais sans item actif → on garde la cible
        targets.append(redirect or c)

    uniq = {t.competency_id: t for t in targets}  # dédoublonne
    if available_competency_ids is not None:
        # Skip des compétences sans item actif : on passe à la cible suivante.
        uniq = {cid: t for cid, t in uniq.items() if cid in available_competency_ids}
    if not uniq:
        return None  # aucune cible servable → fin de session propre côté appelant
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
) -> Tuple[Optional[object], Optional[object]]:
    """Retourne (competency_id, item_id) du prochain item à servir.

    (None, None) si aucune cible n'a d'item actif disponible : l'appelant clôt la
    session par le mécanisme d'arrêt standard (pas d'exception, pas de 500).
    """
    states_by_id = states_by_id or {c.competency_id: c for c in candidates}
    available = {it.competency_id for it in items if it.status == "active"}
    comp = pick_competency(candidates, hard_prereqs=hard_prereqs, states_by_id=states_by_id,
                           available_competency_ids=available)
    if comp is None:
        return None, None
    state = states_by_id.get(comp)
    ability = state.ability if state else 1500.0
    return comp, pick_item(comp, ability, items, seen_item_ids)
