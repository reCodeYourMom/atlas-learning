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


# ---------------------------------------------------------------------------
# Contrôles méthodologiques A1.7
# ---------------------------------------------------------------------------
#
# Jusqu'ici documentés comme « scan automatique du JSON » mais calculés à la main et
# recopiés dans les dossiers de revue. Ici ils deviennent rejouables par un tiers.
#
# ERREURS (bloquent le seed) : ce qui est structurellement faux ou contraire à une règle
# stricte de la méthodologie (nommage A1.2, bornes de poids S6, DAG S1, arêtes vers
# l'inconnu, enums). AVERTISSEMENTS (à reporter dans le dossier de revue A1.8) : les
# cibles et invariants « ou exception documentée » — densité S2, monotonie des priors E4,
# ≥ 3 contextes N5, ≥ 2 REASON par grade A1.5. `strict=True` promeut les avertissements
# en erreurs (CI d'un nouveau domaine).

import re
from dataclasses import dataclass, field
from statistics import median

CODE_RE = re.compile(r"^MATH\.G[2-8]\.(NS|NF|NBT|OA|RP|EE|G|MD)\.[A-Z0-9_]+$")
HARD_WEIGHT_RANGE = (0.65, 0.90)
SOFT_WEIGHT_MAX = 0.70
DENSITY_RANGE = (1.3, 1.6)
MIN_ITEM_CONTEXTS = 3
MIN_REASON_PER_GRADE = 2
COGNITIVE_LEVELS = ("RECALL", "APPLY", "REASON")
NODE_STATUSES = ("draft", "active")


@dataclass
class ReferentielReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings,
                "stats": self.stats}


def _domain_of(code: str) -> str:
    parts = code.split(".")
    return parts[2] if len(parts) >= 3 else "?"


def longest_hard_chain(edges: list) -> list:
    """Plus longue chaîne d'arêtes HARD (liste de codes, source → … → cible). S3."""
    hard = [(e[0], e[1]) for e in edges if len(e) > 2 and str(e[2]).upper() == "HARD"]
    if not hard or has_cycle(hard):
        return []
    adj = _build_adjacency(hard)
    memo: dict = {}

    def best(u):
        if u in memo:
            return memo[u]
        chain = [u]
        for v in adj.get(u, ()):
            cand = [u] + best(v)
            if len(cand) > len(chain):
                chain = cand
        memo[u] = chain
        return chain

    nodes = {s for s, _ in hard} | {t for _, t in hard}
    return max((best(n) for n in nodes), key=len)


def check_referentiel(data: dict, *, external_codes=frozenset(), strict: bool = False
                      ) -> ReferentielReport:
    """Applique les contrôles A1.7 à un référentiel {nodes, edges[, meta]}.

    `external_codes` : codes d'AUTRES domaines déjà en base ou fournis à côté — une arête
    vers l'un d'eux est un PONT inter-domaines (S5), compté à part (E5), pas une erreur.
    """
    rep = ReferentielReport()
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    by_code: dict = {}

    # --- nœuds ---
    for n in nodes:
        code = n.get("code")
        if not code:
            rep.errors.append("nœud sans code"); continue
        if code in by_code:
            rep.errors.append(f"E-CODE-DUP {code} : code dupliqué")
        by_code[code] = n
        if not CODE_RE.match(code):
            rep.errors.append(f"E-NAME {code} : hors regex A1.2 MATH.G{{2-8}}.{{DOMAINE}}.{{SKILL}}")
        if not isinstance(n.get("grade"), int) or not 2 <= n["grade"] <= 8:
            rep.errors.append(f"E-GRADE {code} : grade {n.get('grade')!r} hors [2, 8]")
        if n.get("cognitive_level") not in COGNITIVE_LEVELS:
            rep.errors.append(f"E-COG {code} : cognitive_level {n.get('cognitive_level')!r}")
        if not isinstance(n.get("difficulty_prior"), (int, float)):
            rep.errors.append(f"E-PRIOR {code} : difficulty_prior manquant ou non numérique")
        status = n.get("status", (data.get("meta") or {}).get("status", "draft"))
        if status not in NODE_STATUSES:
            rep.errors.append(f"E-STATUS {code} : status {status!r} (draft|active)")
        for k in ("label_en", "label_ar"):
            if not n.get(k):
                rep.errors.append(f"E-LABEL {code} : {k} manquant")
        if len(n.get("item_contexts") or []) < MIN_ITEM_CONTEXTS:
            rep.warnings.append(f"W-CONTEXTS {code} : {len(n.get('item_contexts') or [])} "
                                f"item_contexts (< {MIN_ITEM_CONTEXTS}, N5)")

    codes = set(by_code)
    known = codes | set(external_codes)

    # --- arêtes ---
    intra, bridges = [], []
    for e in edges:
        if len(e) < 4:
            rep.errors.append(f"E-EDGE-FORMAT {e!r} : attendu [source, cible, HARD|SOFT, poids]")
            continue
        s_, t_, etype, w = e[0], e[1], str(e[2]).upper(), e[3]
        if s_ == t_:
            rep.errors.append(f"E-SELF-LOOP {s_}")
            continue
        if s_ not in known or t_ not in known:
            rep.errors.append(f"E-EDGE-UNKNOWN {s_} → {t_} : nœud inconnu")
            continue
        if etype not in ("HARD", "SOFT"):
            rep.errors.append(f"E-EDGE-TYPE {s_} → {t_} : {e[2]!r}")
            continue
        if not isinstance(w, (int, float)):
            rep.errors.append(f"E-WEIGHT {s_} → {t_} : poids non numérique")
            continue
        if etype == "HARD" and not HARD_WEIGHT_RANGE[0] <= w <= HARD_WEIGHT_RANGE[1]:
            rep.errors.append(f"E-WEIGHT {s_} → {t_} : HARD {w} hors "
                              f"[{HARD_WEIGHT_RANGE[0]}, {HARD_WEIGHT_RANGE[1]}] (S6/E4)")
        if etype == "SOFT" and not 0 < w <= SOFT_WEIGHT_MAX:
            rep.errors.append(f"E-WEIGHT {s_} → {t_} : SOFT {w} hors (0, {SOFT_WEIGHT_MAX}] (S6)")
        if s_ in codes and t_ in codes:
            intra.append(e)
        else:
            bridges.append(e)
        # E4 : le prior croît le long d'un HARD intra-domaine (ou exception documentée)
        if etype == "HARD" and s_ in by_code and t_ in by_code:
            ps, pt = by_code[s_].get("difficulty_prior"), by_code[t_].get("difficulty_prior")
            if isinstance(ps, (int, float)) and isinstance(pt, (int, float)) and pt <= ps:
                rep.warnings.append(f"W-PRIOR-MONOTONIC {s_} ({ps}) → {t_} ({pt}) : "
                                    "prior(cible) ≤ prior(source) sur un HARD (E4)")

    valid_edges = [e for e in edges if len(e) >= 4 and e[0] in known and e[1] in known
                   and e[0] != e[1]]
    if has_cycle(valid_edges):
        rep.errors.append("E-CYCLE : le graphe contient un cycle (DAG requis, S1)")

    # --- S2 densité, S3 chaîne, S4 racines, S5 ponts ---
    if nodes:
        d_intra = len(intra) / len(nodes)
        d_total = len(valid_edges) / len(nodes)
        if not DENSITY_RANGE[0] <= d_intra <= DENSITY_RANGE[1]:
            rep.warnings.append(f"W-DENSITY intra {d_intra:.2f} hors "
                                f"[{DENSITY_RANGE[0]}, {DENSITY_RANGE[1]}] (S2)")
    else:
        d_intra = d_total = 0.0
    roots = sorted(find_orphans(intra, codes))

    # --- A1.5 : ≥ 2 REASON par grade ---
    per_grade: dict = {}
    for n in nodes:
        g = n.get("grade")
        per_grade.setdefault(g, {"n": 0, "reason": 0, "priors": []})
        per_grade[g]["n"] += 1
        if n.get("cognitive_level") == "REASON":
            per_grade[g]["reason"] += 1
        if isinstance(n.get("difficulty_prior"), (int, float)):
            per_grade[g]["priors"].append(n["difficulty_prior"])
    for g, agg in sorted(per_grade.items(), key=lambda kv: str(kv[0])):
        if agg["reason"] < MIN_REASON_PER_GRADE:
            rep.warnings.append(f"W-REASON G{g} : {agg['reason']} REASON "
                                f"(< {MIN_REASON_PER_GRADE}, A1.5)")

    rep.stats = {
        "domains": sorted({_domain_of(c) for c in codes}),
        "n_nodes": len(nodes), "n_edges": len(valid_edges),
        "n_intra": len(intra), "n_bridges": len(bridges),
        "density_intra": round(d_intra, 3), "density_total": round(d_total, 3),
        "roots": roots,
        "longest_hard_chain": longest_hard_chain(intra),
        "cognitive": {lvl: sum(1 for n in nodes if n.get("cognitive_level") == lvl)
                      for lvl in COGNITIVE_LEVELS},
        "prior_median_by_grade": {str(g): median(a["priors"]) for g, a in per_grade.items()
                                  if a["priors"]},
    }
    if strict and rep.warnings:
        rep.errors.extend(f"(strict) {w}" for w in rep.warnings)
    return rep
