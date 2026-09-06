"""Logique de session adaptative (Epic 4, T4.3) — réutilise T4.1/T4.2/T3.4.

Testable sans HTTP. Les endpoints FastAPI (app.py) ne font qu'appeler ces fonctions.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.audit import log_action
from src.engine.selection import CompetencyState, ItemRef, select_next
from src.engine.service import ELO_START, on_response
from src.models.competency import Competency
from src.restitution.diagnosis import MASTERY_ELO
from src.restitution.scale import DEFAULT_ANCHORS, restitute
from src.engine.stopping import StopConfig, should_stop
from src.items.quarantine import active_pool
from src.models.base import EdgeType, ResponseLanguage, ensure_utc, utcnow
from src.models.competency import CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, StudentCompetencyAbility
from src.models.session import AssessmentSession


class AlreadyAnswered(Exception):
    """Item déjà répondu dans cette session (anti double-comptage, AC5)."""


class SessionCompleted(Exception):
    """Session terminée : toute nouvelle réponse est refusée (409 côté API).

    Contrairement à next_item (qui répond {done: true} — contrat de FIN de flux),
    accepter un POST de réponse ici bougerait l'Elo HORS du flux adaptatif, alors que
    l'arrêt a été décidé par should_stop (revue 2026-07-08).
    """


# Namespace UUIDv5 du projet pour dériver un response_id DÉTERMINISTE de
# (session_id, item_id) : rejouer le même submit (double-clic, retry réseau) produit
# le MÊME id, que le moteur reconnaît → son idempotence par response_id devient
# effective de bout en bout (revue 2026-07-07).
RESPONSE_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "atlas-learning/response")


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
    target_competency_ids: Optional[List] = None, locale: str = "en",
) -> AssessmentSession:
    # Locale validée ICI aussi (fonction appelable hors HTTP) : une valeur hors enum
    # ne serait rejetée que par Postgres — trop tard, et jamais sur SQLite (dev/CI).
    try:
        loc = ResponseLanguage(locale)
    except ValueError:
        raise ValueError(f"locale invalide : {locale!r} (attendu 'en' ou 'ar')")
    sess = AssessmentSession(
        student_id=student_id, school_id=school_id,
        target_competency_ids=[str(c) for c in target_competency_ids] if target_competency_ids else None,
        locale=loc,
    )
    s.add(sess)
    s.flush()  # pour disposer de sess.id
    log_action(s, action="session.create", school_id=school_id, resource_type="session",
               resource_id=sess.id, details={"student_id": str(student_id), "locale": loc.value})
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


def _mastery_snapshot(s: Session, student_id, competency_id) -> dict:
    """État de maîtrise d'UNE compétence pour cet élève, en langage de restitution.

    Sert le « avant/après » d'une réponse : c'est le seul endroit du produit où
    l'estimation de maîtrise se voit BOUGER en direct. Une compétence encore jamais
    mesurée part de la valeur d'entrée du moteur (ELO_START), pas de zéro.
    """
    ability = s.execute(
        select(StudentCompetencyAbility).where(
            StudentCompetencyAbility.student_id == student_id,
            StudentCompetencyAbility.competency_id == competency_id,
        )
    ).scalar_one_or_none()
    elo = ability.ability_elo if ability else ELO_START
    conf = ability.confidence if ability else 0.0
    n_direct = ability.n_direct if ability else 0
    r = restitute(elo, conf, DEFAULT_ANCHORS)
    return {
        "elo": round(elo, 1),
        "percentile": r.percentile,
        "level": r.level,
        "confidence": round(conf, 3),
        "n_direct": n_direct,
        # Au-dessus du seuil ET réellement mesuré — même garde que les vues enseignant.
        "mastered": n_direct > 0 and elo >= MASTERY_ELO,
    }


def _finish(s: Session, session: AssessmentSession, reason: str) -> dict:
    session.status = "completed"
    session.stop_reason = reason
    session.ended_at = utcnow()
    s.commit()
    return {"done": True, "reason": reason}


def next_item(s: Session, session: AssessmentSession, config: StopConfig = StopConfig()) -> dict:
    if session.status == "completed":
        return {"done": True, "reason": session.stop_reason}

    candidates, states_by_id, items, hard_prereqs = _build(s, session)
    n_served = len(_seen_item_ids(s, session.id))
    # ensure_utc : started_at relu de SQLite est naïf (convention UTC) → sans
    # normalisation, la soustraction aware − naïf lèverait TypeError.
    elapsed = (utcnow() - ensure_utc(session.started_at)).total_seconds()
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
    # Ordre des refus : du plus SPÉCIFIQUE au plus général. Les deux sortent en 409, mais
    # ils ne disent pas la même chose au client — et « déjà répondu » est la cause réelle
    # quand elle s'applique. Depuis que la sélection ne re-sert plus un item vu, une
    # session peut se clore juste après le dernier item disponible : tester d'abord l'état
    # de session faisait alors répondre « session terminée » au rejeu d'un item, masquant
    # le double-submit. Aucun risque à inverser : les deux branches lèvent avant tout effet.
    #
    # Garde rapide (non atomique) : rejette le double-submit déjà commité.
    if item_id in _seen_item_ids(s, session.id):
        raise AlreadyAnswered(str(item_id))
    # Session terminée → refus AVANT tout effet (revue 2026-07-08) : sans cette garde,
    # un client pouvait POSTer des réponses après l'arrêt et bouger l'Elo hors flux.
    if session.status != "active":
        raise SessionCompleted(str(session.id))
    # Photo AVANT : prise ici, la seule fenêtre où l'ancienne estimation existe encore.
    item = s.get(Item, item_id)
    comp_id = item.competency_id if item is not None else None
    mastery_before = _mastery_snapshot(s, session.student_id, comp_id) if comp_id else None
    # response_id déterministe : le rejeu du même (session, item) produit le même id
    # → le moteur le reconnaît et ne réapplique RIEN (plus de uuid4 neuf à chaque appel).
    response_id = uuid.uuid5(RESPONSE_ID_NAMESPACE, f"{session.id}:{item_id}")
    def _apply():
        return on_response(
            s, student_id=session.student_id, item_id=item_id, is_correct=is_correct,
            school_id=session.school_id, session_id=session.id,
            response_time_ms=response_time_ms, response_id=response_id,
            language=session.locale,   # C-0 : la Response porte la langue de SA session
        )

    try:
        resp = _apply()
    except IntegrityError:
        # on_response a déjà fait le rollback complet. DEUX causes distinctes
        # (revue adversariale 2026-07-07) — les confondre perdait des réponses :
        #   1. double-submit : la PK du response_id déterministe / la contrainte unique
        #      (session_id, item_id) a rejeté le doublon → la Response EXISTE déjà
        #      (commitée par la transaction gagnante) → même contrat que la garde : 409 ;
        #   2. création CONCURRENTE d'une ligne ability manquante (PK composite
        #      student/competency, cf. engine/service.py) : la Response n'a PAS été
        #      enregistrée — un 409 la perdrait silencieusement. La transaction adverse
        #      a commité la ligne → on REJOUE une fois (le SELECT FOR UPDATE verrouille
        #      désormais la ligne existante).
        if s.get(Response, response_id) is not None:
            raise AlreadyAnswered(str(item_id))
        try:
            resp = _apply()
        except IntegrityError:
            # Le rejeu perd à son tour : si la Response existe maintenant, c'est un
            # vrai double-submit (409) ; sinon on laisse remonter (500 honnête,
            # le client peut rejouer) plutôt que de prétendre à un doublon.
            if s.get(Response, response_id) is not None:
                raise AlreadyAnswered(str(item_id))
            raise
    # Rejeu passé SOUS la garde (course) : on_response a reconnu le response_id existant
    # et n'a RIEN réappliqué (attribut transitoire `replayed`, cf. engine/service.py).
    # Sans ce test, on ré-émettait une 2e entrée AuditLog 'response.submit' et on
    # répondait 200 — alors que le même rejeu plus tard donne 409 (sémantique de replay
    # non déterministe, revue 2026-07-08) → 409 uniforme, zéro audit dupliqué.
    if getattr(resp, "replayed", False):
        raise AlreadyAnswered(str(item_id))
    log_action(s, action="response.submit", school_id=session.school_id, resource_type="response",
               resource_id=resp.id, details={"student_id": str(session.student_id),
                                             "item_id": str(item_id), "correct": is_correct})
    s.commit()

    result = next_item(s, session, config)
    # Le « avant/après » de la compétence qui vient d'être mesurée. C'est CE bloc que
    # l'élève (et l'interlocuteur d'une démo) voit bouger à chaque réponse : sans lui,
    # l'API ne renvoyait qu'une correction binaire, et l'adaptativité restait invisible.
    if comp_id is not None and mastery_before is not None:
        comp = s.get(Competency, comp_id)
        after = _mastery_snapshot(s, session.student_id, comp_id)
        result["mastery"] = {
            "competency_id": str(comp_id),
            "label_en": comp.label_en if comp else None,
            "label_ar": comp.label_ar if comp else None,
            "before": mastery_before,
            "after": after,
            "delta_elo": round(after["elo"] - mastery_before["elo"], 1),
            # Franchissement du seuil PAR L'ESTIMATION, vers le haut. On compare les Elo,
            # pas le drapeau `mastered` : celui-ci exige aussi n_direct > 0, si bien qu'à
            # la toute première mesure d'une compétence il passait de False à True — même
            # sur une réponse FAUSSE et un Elo en baisse. On annonçait un franchissement
            # là où l'élève venait de reculer.
            "crossed_mastery": (mastery_before["elo"] < MASTERY_ELO <= after["elo"]),
        }
    return result
