"""Item fit systématique — observé vs attendu logistique par bins d'ability (C4.2).

Extension ANALYTIQUE du garde-fou quarantaine (src/items/quarantine.py, T2.5) :
là où le job cron ne regarde que la divergence GLOBALE observé/attendu, ce script
trace la courbe par bins d'ability des répondants — un item peut être globalement
« dans les clous » mais mal discriminer (plat) ou s'inverser (piège linguistique).

Réutilise TEL QUEL le modèle logistique et le seuil du garde-fou :
  - expected_success(difficulty_elo, ability) : P(réussite) type Elo/Rasch ;
  - is_drifting / ItemStats : mêmes seuils que le job quarantaine (n ≥ 30,
    divergence > 0.40) → tout item flaggé ici SERA quarantainé par le cron ;
  - référence = ability MOYENNE RÉELLE des répondants (jamais la constante 1200),
    même convention que scripts/run_quarantine.py.

Approximation documentée : l'ability utilisée est l'ability ACTUELLE de l'élève
(StudentCompetencyAbility), pas celle au moment de la réponse (non journalisée).
Acceptable sur un pilote court ; à réévaluer si les fenêtres d'analyse s'allongent.

Usage  : DATABASE_URL=... python scripts/analysis/item_fit.py
                          [--min-responses N] [--bins N] [--max-divergence X]
Sortie : JSON sur stdout (lecture seule — la mise en quarantaine reste le rôle
         exclusif de scripts/run_quarantine.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db import SessionLocal, make_engine
from src.engine.service import ELO_START
from src.items.quarantine import (
    DEFAULT_MAX_DIVERGENCE,
    DEFAULT_MIN_RESPONSES,
    ItemStats,
    expected_success,
    is_drifting,
)
from src.models.item import Item
from src.models.measurement import Response, StudentCompetencyAbility

DEFAULT_BINS = 5


def _bin_edges(values: List[float], bins: int) -> List[float]:
    """Bornes internes de bins équi-peuplés (quantiles), croissantes."""
    ordered = sorted(values)
    n = len(ordered)
    return [ordered[(k * n) // bins] for k in range(1, bins)]


def run(s: Session, *, min_responses: int, bins: int, max_divergence: float) -> dict:
    ability: Dict[tuple, float] = {
        (row.student_id, row.competency_id): row.ability_elo
        for row in s.execute(
            select(StudentCompetencyAbility.student_id,
                   StudentCompetencyAbility.competency_id,
                   StudentCompetencyAbility.ability_elo)
        )
    }
    items = {i.id: i for i in s.execute(select(Item)).scalars()}

    by_item: Dict[object, list] = {}  # item_id -> [(ability, is_correct)]
    # Colonnes explicites (jamais select(Response) entier) : robuste aux colonnes
    # du modèle pas encore migrées dans la base interrogée (ex. language, C-0).
    for student_id, competency_id, item_id, is_correct in s.execute(
            select(Response.student_id, Response.competency_id,
                   Response.item_id, Response.is_correct)):
        ab = ability.get((student_id, competency_id), ELO_START)
        by_item.setdefault(item_id, []).append((ab, bool(is_correct)))

    items_out, n_flagged = [], 0
    for item_id, rows in sorted(by_item.items(), key=lambda kv: str(kv[0])):
        item = items.get(item_id)
        if item is None:
            continue  # réponse orpheline (ne devrait pas exister : FK RESTRICT)
        n = len(rows)
        if n < min_responses:
            continue  # anti-bruit : même convention AC4 que la quarantaine
        obs_global = sum(1 for _, ok in rows if ok) / n
        reference = sum(ab for ab, _ in rows) / n
        stats = ItemStats(n_responses=n, success_rate=obs_global,
                          difficulty_elo=item.difficulty_elo)
        flagged = is_drifting(stats, min_responses=min_responses,
                              max_divergence=max_divergence, reference_ability=reference)

        # Courbe observé/attendu par bins d'ability (quantiles des répondants).
        edges = _bin_edges([ab for ab, _ in rows], bins)
        buckets: List[list] = [[] for _ in range(bins)]
        for ab, ok in rows:
            k = sum(1 for e in edges if ab >= e)
            buckets[k].append((ab, ok))
        bins_out, weighted_abs = [], 0.0
        for k, bucket in enumerate(buckets):
            if not bucket:
                continue
            nb = len(bucket)
            obs = sum(1 for _, ok in bucket if ok) / nb
            exp = sum(expected_success(item.difficulty_elo, ab) for ab, _ in bucket) / nb
            weighted_abs += nb * abs(obs - exp)
            bins_out.append({"bin": k, "n": nb,
                             "ability_mean": round(sum(ab for ab, _ in bucket) / nb, 1),
                             "observed": round(obs, 4), "expected": round(exp, 4),
                             "divergence": round(obs - exp, 4)})

        if flagged:
            n_flagged += 1
        items_out.append({
            "item_id": str(item_id),
            "competency_id": str(item.competency_id),
            "status": getattr(item.status, "value", str(item.status)),
            "difficulty_elo": round(item.difficulty_elo, 1),
            "n_responses": n,
            "reference_ability": round(reference, 1),
            "observed_global": round(obs_global, 4),
            "expected_at_reference": round(expected_success(item.difficulty_elo, reference), 4),
            "global_divergence": round(
                abs(obs_global - expected_success(item.difficulty_elo, reference)), 4),
            "mean_abs_bin_divergence": round(weighted_abs / n, 4),
            "bins": bins_out,
            "flagged": flagged,
            "action": ("candidat quarantaine (sera saisi par run_quarantine)"
                       if flagged else "aucune"),
        })

    return {
        "analysis": "item_fit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"min_responses": min_responses, "bins": bins,
                   "max_divergence": max_divergence},
        "n_items_analyzed": len(items_out),
        "n_flagged": n_flagged,
        "items": items_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Item fit : observé vs attendu logistique par bins d'ability.")
    parser.add_argument("--min-responses", type=int, default=DEFAULT_MIN_RESPONSES,
                        help=f"réponses minimales par item (défaut {DEFAULT_MIN_RESPONSES}, "
                             "même seuil que la quarantaine)")
    parser.add_argument("--bins", type=int, default=DEFAULT_BINS,
                        help=f"nb de bins d'ability (défaut {DEFAULT_BINS})")
    parser.add_argument("--max-divergence", type=float, default=DEFAULT_MAX_DIVERGENCE,
                        help=f"seuil de flag observé/attendu (défaut {DEFAULT_MAX_DIVERGENCE}, "
                             "même seuil que la quarantaine)")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = run(s, min_responses=args.min_responses, bins=args.bins,
                     max_divergence=args.max_divergence)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
