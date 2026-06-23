"""Logique de session adaptative (Epic 4, T4.3) — réutilise T4.1/T4.2/T3.4.

Testable sans HTTP. Les endpoints FastAPI (app.py) ne font qu'appeler ces fonctions.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.audit import log_action
from src.engine.selection import CompetencyState, ItemRef, select_next
from src.engine.service import ELO_START, on_response
from src.engine.stopping import StopConfig, should_stop
from src.items.quarantine import active_pool
from src.models.base import EdgeType
from src.models.competency import CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, StudentCompetencyAbility
from src.models.session import AssessmentSession


class AlreadyAnswered(Exception):
    """Item déjà répondu dans cette session (anti double-comptage, AC5)."""


def _public_content(content: Optional[dict]) -> Optional[dict]:
    """Contenu SANS la clé de correction (jamais envoyée au client)."""
    if not content:
        return content
    return {k: v for k, v in content.items() if k != "answer"}


def grade_answer(item: Item, selected: str, lang: str = "en") -> bool:
    """Correction CÔTÉ SERVEUR : compare la réponse choisie à la clé de l'item."""
    content = item.content_ar if (lang == "ar" and item.content_ar) else item.content_en
    return selected is not None and selected == content.get("answer")


def start_session(
    s: Session, *, student_id: uuid.UUID, school_id: uuid.UUID,
    target_competency_ids: Optional[List] = None,
) -> AssessmentSession:
    sess = AssessmentSession(
        student_id=student_id, school_id=school_id,
        target_competency_ids=[str(c) for c in target_competency_ids] if target_competency_ids else None,
    )
    s.add(sess)
    s.flush()  # pour disposer de sess.id
    log_action(s, action="session.create", school_id=school_id, resource_type="session",
               resource_id=sess.id, details={"student_id": str(student_id)})
    s.commit()
    return sess


def _seen_item_ids(s: Session, session_id) -> set:
    rows = s.execute(select(Response.item_id).where(Response.session_id == session_id)).scalars().all()
    return set(rows)


def _build(s: Session, session: AssessmentSession):
    """Construit candidats, états, items, prérequis HARD pour la sélection."""
    items_db = active_pool(s)
    by_comp = {}
    for it in items_db:
        by_comp.setdefault(it.competency_id, []).append(it)

    candidate_ids = set(by_comp)
    if session.target_competency_ids:
        targets = {uuid.UUID(c) if isinstance(c, str) else c for c in session.target_competency_ids}
        candidate_ids &= targets

    abilities = {
        a.competency_id: a
        for a in s.execute(
            select(StudentCompetencyAbility).where(StudentCompetencyAbility.student_id == session.student_id)
        ).scalars()
    }

    def state(cid) -> CompetencyState:
        a = abilities.get(cid)
        if a is None:
            return CompetencyState(cid, ELO_START, 0.0, 0)
        return CompetencyState(cid, a.ability_elo, a.confidence, a.n_direct)

    hard_prereqs = {}
    for e in s.execute(
        select(CompetencyPrerequisite).where(CompetencyPrerequisite.edge_type == EdgeType.HARD)
    ).scalars():
        hard_prereqs.setdefault(e.target_id, []).append(e.source_id)

    candidates = [state(cid) for cid in candidate_ids]
    referenced = set(candidate_ids)
    for cid in candidate_ids:
        referenced.update(hard_prereqs.get(cid, []))
    states_by_id = {cid: state(cid) for cid in referenced}

    items = [ItemRef(it.id, it.competency_id, it.difficulty_elo, "active") for it in items_db]
    return candidates, states_by_id, items, hard_prereqs


def _finish(s: Session, session: AssessmentSession, reason: str) -> dict:
    session.status = "completed"
    session.stop_reason = reason
    session.ended_at = datetime.now()
    s.commit()
    return {"done": True, "reason": reason}


def next_item(s: Session, session: AssessmentSession, config: StopConfig = StopConfig()) -> dict:
    if session.status == "completed":
        return {"done": True, "reason": session.stop_reason}

    candidates, states_by_id, items, hard_prereqs = _build(s, session)
    n_served = len(_seen_item_ids(s, session.id))
    elapsed = (datetime.now() - session.started_at).total_seconds()
    decision = should_stop([c.confidence for c in candidates], n_served, elapsed, config)
    if decision.stop:
        return _finish(s, session, decision.reason)

    comp, item_id = select_next(candidates, items, _seen_item_ids(s, session.id),
                                hard_prereqs=hard_prereqs, states_by_id=states_by_id)
    if item_id is None:
        return _finish(s, session, "no_items")

    item = s.get(Item, item_id)
    return {
        "done": False,
        "session_id": str(session.id),
        "competency_id": str(comp),
        "item_id": str(item.id),
        "answer_format": item.answer_format.value,
        "content_en": _public_content(item.content_en),       # sans la clé de correction
        "content_ar": _public_content(item.content_ar),       # peut être None (AR non traduit)
    }


def submit_response(
    s: Session, session: AssessmentSession, *, item_id: uuid.UUID,
    is_correct: bool, response_time_ms: Optional[int] = None,
    config: StopConfig = StopConfig(),
) -> dict:
    if item_id in _seen_item_ids(s, session.id):
        raise AlreadyAnswered(str(item_id))
    resp = on_response(
        s, student_id=session.student_id, item_id=item_id, is_correct=is_correct,
        school_id=session.school_id, session_id=session.id, response_time_ms=response_time_ms,
    )
    log_action(s, action="response.submit", school_id=session.school_id, resource_type="response",
               resource_id=resp.id, details={"student_id": str(session.student_id),
                                             "item_id": str(item_id), "correct": is_correct})
    s.commit()
    return next_item(s, session, config)
