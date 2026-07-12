"""Diagnostic causal (Epic 5, T5.3) — le « waw ».

Pour une compétence en lacune, explore la clôture amont COMPLÈTE des prérequis HARD
(tous les ancêtres transitifs, protection cycles) et renvoie comme cause racine le
nœud ESTIMÉ non maîtrisé LE PLUS EN AMONT : celui dont aucun ancêtre HARD transitif
PROPRE (lui-même exclu — cas des cycles) estimé n'est non maîtrisé. La maîtrise n'est PAS monotone le long du graphe
(Elo par nœud indépendant, propagation amortie) : on ne peut donc ni suivre une seule
branche (dépendance à l'ordre DB), ni s'arrêter aux prérequis directs maîtrisés.
Un ancêtre JAMAIS estimé (absent du dict `abilities`) n'est jamais désigné racine :
aucune observation n'autorise à affirmer qu'il « n'est pas maîtrisé ».
Fonction pure (le rendu UI est séparé).
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple, Set

MASTERY_ELO = 1500.0  # seuil de maîtrise (échelle Elo) — configurable


class Diagnosis(NamedTuple):
    gap: str                 # compétence en lacune analysée
    root_cause: str          # cause racine (peut être gap lui-même)
    is_self: bool            # True = lacune propre, pas de prérequis manquant
    chain: List[str]         # chemin gap → ... → root_cause (arêtes HARD réelles)
    explanation: str


def _mastered(abilities: Dict[str, float], code: str, threshold: float) -> bool:
    # compétence sans estimation → considérée non maîtrisée (conservateur).
    # NB : ce défaut par nœud ne suffit PAS à en faire une cause racine — la
    # sélection de racine (diagnose) ne retient que les nœuds ESTIMÉS (présents
    # dans `abilities`) : accuser un nœud sur lequel il n'existe AUCUNE observation
    # produisait des racines systématiques absurdes (revue adversariale 2026-07-07).
    return abilities.get(code, float("-inf")) >= threshold


def _upstream_closure(gap: str, hard_prereqs: Dict[str, List[str]]) -> Dict[str, int]:
    """Clôture amont de `gap` : tous ses ancêtres HARD transitifs, avec leur profondeur
    BFS (longueur du plus court chemin d'arêtes HARD depuis `gap`). Inclut `gap` (0).
    Chaque nœud n'est visité qu'une fois → protection cycles et diamants."""
    depth: Dict[str, int] = {gap: 0}
    frontier = [gap]
    while frontier:
        nxt: List[str] = []
        for node in frontier:
            for p in hard_prereqs.get(node, []):
                if p not in depth:
                    depth[p] = depth[node] + 1
                    nxt.append(p)
        frontier = nxt
    return depth


def _hard_ancestors(code: str, hard_prereqs: Dict[str, List[str]]) -> Set[str]:
    """Ancêtres HARD transitifs propres de `code` (peut contenir `code` si cycle)."""
    seen: Set[str] = set()
    stack = list(hard_prereqs.get(code, []))
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(hard_prereqs.get(n, []))
    return seen


def _chain_to(
    gap: str,
    root: str,
    abilities: Dict[str, float],
    hard_prereqs: Dict[str, List[str]],
    threshold: float,
) -> List[str]:
    """Plus court chemin gap → … → root le long des arêtes HARD (pour le récit causal).

    Déterministe : à longueur égale, chaque maillon partagé entre plusieurs parents du
    même niveau BFS reçoit le parent de clé minimale (non maîtrisé d'abord, puis code) —
    choix par clé au moment de l'affectation, PAS au premier arrivé du frontier (l'ordre
    inter-parents reflétait l'ordre DB, sans sens métier ; revue 2026-07-08). Préférence
    locale (greedy) par maillon, indépendante de l'ordre DB des prérequis.
    Peut traverser un maillon maîtrisé : c'est le cas « ancêtre transitif cassé »."""
    parent: Dict[str, str] = {}
    seen = {gap}
    frontier = [gap]
    while frontier and root not in parent and root != gap:
        # découvertes du niveau : pour chaque nouveau nœud, retenir le MEILLEUR parent
        # parmi tous les candidats du niveau (min sur (maîtrisé, code) → indépendant de
        # l'ordre d'itération du frontier).
        discovered: Dict[str, str] = {}
        for node in frontier:
            for p in hard_prereqs.get(node, []):
                if p in seen:
                    continue
                best = discovered.get(p)
                if best is None or ((_mastered(abilities, node, threshold), node)
                                    < (_mastered(abilities, best, threshold), best)):
                    discovered[p] = node
        for p, par in discovered.items():
            seen.add(p)
            parent[p] = par
        frontier = list(discovered)
    path = [root]
    while path[-1] != gap:
        path.append(parent[path[-1]])
    return list(reversed(path))


def diagnose(
    gap: str,
    abilities: Dict[str, float],
    hard_prereqs: Dict[str, List[str]],
    *,
    threshold: float = MASTERY_ELO,
) -> Diagnosis:
    """Cause racine d'une lacune : le nœud non maîtrisé le plus en amont de sa clôture HARD.

    - seuls les ancêtres ESTIMÉS (présents dans `abilities`) peuvent être déclarés non
      maîtrisés : un nœud sans ligne ability n'a fait l'objet d'AUCUNE observation — en
      faire la racine (et cibler sa remédiation) affirmerait « n'est pas maîtrisé » sans
      aucune donnée, et regrouperait toute une classe sous l'origine jamais mesurée du
      référentiel (revue adversariale 2026-07-07) ;
    - candidates racines : ancêtres estimés non maîtrisés SANS ancêtre HARD transitif
      PROPRE estimé non maîtrisé (un nœud en cycle est son propre ancêtre transitif :
      on l'exclut de sa clôture pour ne pas le disqualifier par auto-ancestralité) ;
    - nœuds non maîtrisés mutuellement ancêtres (cycle, même partiellement maîtrisé) →
      aucune racine stricte, repli sur tous les ancêtres non maîtrisés ;
    - choix déterministe : profondeur BFS maximale depuis `gap`, puis tri stable par code ;
    - is_self=True si aucun ancêtre ESTIMÉ n'est en défaut — l'explication distingue le
      cas où des ancêtres non encore évalués subsistent (on ne certifie pas leur maîtrise).
    """
    depth = _upstream_closure(gap, hard_prereqs)
    unmastered = {c for c in depth
                  if c != gap and c in abilities and not _mastered(abilities, c, threshold)}

    if not unmastered:
        unmeasured = {c for c in depth if c != gap and c not in abilities}
        if unmeasured:
            explanation = (f"Lacune sur {gap} elle-même : aucun prérequis HARD estimé "
                           f"n'est manquant (certains prérequis amont n'ont pas encore "
                           f"été évalués).")
        else:
            explanation = f"Lacune sur {gap} elle-même : aucun prérequis HARD manquant."
        return Diagnosis(gap, gap, True, [gap], explanation)

    # racines strictes : sans ancêtre PROPRE non maîtrisé — on retire c de sa propre
    # clôture (_hard_ancestors contient c si c est dans un cycle : un nœud non maîtrisé
    # en cycle avec des nœuds maîtrisés serait sinon disqualifié par auto-ancestralité
    # au profit d'une racine plus superficielle ; revue 2026-07-08).
    candidates = [c for c in unmastered
                  if not ((_hard_ancestors(c, hard_prereqs) - {c}) & unmastered)]
    # repli documenté : nœuds non maîtrisés mutuellement ancêtres (cycle, même
    # partiellement maîtrisé) → aucune racine stricte.
    pool = candidates or sorted(unmastered)
    root = min(pool, key=lambda c: (-depth[c], c))

    chain = _chain_to(gap, root, abilities, hard_prereqs, threshold)
    explanation = (f"Bloque sur {gap} parce que {root}, prérequis "
                   f"{'direct' if len(chain) == 2 else 'en amont'} de {gap}, n'est pas maîtrisé.")
    return Diagnosis(gap, root, False, chain, explanation)


def find_gaps(abilities: Dict[str, float], *, threshold: float = MASTERY_ELO) -> List[str]:
    """Compétences ESTIMÉES non maîtrisées (candidates au diagnostic).

    Volontairement TOUTES les lignes ability — mesurées (n_direct > 0) comme propagées :
    le diagnostic causal travaille sur les estimations existantes. Asymétrie assumée avec
    la restitution : la garde _is_mastered de src/api/views_service.py exige n_direct > 0
    pour AFFICHER « maîtrisé », pas pour déclarer une lacune (revue 2026-07-08)."""
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
