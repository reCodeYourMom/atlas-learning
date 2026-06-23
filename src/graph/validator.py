"""Validateur de graphe de prérequis (T1.2).

Fonctions pures, sans accès DB. Protègent le seed (T1.3) :
le graphe ne doit jamais contenir de cycle.

Représentation d'une arête : tuple (source, target) — source est prérequis de target.
"""
from __future__ import annotations

from collections import defaultdict

# Couleurs DFS
_WHITE, _GRAY, _BLACK = 0, 1, 2


def _build_adjacency(edges: list[tuple]) -> dict:
    adj: dict = defaultdict(list)
    for edge in edges:
        source, target = edge[0], edge[1]
        adj[source].append(target)
    return adj


def has_cycle(edges: list[tuple]) -> bool:
    """True si le graphe (orienté) contient au moins un cycle.

    Gère les arêtes à 2 éléments (source, target) ou plus (les suivants ignorés),
    pour accepter directement le format (source, target, edge_type, weight).
    """
    adj = _build_adjacency(edges)
    nodes = set(adj.keys()) | {e[1] for e in edges}
    color = {n: _WHITE for n in nodes}

    def dfs(u) -> bool:
        color[u] = _GRAY
        for v in adj.get(u, ()):  # noqa
            if color.get(v, _WHITE) == _GRAY:
                return True
            if color.get(v, _WHITE) == _WHITE and dfs(v):
                return True
        color[u] = _BLACK
        return False

    for node in nodes:
        if color[node] == _WHITE and dfs(node):
            return True
    return False


def would_create_cycle(edges: list[tuple], new_edge: tuple) -> bool:
    """True si ajouter new_edge crée un cycle dans le graphe existant.

    Auto-boucle (A->A) considérée comme cycle.
    """
    source, target = new_edge[0], new_edge[1]
    if source == target:
        return True
    return has_cycle(list(edges) + [new_edge])


def find_orphans(edges: list[tuple], all_codes: set) -> set:
    """Renvoie les nœuds sans aucune arête entrante (candidats racines).

    Utile au seed pour distinguer racines légitimes d'orphelins suspects.
    """
    has_parent = {e[1] for e in edges}
    return {c for c in all_codes if c not in has_parent}
