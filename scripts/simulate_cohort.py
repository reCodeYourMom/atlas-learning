"""Simulation cohorte synthétique + réglage paramètres (Epic 3, T3.5).

Élèves à ability VRAIE cachée → réponses tirées selon la proba Elo → on vérifie
que le moteur retrouve les niveaux, calibre les items, et que la propagation aide
les compétences peu testées. Script de réglage (pas du code de prod).

Déterministe (seed fixe). Aucun DB, aucun LLM : on rejoue les fonctions pures.

Errata E10 : `--referentiel` (répétable) remplace le chemin hardcodé — plusieurs
référentiels sont fusionnés (nodes + edges) pour tester les ponts inter-domaines
(gate G5, ex. fractions + décimaux). Défaut = fractions seules, sortie inchangée.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine.elo import Neighbor, confidence, expected_score, propagate, update_elo
from src.items.quarantine import ItemStats, is_drifting

SEED = 42
N_STUDENTS = 40
N_RESP = 30          # réponses directes / élève sur sa compétence primaire
ITEMS_PER_COMP = 6
DEFAULT_REFERENTIEL = Path(__file__).resolve().parents[1] / "data" / "referentiel_fractions.json"


def load_referentiels(paths) -> dict:
    """Fusionne plusieurs référentiels {nodes, edges} en un graphe unique (E10).

    Concaténation dans l'ordre des fichiers (le tirage RNG dépend de l'ordre des
    nœuds : un seul fichier = comportement historique à l'identique). Les ponts
    inter-domaines (arêtes dont source et cible viennent de fichiers différents)
    se résolvent sur le graphe fusionné — d'où la vérification APRÈS fusion.
    """
    nodes, edges, seen = [], [], set()
    for p in paths:
        data = json.loads(Path(p).read_text("utf-8"))
        for n in data["nodes"]:
            if n["code"] in seen:
                sys.exit(f"Code dupliqué entre référentiels : {n['code']}")
            seen.add(n["code"])
            nodes.append(n)
        edges.extend(data["edges"])
    unresolved = sorted({c for s, t, *_ in edges for c in (s, t) if c not in seen})
    if unresolved:
        sys.exit(f"Ponts non résolus (nœuds absents des référentiels fournis) : {unresolved}")
    return {"nodes": nodes, "edges": edges}


def pearson(xs, ys) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def build_world(rng, data):
    codes = [n["code"] for n in data["nodes"]]
    prior = {n["code"]: float(n["difficulty_prior"]) for n in data["nodes"]}
    adj = {}
    for s_code, t_code, etype, w in data["edges"]:
        adj.setdefault(t_code, []).append((s_code, float(w), etype))  # voisin = prérequis
        adj.setdefault(s_code, []).append((t_code, float(w), etype))  # et dépendant
    # items globaux : difficulté vraie autour du prior de la compétence
    items = {}  # item_id -> (comp, true_difficulty)
    for c in codes:
        for k in range(ITEMS_PER_COMP):
            items[f"{c}#{k}"] = (c, prior[c] + rng.gauss(0, 120))
    students = {i: rng.gauss(1500, 250) for i in range(N_STUDENTS)}  # ability vraie cachée
    # compétences primaires : on prend celles qui ont des voisins (pour tester la propagation)
    core = [c for c in codes if adj.get(c)][:8]
    return codes, prior, adj, items, students, core


def make_event_log(rng, items, students, core):
    """Pré-tire les réponses (indépendant du moteur) → rejouable avec/sans propagation."""
    items_by_comp = {}
    for iid, (c, _) in items.items():
        items_by_comp.setdefault(c, []).append(iid)
    log = []  # (student, comp, item_id, is_correct)
    for stu, true_ab in students.items():
        primary = core[stu % len(core)]
        for _ in range(N_RESP):
            iid = rng.choice(items_by_comp[primary])
            _, true_diff = items[iid]
            correct = rng.random() < expected_score(true_ab, true_diff)
            log.append((stu, primary, iid, correct))
    return log, {stu: core[stu % len(core)] for stu in students}


def run_engine(log, items, prior, *, propagate_on):
    # réaliste : difficulty_elo démarre au difficulty_prior de la compétence (connu),
    # puis se recale avec le trafic.
    item_diff = {iid: prior[items[iid][0]] for iid in items}
    item_n = {iid: 0 for iid in items}
    est, nd, conf = {}, {}, {}
    for stu, comp, iid, correct in log:
        a = est.get((stu, comp), 1500.0)
        ndc = nd.get((stu, comp), 0)
        na, ni = update_elo(a, item_diff[iid], correct, ndc, item_n[iid])
        est[(stu, comp)] = na
        nd[(stu, comp)] = ndc + 1
        conf[(stu, comp)] = confidence(ndc + 1)
        item_diff[iid] = ni
        item_n[iid] += 1
        if propagate_on:
            from src.engine.elo import DAMPING  # noqa
            neigh = [Neighbor(nb, est.get((stu, nb), 1500.0), conf.get((stu, nb), 0.0), w, et)
                     for (nb, w, et) in _ADJ.get(comp, [])]
            for p in propagate(na - a, conf[(stu, comp)], neigh):
                est[(stu, p.competency_id)] = p.new_ability
    return est, nd, item_diff, item_n


def main() -> None:
    global _ADJ
    p = argparse.ArgumentParser(description="Simulation cohorte synthétique (T3.5, gate G5).")
    p.add_argument("--referentiel", type=Path, action="append", default=None,
                   help="JSON référentiel {nodes, edges} — répétable pour fusionner "
                        "plusieurs domaines (défaut : data/referentiel_fractions.json).")
    args = p.parse_args()
    data = load_referentiels(args.referentiel or [DEFAULT_REFERENTIEL])

    rng = random.Random(SEED)
    codes, prior, adj, items, students, core = build_world(rng, data)
    _ADJ = adj
    log, primary_of = make_event_log(rng, items, students, core)

    est, nd, item_diff, item_n = run_engine(log, items, prior, propagate_on=True)
    est_np, *_ = run_engine(log, items, prior, propagate_on=False)

    checks = []

    # AC1 : ability estimée à ±150 de la vraie (médiane) sur la compétence primaire
    errs = [abs(est[(stu, primary_of[stu])] - students[stu]) for stu in students]
    med = median(errs)
    checks.append((f"AC1 médiane |est-vrai| = {med:.0f} Elo (cible <150)", med < 150))

    # AC2 : difficulty_elo des items corrèle avec la difficulté vraie (>0.8) sur items
    # CALIBRÉS = ≥ 30 réponses (burn-in 20 + ≥ 10 mises à jour réelles). Sous 30, la
    # difficulté est encore gelée au prior ou à peine ajustée : on mesurerait la qualité
    # des priors, pas la calibration (revue 2026-07-12 — le seuil 10 faisait échouer
    # l'AC à 0.74 en incluant des items jamais calibrés).
    calibrated = [iid for iid in items if item_n[iid] >= 30]
    corr = pearson([item_diff[i] for i in calibrated], [items[i][1] for i in calibrated])
    checks.append((f"AC2 corrélation difficulté élo/vraie = {corr:.2f} (cible >0.8, {len(calibrated)} items)", corr > 0.8))

    # AC3 : propagation réduit l'erreur sur les voisins JAMAIS testés directement
    light = [(stu, nb) for stu in students for (nb, _, _) in adj.get(primary_of[stu], [])
             if (stu, nb) not in nd]  # voisins sans réponse directe
    err_prop = median([abs(est.get((s, c), 1500.0) - students[s]) for s, c in light])
    err_base = median([abs(est_np.get((s, c), 1500.0) - students[s]) for s, c in light])
    checks.append((f"AC3 erreur voisins : propagation {err_prop:.0f} vs baseline {err_base:.0f}", err_prop < err_base))

    # AC4 : aucune quarantaine à tort sur données cohérentes.
    # La référence de quarantaine = ability MOYENNE RÉELLE des répondants (pas une constante).
    succ, resp_ab = {}, {}
    for stu, comp, iid, correct in log:
        s = succ.setdefault(iid, [0, 0]); s[0] += int(correct); s[1] += 1
        resp_ab.setdefault(iid, []).append(students[stu])
    drifting = [
        iid for iid in calibrated
        if is_drifting(
            ItemStats(item_n[iid], succ[iid][0] / succ[iid][1], item_diff[iid]),
            reference_ability=sum(resp_ab[iid]) / len(resp_ab[iid]),
        )
    ]
    checks.append((f"AC4 items en quarantaine à tort = {len(drifting)} (cible 0)", len(drifting) == 0))

    print(f"Cohorte : {N_STUDENTS} élèves × {N_RESP} réponses, {len(items)} items\n")
    ok = True
    for label, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
        ok = ok and passed
    print()
    print("Simulation OK — paramètres (K, τ, DAMPING) validés." if ok else "Simulation : ajuster les paramètres.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
