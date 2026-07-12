"""Invariance inter-écoles — mêmes items, mêmes difficultés estimées ±SE (C4.4).

Principe : si la mesure est invariante, la difficulté d'un item estimée depuis
les réponses de l'école A doit être compatible (à l'erreur-type près) avec celle
estimée depuis l'école B. Une divergence systématique signale un biais de
contexte (conditions de passation, curriculum local, triche) — PAS un item.

Estimation PAR ÉCOLE (indépendante du difficulty_elo global, qui mélange tout
le trafic) : inversion du modèle logistique du moteur (src/engine/elo.py) —
  p = 1 / (1 + 10^((b − ā)/400))   →   b̂ = ā + 400·log10((1−p)/p)
avec ā = ability moyenne des répondants de l'école sur la compétence de l'item,
et p le taux de réussite observé (correction de continuité (x+0.5)/(n+1) pour
éviter p ∈ {0, 1}). Erreur-type par méthode delta :
  SE(b̂) = (400/ln 10) / sqrt(n·p·(1−p))

Comparaison par paire d'écoles : z = |b̂₁ − b̂₂| / sqrt(SE₁² + SE₂²) ; l'item est
NON-invariant si z > 1.96 (5 %). Le résumé donne aussi le biais moyen par école
(b̂_école − b̂_ensemble) : un décalage constant → problème d'école, pas d'items.

Usage  : DATABASE_URL=... python scripts/analysis/invariance.py
                          [--min-per-school N] [--z-crit X]
Sortie : JSON sur stdout (lecture seule).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import SessionLocal, make_engine
from src.engine.service import ELO_START
from src.models.measurement import Response, StudentCompetencyAbility

DEFAULT_MIN_PER_SCHOOL = 20  # réponses minimales par item × école
DEFAULT_Z_CRIT = 1.96        # 5 % bilatéral

_ELO_PER_LN = 400.0 / math.log(10.0)  # 400/ln10 ≈ 173.72 (le « logit Elo » de C1.1)


def estimate_difficulty(n: int, n_correct: int, mean_ability: float) -> dict:
    """(b̂, SE) par inversion logistique + méthode delta. Correction de continuité."""
    p = (n_correct + 0.5) / (n + 1.0)
    b_hat = mean_ability + 400.0 * math.log10((1.0 - p) / p)
    se = _ELO_PER_LN / math.sqrt(n * p * (1.0 - p))
    return {"n": n, "p_observed": round(p, 4), "mean_ability": round(mean_ability, 1),
            "difficulty_hat": round(b_hat, 1), "se": round(se, 1)}


def run(s: Session, *, min_per_school: int, z_crit: float) -> dict:
    ability: Dict[tuple, float] = {
        (row.student_id, row.competency_id): row.ability_elo
        for row in s.execute(
            select(StudentCompetencyAbility.student_id,
                   StudentCompetencyAbility.competency_id,
                   StudentCompetencyAbility.ability_elo)
        )
    }

    # (item, école) -> [n, n_correct, Σability] ; item -> competency.
    # Colonnes explicites (jamais select(Response) entier) : robuste aux colonnes
    # du modèle pas encore migrées dans la base interrogée (ex. language, C-0).
    cells: Dict[tuple, list] = {}
    comp_of: Dict[object, object] = {}
    for student_id, competency_id, item_id, school_id, is_correct in s.execute(
            select(Response.student_id, Response.competency_id,
                   Response.item_id, Response.school_id, Response.is_correct)):
        ab = ability.get((student_id, competency_id), ELO_START)
        cell = cells.setdefault((item_id, school_id), [0, 0, 0.0])
        cell[0] += 1
        cell[1] += int(bool(is_correct))
        cell[2] += ab
        comp_of[item_id] = competency_id

    # Estimations par item × école (n suffisant seulement).
    per_item: Dict[object, dict] = {}
    for (item_id, school_id), (n, n_ok, sum_ab) in cells.items():
        if n < min_per_school:
            continue
        per_item.setdefault(item_id, {})[school_id] = estimate_difficulty(n, n_ok, sum_ab / n)

    items_out, n_flagged = [], 0
    school_bias: Dict[object, list] = {}  # école -> [b̂_école − b̂_moyen_item]
    for item_id, by_school in sorted(per_item.items(), key=lambda kv: str(kv[0])):
        if len(by_school) < 2:
            continue  # item vu dans une seule école : pas de comparaison possible
        schools = sorted(by_school, key=str)
        pooled_mean = sum(e["difficulty_hat"] for e in by_school.values()) / len(by_school)
        for sc in schools:
            school_bias.setdefault(sc, []).append(by_school[sc]["difficulty_hat"] - pooled_mean)
        comparisons = []
        invariant = True
        for i in range(len(schools)):
            for j in range(i + 1, len(schools)):
                e1, e2 = by_school[schools[i]], by_school[schools[j]]
                se_diff = math.sqrt(e1["se"] ** 2 + e2["se"] ** 2)
                z = abs(e1["difficulty_hat"] - e2["difficulty_hat"]) / se_diff if se_diff else 0.0
                flagged = z > z_crit
                invariant = invariant and not flagged
                comparisons.append({
                    "school_a": str(schools[i]), "school_b": str(schools[j]),
                    "diff_elo": round(e1["difficulty_hat"] - e2["difficulty_hat"], 1),
                    "se_diff": round(se_diff, 1), "z": round(z, 2), "flagged": flagged,
                })
        if not invariant:
            n_flagged += 1
        items_out.append({
            "item_id": str(item_id),
            "competency_id": str(comp_of.get(item_id)),
            "n_schools": len(schools),
            "by_school": {str(sc): by_school[sc] for sc in schools},
            "comparisons": comparisons,
            "invariant": invariant,
            "action": "aucune" if invariant else
                      "revue : biais de contexte ou item ambigu — croiser avec DIF et item fit",
        })

    return {
        "analysis": "invariance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"min_per_school": min_per_school, "z_crit": z_crit},
        "n_items_comparable": len(items_out),
        "n_items_non_invariant": n_flagged,
        # Biais moyen par école : un décalage constant → cause ÉCOLE (passation),
        # pas items — à lire avant d'incriminer des items individuels.
        "school_mean_bias_elo": {
            str(sc): round(sum(v) / len(v), 1) for sc, v in sorted(
                school_bias.items(), key=lambda kv: str(kv[0]))
        },
        "items": items_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Invariance inter-écoles des difficultés d'items (±SE).")
    parser.add_argument("--min-per-school", type=int, default=DEFAULT_MIN_PER_SCHOOL,
                        help=f"réponses minimales par item × école (défaut {DEFAULT_MIN_PER_SCHOOL})")
    parser.add_argument("--z-crit", type=float, default=DEFAULT_Z_CRIT,
                        help=f"seuil z de non-invariance (défaut {DEFAULT_Z_CRIT} = 5 %% bilatéral)")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = run(s, min_per_school=args.min_per_school, z_crit=args.z_crit)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
