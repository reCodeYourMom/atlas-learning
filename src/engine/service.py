"""Orchestrateur on_response (Epic 3, T3.4).

À la réception d'une réponse : écrit la `response`, met à jour l'Elo direct (T3.1),
la confiance (T3.2), propage aux voisins (T3.3) — le tout en UNE transaction atomique.
Aucun LLM. Isolation tenant (school_id sur toutes les écritures).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from src.engine.elo import Neighbor, confidence, propagate, update_elo
from src.models.competency import CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, StudentCompetencyAbility

ELO_START = 1500.0  # ability initiale (centre de l'échelle) tant que jamais mesurée


def _ability(session: Session, student_id, competency_id, school_id) -> StudentCompetencyAbility:
    row = session.get(StudentCompetencyAbility, (student_id, competency_id))
    if row is None:
        row = StudentCompetencyAbility(
            student_id=student_id, competency_id=competency_id, school_id=school_id,
            ability_elo=ELO_START, n_direct=0, confidence=0.0,
        )
        session.add(row)
    return row


def on_response(
    session: Session,
    *,
    student_id: uuid.UUID,
    item_id: uuid.UUID,
    is_correct: bool,
    school_id: uuid.UUID,
    response_time_ms: Optional[int] = None,
    session_id: Optional[uuid.UUID] = None,
    response_id: Optional[uuid.UUID] = None,
) -> Response:
    """Applique une réponse de bout en bout (transaction atomique). Retourne la Response.

    Idempotent : rejouer la même `response_id` ne réapplique pas l'effet.
    """
    if response_id is not None:
        existing = session.get(Response, response_id)
        if existing is not None:
            return existing  # déjà appliquée

    try:
        item = session.get(Item, item_id)
        if item is None:
            raise ValueError(f"item {item_id} introuvable")
        comp_id = item.competency_id

        # --- update Elo direct (T3.1 + T3.2) ---
        ability = _ability(session, student_id, comp_id, school_id)
        old_ability = ability.ability_elo
        new_ability, new_item_diff = update_elo(
            ability.ability_elo, item.difficulty_elo, is_correct,
            ability.n_direct, item.n_responses,
        )
        ability.ability_elo = new_ability
        ability.n_direct += 1
        ability.confidence = confidence(ability.n_direct)
        ability.last_measured_at = datetime.now()
        item.difficulty_elo = new_item_diff
        item.n_responses += 1
        delta = new_ability - old_ability

        # --- propagation 1-saut (T3.3) ---
        edges = session.execute(
            select(CompetencyPrerequisite).where(
                or_(CompetencyPrerequisite.source_id == comp_id,
                    CompetencyPrerequisite.target_id == comp_id)
            )
        ).scalars().all()
        neighbors = []
        for e in edges:
            nb_comp = e.target_id if e.source_id == comp_id else e.source_id
            nb_row = session.get(StudentCompetencyAbility, (student_id, nb_comp))
            neighbors.append(Neighbor(
                competency_id=nb_comp,
                ability=nb_row.ability_elo if nb_row else ELO_START,
                confidence=nb_row.confidence if nb_row else 0.0,
                correlation_strength=e.correlation_strength,
                edge_type=e.edge_type.value,
            ))
        for p in propagate(delta, ability.confidence, neighbors):
            nb_row = _ability(session, student_id, p.competency_id, school_id)
            nb_row.ability_elo = p.new_ability      # inféré : on ne touche PAS n_direct ni confidence

        # --- response append-only ---
        resp = Response(
            id=response_id or uuid.uuid4(),
            school_id=school_id, student_id=student_id, item_id=item_id,
            competency_id=comp_id, is_correct=is_correct,
            response_time_ms=response_time_ms, session_id=session_id,
            created_at=datetime.now(),
        )
        session.add(resp)
        session.commit()
        return resp
    except Exception:
        session.rollback()
        raise
