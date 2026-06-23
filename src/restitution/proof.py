"""Surfaces de preuve (Mouvement 03 du bench Alef→Atlas) — l'impact comme interface.

Le bench : « concevoir dès maintenant les surfaces de preuve — gains de maîtrise par cohorte,
avant/après, projection de trajectoire. Un avant/après causal est plus vendeur qu'un % d'examen. »

Atlas est pré-traction par choix : ces surfaces se nourrissent du journal de réponses
(append-only) dès la première cohorte pilote — pas besoin d'attendre. Honnêteté (Brief §2,
« mesuré vs estimé ») : c'est un avant/après PÉRIODE, fenêtre explicite, effectifs annotés —
jamais survendu en essai clinique. Aucune PII élève (agrégats seulement).
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.competency import Competency
from src.models.measurement import Response, StudentCompetencyAbility
from src.restitution.diagnosis import MASTERY_ELO
from src.restitution.scale import DEFAULT_ANCHORS


def _rate(rows: list) -> Optional[float]:
    return round(sum(1 for r in rows if r.is_correct) / len(rows), 3) if rows else None


def proof_surfaces(
    s: Session,
    school_id: uuid.UUID,
    *,
    now: Optional[datetime] = None,
    window_days: int = 30,
    min_n: int = 3,
) -> dict:
    """Preuve d'impact d'un établissement, dérivée du journal de réponses + état Elo courant.

    - cohort : taux de réussite période précédente vs récente (avant/après) ;
    - gains : par compétence, avant→après trié par plus gros gain (le récit d'impact) ;
    - trajectory : distribution de la cohorte par niveau (projection vers le supérieur).
    """
    now = now or datetime.now()
    split = now - timedelta(days=window_days)

    code_of: dict = {}
    label_of: dict = {}
    label_ar_of: dict = {}
    for c in s.execute(select(Competency)).scalars():
        code_of[c.id] = c.code
        label_of[c.id] = c.label_en
        label_ar_of[c.id] = c.label_ar

    responses = list(s.execute(
        select(Response).where(Response.school_id == school_id)
    ).scalars())
    before = [r for r in responses if r.created_at < split]
    after = [r for r in responses if r.created_at >= split]

    by_comp_before: dict = defaultdict(list)
    by_comp_after: dict = defaultdict(list)
    for r in before:
        by_comp_before[r.competency_id].append(r)
    for r in after:
        by_comp_after[r.competency_id].append(r)

    gains: List[dict] = []
    for cid in set(by_comp_before) | set(by_comp_after):
        b, a = by_comp_before[cid], by_comp_after[cid]
        if len(b) < min_n or len(a) < min_n:
            continue  # effectif insuffisant des deux côtés → on n'affiche pas (honnêteté)
        rb, ra = _rate(b), _rate(a)
        gains.append({
            "competency_code": code_of.get(cid, str(cid)),
            "label_en": label_of.get(cid, ""), "label_ar": label_ar_of.get(cid, ""),
            "before": rb, "after": ra, "delta": round((ra or 0) - (rb or 0), 3),
            "n_before": len(b), "n_after": len(a),
        })
    gains.sort(key=lambda g: -g["delta"])

    cohort = {
        "window_days": window_days,
        "before": _rate(before), "after": _rate(after),
        "n_before": len(before), "n_after": len(after),
        "delta": (round((_rate(after) or 0) - (_rate(before) or 0), 3)
                  if before and after else None),
    }

    # Projection de trajectoire : où se situe la cohorte (niveau moyen par élève, mesure directe).
    abilities = list(s.execute(
        select(StudentCompetencyAbility).where(
            StudentCompetencyAbility.school_id == school_id,
            StudentCompetencyAbility.n_direct > 0,
        )
    ).scalars())
    by_student: dict = defaultdict(list)
    for r in abilities:
        by_student[r.student_id].append(r.ability_elo)
    bands: dict = defaultdict(int)
    for elos in by_student.values():
        bands[DEFAULT_ANCHORS.level(sum(elos) / len(elos))] += 1
    order = [a.level for a in DEFAULT_ANCHORS.anchors]
    trajectory = [{"level": lvl, "n_students": bands.get(lvl, 0)} for lvl in order]

    return {
        "school_id": str(school_id),
        "cohort": cohort,
        "gains": gains,
        "trajectory": trajectory,
        "n_students_measured": len(by_student),
        "n_mastered_skills": sum(1 for r in abilities if r.ability_elo >= MASTERY_ELO),
        "n_measured_skills": len(abilities),
    }
