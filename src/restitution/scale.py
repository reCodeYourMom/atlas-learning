"""Couche de restitution (Epic 5, T5.2) : Elo interne → lisible (percentile, niveau, bande).

Strictement séparée du moteur : changer la table d'ancrage ne touche pas l'Elo.
Confiance basse → on affiche une fourchette (honnêteté : estimation vs mesure).
"""
from __future__ import annotations

from typing import List, NamedTuple, Optional, Tuple


class Anchor(NamedTuple):
    elo: float
    percentile: float    # [0..100]
    level: str           # ex. "G3", "G4"


class AnchorTable:
    """Table de correspondance Elo → percentile/niveau, CONFIGURABLE (pas en dur)."""

    def __init__(self, anchors: List[Anchor]):
        self.anchors = sorted(anchors, key=lambda a: a.elo)

    def percentile(self, elo: float) -> float:
        a = self.anchors
        if elo <= a[0].elo:
            return a[0].percentile
        if elo >= a[-1].elo:
            return a[-1].percentile
        for lo, hi in zip(a, a[1:]):
            if lo.elo <= elo <= hi.elo:
                t = (elo - lo.elo) / (hi.elo - lo.elo)
                return round(lo.percentile + t * (hi.percentile - lo.percentile), 1)
        return a[-1].percentile

    def level(self, elo: float) -> str:
        chosen = self.anchors[0]
        for a in self.anchors:
            if elo >= a.elo:
                chosen = a
        return chosen.level


class Restitution(NamedTuple):
    percentile: float
    level: str
    is_range: bool
    percentile_range: Optional[Tuple[float, float]]  # si confiance basse


def restitute(
    ability: float,
    confidence: float,
    table: AnchorTable,
    *,
    confidence_threshold: float = 0.5,
    band: float = 150.0,
) -> Restitution:
    """Convertit une ability en restitution lisible. Fourchette si confiance basse."""
    pct = table.percentile(ability)
    lvl = table.level(ability)
    if confidence < confidence_threshold:
        lo = table.percentile(ability - band)
        hi = table.percentile(ability + band)
        return Restitution(pct, lvl, True, (lo, hi))
    return Restitution(pct, lvl, False, None)


# Table d'ancrage par défaut (barème expert ; à remplacer par cohorte réelle plus tard).
DEFAULT_ANCHORS = AnchorTable([
    Anchor(1000, 5, "G2"),
    Anchor(1300, 25, "G3"),
    Anchor(1500, 50, "G4"),
    Anchor(1800, 75, "G5"),
    Anchor(2100, 95, "G6"),
])
