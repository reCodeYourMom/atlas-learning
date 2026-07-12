"""Fidélité — split-half pair/impair + correction de Spearman-Brown (C4.3).

Par compétence : les réponses de chaque élève sont ordonnées chronologiquement
(created_at, puis id pour un ordre stable), puis séparées en deux moitiés par
POSITION (impaire = 1re, 3e, 5e… ; paire = 2e, 4e, 6e…) — le découpage pair/impair
neutralise les effets de fatigue/apprentissage qu'un découpage première/seconde
moitié confondrait avec l'erreur de mesure.

Le score de chaque moitié = taux de réussite. La corrélation de Pearson entre
les deux moitiés (r_half, sur les élèves ayant assez de réponses) est corrigée
par Spearman-Brown pour estimer la fidélité du test complet :

    r_sb = 2·r_half / (1 + r_half)

Lecture (seuils indicatifs pilote, cf. Plan-Analyses-Pilote.md) :
  r_sb ≥ 0.7   acceptable pour un usage diagnostique formatif ;
  0.5–0.7      publier avec réserve (SE affichée), viser plus de réponses ;
  < 0.5        alerte — mesure trop bruitée pour être restituée sur cette compétence.

Limite assumée : sur un flux ADAPTATIF, les items ne sont pas parallèles entre
moitiés — r_sb est un ordre de grandeur, pas un alpha de Cronbach de test fixe.
Le manuel (C1) documente cette lecture.

Usage  : DATABASE_URL=... python scripts/analysis/reliability.py
                          [--min-responses N] [--min-students N]
Sortie : JSON sur stdout (lecture seule).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import SessionLocal, make_engine
from src.models.measurement import Response

DEFAULT_MIN_RESPONSES = 6   # par élève × compétence (≥3 items par moitié)
DEFAULT_MIN_STUDENTS = 10   # élèves minimum pour publier un r par compétence


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Corrélation de Pearson, None si variance nulle (r indéfini)."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    if vx == 0.0 or vy == 0.0:
        return None
    return cov / (vx * vy)


def spearman_brown(r_half: float) -> Optional[float]:
    """Fidélité corrigée test complet. None si r_half = -1 (dénominateur nul)."""
    if r_half <= -1.0:
        return None
    return 2.0 * r_half / (1.0 + r_half)


def split_half_scores(rows: List[Tuple]) -> Tuple[float, float]:
    """(score moitié impaire, score moitié paire) — rows déjà triées, bool par réponse."""
    odd = [ok for i, ok in enumerate(rows) if i % 2 == 0]   # positions 1,3,5… (1-based)
    even = [ok for i, ok in enumerate(rows) if i % 2 == 1]  # positions 2,4,6…
    return (sum(odd) / len(odd), sum(even) / len(even))


def run(s: Session, *, min_responses: int, min_students: int) -> dict:
    # (student, competency) -> [(created_at, id, is_correct)] trié chronologiquement.
    # Colonnes explicites (jamais select(Response) entier) : robuste aux colonnes
    # du modèle pas encore migrées dans la base interrogée (ex. language, C-0).
    per_cell: Dict[tuple, list] = {}
    for student_id, competency_id, created_at, rid, is_correct in s.execute(
            select(Response.student_id, Response.competency_id,
                   Response.created_at, Response.id, Response.is_correct)):
        per_cell.setdefault((student_id, competency_id), []).append(
            (created_at, str(rid), bool(is_correct)))

    by_comp: Dict[object, list] = {}  # competency -> [(odd_score, even_score, n)]
    for (student_id, comp_id), rows in per_cell.items():
        if len(rows) < min_responses:
            continue
        rows.sort(key=lambda t: (t[0] is None, t[0], t[1]))  # created_at puis id (stable)
        odd, even = split_half_scores([ok for _, _, ok in rows])
        by_comp.setdefault(comp_id, []).append((odd, even, len(rows)))

    comps_out, n_below = [], 0
    for comp_id, pairs in sorted(by_comp.items(), key=lambda kv: str(kv[0])):
        entry = {"competency_id": str(comp_id), "n_students": len(pairs),
                 "mean_n_responses": round(sum(n for _, _, n in pairs) / len(pairs), 1)}
        if len(pairs) < min_students:
            entry.update({"status": "insufficient",
                          "note": f"moins de {min_students} élèves exploitables"})
            comps_out.append(entry)
            continue
        r_half = pearson([o for o, _, _ in pairs], [e for _, e, _ in pairs])
        if r_half is None:
            entry.update({"status": "degenerate",
                          "note": "variance nulle sur une des moitiés (r indéfini)"})
            comps_out.append(entry)
            continue
        r_sb = spearman_brown(r_half)
        entry.update({
            "status": "ok",
            "r_split_half": round(r_half, 4),
            "r_spearman_brown": round(r_sb, 4) if r_sb is not None else None,
        })
        if r_sb is not None and r_sb < 0.5:
            entry["alert"] = "fidélité < 0.5 — mesure trop bruitée pour restitution"
            n_below += 1
        comps_out.append(entry)

    return {
        "analysis": "reliability",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"min_responses": min_responses, "min_students": min_students},
        "n_competencies_analyzed": sum(1 for c in comps_out if c.get("status") == "ok"),
        "n_alerts": n_below,
        "competencies": comps_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fidélité split-half pair/impair + Spearman-Brown, par compétence.")
    parser.add_argument("--min-responses", type=int, default=DEFAULT_MIN_RESPONSES,
                        help=f"réponses minimales par élève × compétence (défaut {DEFAULT_MIN_RESPONSES})")
    parser.add_argument("--min-students", type=int, default=DEFAULT_MIN_STUDENTS,
                        help=f"élèves minimum par compétence (défaut {DEFAULT_MIN_STUDENTS})")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = run(s, min_responses=args.min_responses, min_students=args.min_students)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
