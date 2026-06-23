"""Workflow de revue humaine des items (T2.3).

- Persiste les items générés (T2.2) en base, statut `ai_generated`.
- Machine à états des statuts : aucune transition ne saute d'étape.
- Approuver / rejeter (soft delete, jamais détruit) / éditer.
- Trace le reviewer dans `provenance`.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.items.generation import GeneratedItem
from src.models.base import ItemStatus
from src.models.item import Item, ItemContent

# Cycle de vie autorisé : ai_generated → human_reviewed → linguist_validated → active.
# quarantined : sortie/réhabilitation du pool. Aucun saut d'étape.
ALLOWED_TRANSITIONS = {
    ItemStatus.AI_GENERATED: {ItemStatus.HUMAN_REVIEWED},
    ItemStatus.HUMAN_REVIEWED: {ItemStatus.LINGUIST_VALIDATED},
    ItemStatus.LINGUIST_VALIDATED: {ItemStatus.ACTIVE},
    ItemStatus.ACTIVE: {ItemStatus.QUARANTINED},
    ItemStatus.QUARANTINED: {ItemStatus.ACTIVE},
}

# Préconditions par statut cible. L'AR doit être validée pour franchir l'étape linguiste.
TRANSITION_GUARDS = {
    ItemStatus.LINGUIST_VALIDATED: lambda it: bool(it.ar_validated and it.content_ar),
}


class InvalidTransition(Exception):
    """Transition de statut interdite (saut d'étape, cible non autorisée, ou précondition non remplie)."""


def _stamp_reviewer(item: Item, reviewer: str, **extra) -> None:
    """Écrit l'identité du reviewer dans provenance (réassignation = change tracking)."""
    prov = dict(item.provenance or {})
    prov["reviewer"] = reviewer
    prov["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    prov.update(extra)
    item.provenance = prov


def insert_generated_items(session: Session, generated: List[GeneratedItem]) -> List[Item]:
    """Persiste des GeneratedItem en Item (statut ai_generated, content_ar en attente T2.4)."""
    items: List[Item] = []
    for g in generated:
        item = Item(
            competency_id=g.competency_id,
            content_en=g.content_en,
            content_ar=None,  # rempli en T2.4
            answer_format=g.answer_format,
            difficulty_prior=g.difficulty_prior,
            context_tags=dict(g.context_tags),
            status=ItemStatus.AI_GENERATED,
            provenance=dict(g.provenance or {}),
        )
        session.add(item)
        items.append(item)
    session.commit()
    return items


def list_pending(session: Session) -> List[Item]:
    """Items à revoir : ai_generated, non supprimés."""
    return list(
        session.execute(
            select(Item)
            .where(Item.status == ItemStatus.AI_GENERATED, Item.deleted_at.is_(None))
            .order_by(Item.created_at)
        ).scalars()
    )


def promote(session: Session, item: Item, target: ItemStatus, reviewer: str) -> Item:
    """Fait avancer l'item d'un cran. Lève InvalidTransition si le saut est interdit."""
    allowed = ALLOWED_TRANSITIONS.get(item.status, set())
    if target not in allowed:
        raise InvalidTransition(
            f"{item.status.value} → {target.value} interdit "
            f"(autorisé : {sorted(s.value for s in allowed) or 'aucun'})"
        )
    guard = TRANSITION_GUARDS.get(target)
    if guard is not None and not guard(item):
        raise InvalidTransition(
            f"{item.status.value} → {target.value} bloqué : précondition non remplie "
            "(AR non validée : ar_validated requis)."
        )
    item.status = target
    _stamp_reviewer(item, reviewer)
    session.commit()
    return item


def approve(session: Session, item: Item, reviewer: str) -> Item:
    """Raccourci : ai_generated → human_reviewed (AC1)."""
    return promote(session, item, ItemStatus.HUMAN_REVIEWED, reviewer)


def reject(session: Session, item: Item, reviewer: str, reason: str) -> Item:
    """Rejette un item : soft delete (jamais détruit), trace reviewer + raison (AC3)."""
    item.deleted_at = datetime.now()
    _stamp_reviewer(item, reviewer, rejected=True, reject_reason=reason)
    session.commit()
    return item


def edit(
    session: Session,
    item: Item,
    reviewer: str,
    *,
    content_en: Optional[dict] = None,
    context_tags: Optional[dict] = None,
) -> Item:
    """Corrige un item pendant la revue (le contenu reste validé par ItemContent)."""
    if content_en is not None:
        ItemContent.model_validate(content_en)  # garde-fou
        item.content_en = content_en
    if context_tags is not None:
        item.context_tags = dict(context_tags)
    _stamp_reviewer(item, reviewer, edited=True)
    session.commit()
    return item


# --- T2.4 : version arabe ---

def list_pending_arabic(session: Session) -> List[Item]:
    """Worklist du linguiste : items revus en EN (human_reviewed) dont l'AR n'est pas validée.

    C'est là que se joue la « descente » de l'arabe : ces items attendent une traduction
    proposée puis validée avant de pouvoir être servis (gate ar_validated).
    """
    return list(
        session.execute(
            select(Item)
            .where(
                Item.status == ItemStatus.HUMAN_REVIEWED,
                Item.ar_validated.is_(False),
                Item.deleted_at.is_(None),
            )
            .order_by(Item.created_at)
        ).scalars()
    )


def set_arabic(session: Session, item: Item, content_ar: dict, *, by: str) -> Item:
    """Pose/corrige `content_ar` (validé ItemContent). N'altère JAMAIS content_en (AC3).

    Repose ar_validated à False : toute modification AR doit être re-validée.
    """
    ItemContent.model_validate(content_ar)  # garde-fou
    item.content_ar = content_ar
    item.ar_validated = False
    _stamp_reviewer(item, by, ar_proposed_by=by)
    session.commit()
    return item


def validate_arabic(session: Session, item: Item, *, linguist: str) -> Item:
    """Le linguiste valide l'AR : ar_validated=True puis human_reviewed → linguist_validated.

    Exige un `content_ar` présent et conforme.
    """
    if not item.content_ar:
        raise InvalidTransition("Pas de content_ar à valider.")
    ItemContent.model_validate(item.content_ar)
    item.ar_validated = True
    _stamp_reviewer(item, linguist, ar_validated_by=linguist)
    session.commit()
    return promote(session, item, ItemStatus.LINGUIST_VALIDATED, reviewer=linguist)


# --- T2.5 : promotion en pool actif ---

def promote_to_active(session: Session, item: Item, reviewer: str) -> Item:
    """Promeut un item en `active` (servi aux élèves).

    Précondition explicite (AC1) : `ar_validated` requis. L'item doit aussi être
    `linguist_validated` (garanti par la machine à états : on n'y arrive qu'après
    revue EN + validation AR).
    """
    if not item.ar_validated:
        raise InvalidTransition("Promotion active refusée : ar_validated requis.")
    return promote(session, item, ItemStatus.ACTIVE, reviewer=reviewer)
