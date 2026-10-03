"""Garde-fou quarantaine (T2.5).

Détecte les items `active` dont les statistiques de terrain divergent de leur
difficulté annoncée, et les sort du pool servi (`quarantined`). Réversible.

La détection est une fonction PURE (stats injectées) : testable sans Epic 4,
puis branchable sur le trafic réel (table response) quand il existera.
"""
from __future__ import annotations

from typing import List, NamedTuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.items.review import _stamp_reviewer
from src.models.base import ItemStatus
from src.models.item import Item

# Ability de référence (échelle Elo) servant d'étalon au taux de réussite attendu.
DEFAULT_REFERENCE_ABILITY = 1200.0
# Nb minimal de réponses avant de juger (anti-bruit, AC4).
DEFAULT_MIN_RESPONSES = 30
# Écart maximal toléré entre taux observé et attendu avant quarantaine.
DEFAULT_MAX_DIVERGENCE = 0.40


class ItemStats(NamedTuple):
    n_responses: int
    success_rate: float       # [0..1] taux de réussite observé
    difficulty_elo: float


def expected_success(difficulty_elo: float, reference_ability: float = DEFAULT_REFERENCE_ABILITY) -> float:
    """Probabilité de réussite attendue (modèle logistique type Elo) à l'ability de référence."""
    return 1.0 / (1.0 + 10.0 ** ((difficulty_elo - reference_ability) / 400.0))


def is_drifting(
    stats: ItemStats,
    *,
    min_responses: int = DEFAULT_MIN_RESPONSES,
    max_divergence: float = DEFAULT_MAX_DIVERGENCE,
    reference_ability: float = DEFAULT_REFERENCE_ABILITY,
) -> bool:
    """True si l'item dérive : assez de réponses ET écart observé/attendu trop grand.

    En dessous de `min_responses`, retourne toujours False (pas de quarantaine sur du bruit, AC4).
    """
    if stats.n_responses < min_responses:
        return False
    exp = expected_success(stats.difficulty_elo, reference_ability)
    return abs(stats.success_rate - exp) > max_divergence


def apply_quarantine(
    session: Session,
    item: Item,
    stats: ItemStats,
    *,
    by: str = "system",
    min_responses: int = DEFAULT_MIN_RESPONSES,
    max_divergence: float = DEFAULT_MAX_DIVERGENCE,
    reference_ability: float = DEFAULT_REFERENCE_ABILITY,
) -> bool:
    """Met l'item en `quarantined` s'il est `active` ET qu'il dérive. Retourne True si quarantaine.

    Réversible plus tard via review.promote(item, ItemStatus.ACTIVE, ...).
    """
    if item.status != ItemStatus.ACTIVE:
        return False
    if not is_drifting(stats, min_responses=min_responses,
                       max_divergence=max_divergence, reference_ability=reference_ability):
        return False
    from src.items.review import promote  # import local : évite un cycle au chargement

    exp = expected_success(stats.difficulty_elo, reference_ability)
    promote(session, item, ItemStatus.QUARANTINED, reviewer=by)
    _stamp_reviewer(
        item, by, quarantined=True,
        quarantine_reason=(
            f"dérive: réussite {stats.success_rate:.2f} vs attendu {exp:.2f} "
            f"sur {stats.n_responses} réponses"
        ),
    )
    session.commit()
    return True


def active_pool(session: Session, competency_id=None) -> List[Item]:
    """Items réellement servables : status active, non supprimés. Exclut quarantined (AC3).

    Base de la sélection d'item (Epic 4).
    """
    stmt = select(Item).where(Item.status == ItemStatus.ACTIVE, Item.deleted_at.is_(None))
    if competency_id is not None:
        stmt = stmt.where(Item.competency_id == competency_id)
    return list(session.execute(stmt).scalars())
