"""Speededness / désengagement — distribution de response_time_ms (C4.5).

`response_time_ms` est journalisé DEPUIS L'ORIGINE (pas de dépendance C-0, cf.
Cadrage-LotC §3/C-0 « note positive ») : cette analyse est la seule du plan C4
exécutable sur toutes les données historiques.

Détection du « rapid guessing » : une réponse sous le seuil (défaut 2 000 ms)
n'est pas une mesure — l'élève n'a pas lu l'item. Deux niveaux de sortie :
  1. réponses rapides → À EXCLURE des estimations (ré-estimation offline,
     calibration C2, analyses DIF/fit) — le moteur temps réel les a déjà
     consommées, l'exclusion vaut pour les analyses ;
  2. élèves dont la part de réponses rapides dépasse le taux d'alerte (défaut
     10 % sur ≥ 10 réponses) → signal de DÉSENGAGEMENT à remonter à l'enseignant
     (restitution), et exclusion de l'élève des études de calibration.

Sort aussi la distribution globale (quantiles) et par item (items à médiane
anormalement basse = candidats item trop facile / réponse devinable).

Usage  : DATABASE_URL=... python scripts/analysis/speededness.py
                          [--threshold-ms N] [--student-flag-rate X] [--min-student-n N]
Sortie : JSON sur stdout (lecture seule).
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
from src.models.measurement import Response

DEFAULT_THRESHOLD_MS = 2000     # sous ce temps : réponse « rapide » (non-mesure)
DEFAULT_STUDENT_FLAG_RATE = 0.10  # part de réponses rapides déclenchant le flag élève
DEFAULT_MIN_STUDENT_N = 10      # réponses minimales avant de flagger un élève


def quantile(ordered: List[int], q: float) -> float:
    """Quantile par interpolation linéaire sur une liste TRIÉE (stdlib pur)."""
    if not ordered:
        return float("nan")
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def distribution(times: List[int]) -> dict:
    ordered = sorted(times)
    return {
        "n": len(ordered),
        "min_ms": ordered[0],
        "p5_ms": round(quantile(ordered, 0.05), 1),
        "p25_ms": round(quantile(ordered, 0.25), 1),
        "median_ms": round(quantile(ordered, 0.50), 1),
        "p75_ms": round(quantile(ordered, 0.75), 1),
        "p95_ms": round(quantile(ordered, 0.95), 1),
        "max_ms": ordered[-1],
    }


def run(s: Session, *, threshold_ms: int, student_flag_rate: float,
        min_student_n: int) -> dict:
    all_times: List[int] = []
    n_missing = 0
    per_student: Dict[object, list] = {}  # student -> [n, n_rapid]
    per_item: Dict[object, list] = {}     # item -> [temps...]
    rapid_response_ids: List[str] = []

    # Colonnes explicites (jamais select(Response) entier) : robuste aux colonnes
    # du modèle pas encore migrées dans la base interrogée (ex. language, C-0).
    for rid, student_id, item_id, t in s.execute(
            select(Response.id, Response.student_id,
                   Response.item_id, Response.response_time_ms)):
        if t is None:
            n_missing += 1
            continue
        all_times.append(t)
        per_item.setdefault(item_id, []).append(t)
        cell = per_student.setdefault(student_id, [0, 0])
        cell[0] += 1
        if t < threshold_ms:
            cell[1] += 1
            rapid_response_ids.append(str(rid))

    n_rapid = len(rapid_response_ids)
    flagged_students = []
    for student_id, (n, nr) in sorted(per_student.items(), key=lambda kv: str(kv[0])):
        rate = nr / n
        if n >= min_student_n and rate > student_flag_rate:
            flagged_students.append({
                "student_id": str(student_id), "n_responses": n,
                "n_rapid": nr, "rapid_rate": round(rate, 3),
                "action": "signal désengagement (restitution enseignant) ; "
                          "exclure de l'étude de calibration C2",
            })

    # Items à médiane basse : réponse probablement devinable sans lecture.
    suspicious_items = []
    for item_id, times in per_item.items():
        med = quantile(sorted(times), 0.5)
        if len(times) >= min_student_n and med < threshold_ms:
            suspicious_items.append({"item_id": str(item_id), "n": len(times),
                                     "median_ms": round(med, 1)})
    suspicious_items.sort(key=lambda e: e["median_ms"])

    return {
        "analysis": "speededness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"threshold_ms": threshold_ms,
                   "student_flag_rate": student_flag_rate,
                   "min_student_n": min_student_n},
        "n_responses_with_time": len(all_times),
        "n_missing_time": n_missing,
        "distribution": distribution(all_times) if all_times else None,
        "n_rapid_responses": n_rapid,
        "rapid_rate_global": round(n_rapid / len(all_times), 4) if all_times else None,
        # Ids des réponses < seuil : liste d'exclusion pour les AUTRES analyses
        # (DIF, fit, calibration) — le journal reste intact (append-only).
        "rapid_response_ids": rapid_response_ids,
        "n_students_flagged": len(flagged_students),
        "flagged_students": flagged_students,
        "suspicious_items_low_median": suspicious_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Distribution des temps de réponse + détection rapid guessing.")
    parser.add_argument("--threshold-ms", type=int, default=DEFAULT_THRESHOLD_MS,
                        help=f"seuil de réponse rapide en ms (défaut {DEFAULT_THRESHOLD_MS})")
    parser.add_argument("--student-flag-rate", type=float, default=DEFAULT_STUDENT_FLAG_RATE,
                        help="part de réponses rapides déclenchant le flag élève "
                             f"(défaut {DEFAULT_STUDENT_FLAG_RATE})")
    parser.add_argument("--min-student-n", type=int, default=DEFAULT_MIN_STUDENT_N,
                        help=f"réponses minimales avant de flagger un élève (défaut {DEFAULT_MIN_STUDENT_N})")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = run(s, threshold_ms=args.threshold_ms,
                     student_flag_rate=args.student_flag_rate,
                     min_student_n=args.min_student_n)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
