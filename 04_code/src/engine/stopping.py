"""Règles d'arrêt de session (Epic 4, T4.2).

Fonction pure. Arrêt si : confiance cible atteinte sur TOUTES les compétences visées,
OU plafond d'items atteint, OU temps écoulé. Paramètres en config (pas en dur).
"""
from __future__ import annotations

from typing import List, NamedTuple, Optional


class StopConfig(NamedTuple):
    confidence_threshold: float = 0.75
    max_items: int = 25
    max_time_s: float = 1200.0


class StopDecision(NamedTuple):
    stop: bool
    reason: Optional[str]  # "confidence" | "max_items" | "time" | None


def should_stop(
    target_confidences: List[float],
    n_items_served: int,
    elapsed_s: float,
    config: StopConfig = StopConfig(),
) -> StopDecision:
    """Décide l'arrêt et renvoie la raison. Ordre : confiance, puis plafond, puis temps."""
    if target_confidences and all(c >= config.confidence_threshold for c in target_confidences):
        return StopDecision(True, "confidence")
    if n_items_served >= config.max_items:
        return StopDecision(True, "max_items")
    if elapsed_s >= config.max_time_s:
        return StopDecision(True, "time")
    return StopDecision(False, None)
