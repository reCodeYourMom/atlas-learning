"""Vues de restitution (Epic 5, T5.4 enseignant + T5.5 admin).

Réutilise le cœur analytique (diagnose_all, aggregate). Logique testable sans HTTP ;
l'autorisation (RBAC) est appliquée dans les endpoints.
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.items.quarantine import active_pool
from src.models.base import EdgeType
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, Student, StudentCompetencyAbility
from src.models.org import Classroom, StudentClassroom
from src.restitution.diagnosis import MASTERY_ELO, diagnose, diagnose_all
from src.restitution.scale import DEFAULT_ANCHORS, restitute
from src.restitution.tutor import explain_diagnosis


def _code_maps(s: Session):
    comps = {c.id: c for c in s.execute(select(Competency)).scalars()}
    code_of = {cid: c.code for cid, c in comps.items()}
    label_of = {c.code: c.label_en for c in comps.values()}
    label_ar_of = {c.code: c.label_ar for c in comps.values()}
    hard: dict = {}
    for e in s.execute(
        select(CompetencyPrerequisite).where(CompetencyPrerequisite.edge_type == EdgeType.HARD)
    ).scalars():
        if e.target_id in code_of and e.source_id in code_of:
            hard.setdefault(code_of[e.target_id], []).append(code_of[e.source_id])
    return code_of, label_of, hard, label_ar_of


def _class_student_ids(s: Session, classroom_id: uuid.UUID) -> set:
    """IDs des élèves vivants d'une classe : inscriptions M:N ∪ classe principale (homeroom)."""
    ids = set(s.execute(
        select(StudentClassroom.student_id).where(StudentClassroom.classroom_id == classroom_id)
    ).scalars())
    ids |= set(s.execute(
        select(Student.id).where(Student.classroom_id == classroom_id)
    ).scalars())
    if not ids:
        return set()
    return set(s.execute(
        select(Student.id).where(Student.id.in_(ids), Student.deleted_at.is_(None))
    ).scalars())


def class_gaps(s: Session, classroom_id: uuid.UUID) -> List[dict]:
    """Lacunes de la classe regroupées par CAUSE RACINE, triées par fréquence (T5.4).

    Chaque entrée porte son diagnostic causal — « où concentrer le cours ».
    """
    code_of, label_of, hard, label_ar_of = _code_maps(s)
    student_ids = _class_student_ids(s, classroom_id)

    counter: Counter = Counter()
    example_gap: dict = {}     # root_cause -> (gap_code, is_self) le plus représentatif
    example_expl: dict = {}
    for sid in student_ids:
        rows = s.execute(
            select(StudentCompetencyAbility).where(StudentCompetencyAbility.student_id == sid)
        ).scalars().all()
        abilities = {code_of[r.competency_id]: r.ability_elo for r in rows if r.competency_id in code_of}
        for d in diagnose_all(abilities, hard):
            counter[d.root_cause] += 1
            example_gap.setdefault(d.root_cause, (d.gap, d.is_self))
            example_expl.setdefault(d.root_cause, d.explanation)

    out = []
    for rc, n in counter.most_common():
        gap_code, is_self = example_gap[rc]
        out.append({
            "root_cause": rc,
            "label": label_of.get(rc, rc),                  # rétro-compat
            "root_cause_label_en": label_of.get(rc, rc),
            "root_cause_label_ar": label_ar_of.get(rc, rc),
            "gap_label_en": label_of.get(gap_code, gap_code),
            "gap_label_ar": label_ar_of.get(gap_code, gap_code),
            "is_self": is_self,
            "student_count": n,
            "diagnosis": example_expl[rc],
        })
    return out


def class_digest(s: Session, classroom_id: uuid.UUID, *, days: int = 7,
                 now: Optional[datetime] = None) -> dict:
    """Digest hebdomadaire enseignant — conçu pour SA cadence (Brief : persona de rétention).

    Pas une boucle quotidienne d'élève (refusée) : l'habitude qui compte est celle de
    l'enseignant qui ouvre sa vue classe chaque semaine. Donne l'activité de la semaine,
    les lacunes ÉMERGENTES (re)mesurées dans la fenêtre, et la priorité #1 où agir.
    """
    now = now or datetime.now()
    since = now - timedelta(days=days)
    code_of, label_of, hard, label_ar_of = _code_maps(s)
    student_ids = _class_student_ids(s, classroom_id)

    # Activité de la semaine.
    responses = list(s.execute(
        select(Response).where(Response.student_id.in_(student_ids),
                               Response.created_at >= since)
    ).scalars()) if student_ids else []
    active_students = {r.student_id for r in responses}

    # Lacunes émergentes : diagnostic dont la lacune (ou sa racine) a été (re)mesurée cette semaine.
    emerging: Counter = Counter()
    emerging_example: dict = {}
    for sid in student_ids:
        rows = s.execute(
            select(StudentCompetencyAbility).where(
                StudentCompetencyAbility.student_id == sid,
                StudentCompetencyAbility.n_direct > 0,
            )
        ).scalars().all()
        abilities = {code_of[r.competency_id]: r.ability_elo for r in rows if r.competency_id in code_of}
        recent = {code_of[r.competency_id] for r in rows
                  if r.competency_id in code_of and r.last_measured_at and r.last_measured_at >= since}
        if not recent:
            continue
        # Une cause racine compte UNE fois par élève (plusieurs lacunes peuvent y remonter).
        seen_roots: dict = {}
        for d in diagnose_all(abilities, hard):
            if d.gap in recent or d.root_cause in recent:
                seen_roots.setdefault(d.root_cause, (d.gap, d.is_self))
        for rc, (gap_code, is_self) in seen_roots.items():
            emerging[rc] += 1
            emerging_example.setdefault(rc, (gap_code, is_self))

    emerging_gaps = []
    for rc, n in emerging.most_common(5):
        gap_code, is_self = emerging_example[rc]
        emerging_gaps.append({
            "root_cause": rc,
            "root_cause_label_en": label_of.get(rc, rc),
            "root_cause_label_ar": label_ar_of.get(rc, rc),
            "gap_label_en": label_of.get(gap_code, gap_code),
            "gap_label_ar": label_ar_of.get(gap_code, gap_code),
            "is_self": is_self,
            "student_count": n,
        })

    all_gaps = class_gaps(s, classroom_id)
    return {
        "classroom_id": str(classroom_id),
        "window_days": days,
        "since": since.isoformat(),
        "n_students": len(student_ids),
        "n_active_students": len(active_students),
        "n_responses": len(responses),
        "emerging_gaps": emerging_gaps,
        "top_priority": all_gaps[0] if all_gaps else None,
    }


def school_overview(s: Session, school_id: uuid.UUID) -> dict:
    """Agrégat établissement (T5.5) : maîtrise par compétence et par classe. SANS PII élève."""
    code_of, label_of, _, _ = _code_maps(s)
    students = s.execute(
        select(Student).where(Student.school_id == school_id, Student.deleted_at.is_(None))
    ).scalars().all()
    # Appartenance M:N : un élève peut compter dans plusieurs classes (spécialités).
    student_ids = [st.id for st in students]
    classes_of: dict = {}
    if student_ids:
        for sid, cid in s.execute(
            select(StudentClassroom.student_id, StudentClassroom.classroom_id)
            .where(StudentClassroom.student_id.in_(student_ids))
        ).all():
            classes_of.setdefault(sid, set()).add(cid)
    for st in students:
        if st.classroom_id:
            classes_of.setdefault(st.id, set()).add(st.classroom_id)

    rows = [r for r in s.execute(
        select(StudentCompetencyAbility).where(StudentCompetencyAbility.school_id == school_id)
    ).scalars() if r.n_direct > 0]  # mesures directes seulement

    by_comp: dict = {}
    for r in rows:
        by_comp.setdefault(r.competency_id, []).append(r.ability_elo)
    competencies = [
        {"code": code_of.get(cid, str(cid)), "label": label_of.get(code_of.get(cid), ""),
         "mean_ability": round(mean(v), 1),
         "mastery_rate": round(sum(1 for x in v if x >= MASTERY_ELO) / len(v), 2),
         "n_measured": len(v)}
        for cid, v in by_comp.items()
    ]
    competencies.sort(key=lambda c: c["mastery_rate"])  # les plus faibles d'abord

    classes = []
    for cls in s.execute(
        select(Classroom).where(Classroom.school_id == school_id, Classroom.deleted_at.is_(None))
    ).scalars():
        vals = [r.ability_elo for r in rows if cls.id in classes_of.get(r.student_id, ())]
        classes.append({
            "classroom_id": str(cls.id), "name": cls.name,
            "n_students": sum(1 for st in students if cls.id in classes_of.get(st.id, ())),
            "mean_ability": round(mean(vals), 1) if vals else None,
        })

    return {"school_id": str(school_id), "n_students": len(students),
            "competencies": competencies, "classes": classes}


# ---------------------------------------------------------------------------
# T5.x — vues UI complémentaires (fiche élève, trajectoire parent, listings)
# Wrappers minces sur le cœur analytique (diagnose / restitute / aggregate).
# ---------------------------------------------------------------------------

def _competency_meta(s: Session) -> dict:
    """code -> {label_en, label_ar, grade, strand}."""
    out = {}
    for c in s.execute(select(Competency)).scalars():
        out[c.code] = {
            "label_en": c.label_en, "label_ar": c.label_ar,
            "grade": c.grade, "strand": ".".join(c.code.split(".")[:3]),
        }
    return out


def list_students(s: Session, classroom_id: uuid.UUID) -> List[dict]:
    """Élèves d'une classe (sans PII inutile : ref externe seulement)."""
    ids = _class_student_ids(s, classroom_id)
    rows = s.execute(select(Student).where(Student.id.in_(ids))).scalars().all() if ids else []
    out = []
    for st in rows:
        abilities = s.execute(
            select(StudentCompetencyAbility).where(
                StudentCompetencyAbility.student_id == st.id,
                StudentCompetencyAbility.n_direct > 0,
            )
        ).scalars().all()
        measured = [a for a in abilities]
        mean_elo = round(mean([a.ability_elo for a in measured]), 1) if measured else None
        n_gaps = sum(1 for a in measured if a.ability_elo < MASTERY_ELO)
        out.append({
            "student_id": str(st.id), "external_ref": st.external_ref or "—",
            "mean_ability": mean_elo, "n_measured": len(measured), "n_gaps": n_gaps,
        })
    out.sort(key=lambda x: (x["mean_ability"] is None, x["mean_ability"] or 0))
    return out


def student_profile(s: Session, student_id: uuid.UUID) -> dict:
    """Fiche élève (écran héros) : profil de maîtrise + diagnostic causal + restitution."""
    code_of, label_of, hard_codes, label_ar_of = _code_maps(s)
    meta = _competency_meta(s)
    rows = s.execute(
        select(StudentCompetencyAbility).where(StudentCompetencyAbility.student_id == student_id)
    ).scalars().all()

    abilities_by_code = {code_of[r.competency_id]: r.ability_elo
                         for r in rows if r.competency_id in code_of}

    competencies = []
    for r in rows:
        code = code_of.get(r.competency_id)
        if code is None:
            continue
        m = meta.get(code, {})
        competencies.append({
            "code": code, "label_en": m.get("label_en", code), "label_ar": m.get("label_ar", code),
            "grade": m.get("grade"), "strand": m.get("strand", code),
            "ability_elo": round(r.ability_elo, 1), "confidence": round(r.confidence, 3),
            "n_direct": r.n_direct, "measured": r.n_direct > 0,
            "mastered": r.ability_elo >= MASTERY_ELO,
        })
    competencies.sort(key=lambda c: (c["grade"] or 0, c["ability_elo"]))

    # Diagnostics causaux sur les lacunes mesurées
    diagnoses = []
    for d in diagnose_all(abilities_by_code, hard_codes):
        diagnoses.append({
            "gap": d.gap,
            "gap_label": label_of.get(d.gap, d.gap),
            "gap_label_ar": label_ar_of.get(d.gap, d.gap),
            "root_cause": d.root_cause,
            "root_cause_label": label_of.get(d.root_cause, d.root_cause),
            "root_cause_label_ar": label_ar_of.get(d.root_cause, d.root_cause),
            "is_self": d.is_self, "chain": d.chain,
            "chain_labels": [label_of.get(c, c) for c in d.chain],
            "chain_labels_ar": [label_ar_of.get(c, c) for c in d.chain],
            "explanation": d.explanation,
        })
    diagnoses.sort(key=lambda d: (d["is_self"], len(d["chain"])), reverse=True)

    restitution = _overall_restitution(rows)
    st = s.get(Student, student_id)
    return {
        "student_id": str(student_id),
        "external_ref": (st.external_ref if st and st.external_ref else "—"),
        "restitution": restitution,
        "competencies": competencies,
        "diagnoses": diagnoses,
        "n_measured": sum(1 for c in competencies if c["measured"]),
        "n_gaps": len(diagnoses),
    }


def _overall_restitution(rows: List[StudentCompetencyAbility]) -> dict:
    """Restitution globale (percentile/niveau/fourchette) pondérée par la confiance."""
    measured = [r for r in rows if r.n_direct > 0]
    pool = measured or list(rows)
    if not pool:
        return {"ability": None, "confidence": 0.0, "percentile": None,
                "level": None, "is_range": True, "percentile_range": None, "measured": False}
    total_w = sum(r.confidence for r in pool)
    if total_w > 0:
        ability = sum(r.ability_elo * r.confidence for r in pool) / total_w
    else:
        ability = sum(r.ability_elo for r in pool) / len(pool)
    confidence = sum(r.confidence for r in pool) / len(pool)
    rest = restitute(ability, confidence, DEFAULT_ANCHORS)
    return {
        "ability": round(ability, 1), "confidence": round(confidence, 3),
        "percentile": rest.percentile, "level": rest.level,
        "is_range": rest.is_range, "percentile_range": list(rest.percentile_range) if rest.percentile_range else None,
        "measured": bool(measured),
    }


def student_trajectory(s: Session, student_id: uuid.UUID) -> dict:
    """Vue parent (lecture seule) : trajectoire vers le supérieur, lacunes en comblement."""
    profile = student_profile(s, student_id)
    rest = profile["restitution"]
    # Lacunes « en cours de comblement » = mesurées, non maîtrisées, présentées positivement.
    closing = [
        {"label_en": c["label_en"], "label_ar": c["label_ar"],
         "ability_elo": c["ability_elo"], "confidence": c["confidence"],
         "progress": _progress_pct(c["ability_elo"])}
        for c in profile["competencies"] if c["measured"] and not c["mastered"]
    ]
    mastered = [
        {"label_en": c["label_en"], "label_ar": c["label_ar"]}
        for c in profile["competencies"] if c["measured"] and c["mastered"]
    ]
    return {
        "student_id": str(student_id), "restitution": rest,
        "n_mastered": len(mastered), "mastered": mastered,
        "closing_gaps": sorted(closing, key=lambda x: -x["progress"]),
        "next_step": _parent_next_step(s, profile["diagnoses"]),
    }


def _parent_next_step(s: Session, diagnoses: List[dict]) -> Optional[dict]:
    """« Prochaine étape » côté parent : la lacune prioritaire + une activité maison ~10 min.

    Le brief fait du parent un bénéficiaire qu'on rassure : on ne montre pas « 24 % en échec »
    mais UNE chose concrète à faire à la maison, ciblée sur la cause racine. Bilingue, sans PII,
    sans la réponse de l'exercice (l'enfant la cherche).
    """
    if not diagnoses:
        return None
    top = diagnoses[0]  # déjà trié par priorité (is_self, longueur de chaîne) dans student_profile
    return {
        "competency_code": top["root_cause"],
        "skill_label_en": top["root_cause_label"],
        "skill_label_ar": top["root_cause_label_ar"],
        "is_self": top["is_self"],
        "gap_label_en": top["gap_label"],
        "gap_label_ar": top["gap_label_ar"],
        "minutes": 10,
        "activity": _home_activity(s, top["root_cause"]),
    }


def _home_activity(s: Session, competency_code: str) -> Optional[dict]:
    """Un exercice validé de la banque (sans la réponse), présenté pour un parent, bilingue."""
    comp = s.execute(
        select(Competency).where(Competency.code == competency_code)
    ).scalar_one_or_none()
    if comp is None:
        return None
    items = [it for it in active_pool(s) if it.competency_id == comp.id]
    if not items:
        return None
    it = items[0]
    return {
        "item_id": str(it.id),
        "answer_format": it.answer_format.value,
        "example_en": (it.content_en or {}).get("stem"),
        "example_ar": (it.content_ar or {}).get("stem") if it.content_ar else None,
    }


def _progress_pct(ability_elo: float) -> int:
    """Position 0..100 d'une ability sur l'échelle d'ancrage (pour une jauge lisible parent)."""
    return int(max(0.0, min(100.0, DEFAULT_ANCHORS.percentile(ability_elo))))


def tutor_explanation(s: Session, student_id: uuid.UUID, gap_code: str) -> dict:
    """Tuteur causal (Mouvement 04) : « pourquoi cet exercice ? » pour la lacune `gap_code`.

    Déterministe, sans PII dans la sortie (seulement des libellés de compétences).
    """
    code_of, label_of, hard, label_ar_of = _code_maps(s)
    rows = s.execute(
        select(StudentCompetencyAbility).where(StudentCompetencyAbility.student_id == student_id)
    ).scalars().all()
    abilities = {code_of[r.competency_id]: r.ability_elo for r in rows if r.competency_id in code_of}
    if gap_code not in abilities or abilities[gap_code] >= MASTERY_ELO:
        # rien à expliquer : compétence non mesurée, inconnue, ou déjà maîtrisée
        return {"available": False, "competency_code": gap_code}
    d = diagnose(gap_code, abilities, hard)
    return {"available": True, **explain_diagnosis(d, label_of, label_ar_of)}


def referentiel_graph(s: Session) -> dict:
    """Graphe de compétences (nœuds + arêtes typées) — pour la viz du diagnostic causal."""
    nodes, edges = [], []
    for c in s.execute(select(Competency)).scalars():
        nodes.append({"code": c.code, "label_en": c.label_en, "label_ar": c.label_ar,
                      "grade": c.grade, "strand": ".".join(c.code.split(".")[:3])})
    code_of = {c.id: c.code for c in s.execute(select(Competency)).scalars()}
    for e in s.execute(select(CompetencyPrerequisite)).scalars():
        if e.source_id in code_of and e.target_id in code_of:
            edges.append({"source": code_of[e.source_id], "target": code_of[e.target_id],
                          "type": e.edge_type.value, "strength": round(e.correlation_strength, 2)})
    return {"nodes": nodes, "edges": edges}


def remediation_preview(s: Session, competency_code: str, lang: str = "en") -> dict:
    """Exercice de remédiation : sert un item actif de la compétence ciblée (cause racine).

    Pas d'appel LLM ni de donnée élève : on puise dans la banque déjà validée.
    """
    comp = s.execute(select(Competency).where(Competency.code == competency_code)).scalar_one_or_none()
    if comp is None:
        return {"available": False, "competency_code": competency_code}
    items = [it for it in active_pool(s) if it.competency_id == comp.id]
    if not items:
        return {"available": False, "competency_code": competency_code,
                "competency_label_en": comp.label_en, "competency_label_ar": comp.label_ar}
    it = items[0]
    content = it.content_ar if (lang == "ar" and it.content_ar) else it.content_en
    public = {k: v for k, v in (content or {}).items() if k != "answer"}
    return {
        "available": True, "competency_code": competency_code,
        "competency_label_en": comp.label_en, "competency_label_ar": comp.label_ar,
        "item_id": str(it.id), "answer_format": it.answer_format.value,
        "content": public,
    }
