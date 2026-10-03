"""Agrégation des abilities : compétence → strand → matière (Epic 5, T5.1).

Pondérée par confiance (une ability peu sûre pèse moins). Distingue mesuré/inféré.
Fonction pure. Neutre matière (le strand vient du code `SUBJECT.GRADE.STRAND.SKILL`).
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple


class AbilityRecord(NamedTuple):
    competency_code: str       # ex. MATH.G4.NF.ADD_UNLIKE_LCM
    ability: float
    confidence: float          # [0..1]
    n_direct: int


class AggregateScore(NamedTuple):
    score: float
    confidence: float          # confiance moyenne du regroupement
    measured: bool             # True si ≥1 mesure directe ; sinon "estimé"
    n_competencies: int


def subject_of(code: str) -> str:
    return code.split(".")[0]


def strand_of(code: str) -> str:
    parts = code.split(".")
    return ".".join(parts[:3]) if len(parts) >= 3 else code  # SUBJECT.GRADE.STRAND


def _aggregate(records: List[AbilityRecord]) -> AggregateScore:
    if not records:
        return AggregateScore(0.0, 0.0, False, 0)
    total_w = sum(r.confidence for r in records)
    if total_w > 0:
        score = sum(r.ability * r.confidence for r in records) / total_w
    else:
        score = sum(r.ability for r in records) / len(records)  # aucune confiance → moyenne brute
    measured = any(r.n_direct > 0 for r in records)
    conf_mean = sum(r.confidence for r in records) / len(records)
    return AggregateScore(round(score, 1), round(conf_mean, 3), measured, len(records))


def aggregate(records: List[AbilityRecord]) -> Dict[str, object]:
    """Retourne l'agrégat par strand et par matière (pondéré confiance)."""
    by_strand: Dict[str, List[AbilityRecord]] = {}
    by_subject: Dict[str, List[AbilityRecord]] = {}
    for r in records:
        by_strand.setdefault(strand_of(r.competency_code), []).append(r)
        by_subject.setdefault(subject_of(r.competency_code), []).append(r)
    return {
        "strands": {k: _aggregate(v) for k, v in by_strand.items()},
        "subjects": {k: _aggregate(v) for k, v in by_subject.items()},
    }
