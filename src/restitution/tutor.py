"""Tuteur causal interrogeable (Mouvement 04 du bench Alef→Atlas) — incarner le moteur.

Le bench : l'IA d'Atlas est « brillante mais muette : elle classe sans dialoguer ». Ici elle
EXPLIQUE « pourquoi cet exercice » et « cette étape », en s'appuyant sur le diagnostic
cause-racine — le moat d'Atlas, pas un chatbot générique.

Garde-fous (Brief sécurité, déjà spécifiés ; le bench les transforme en argument de gouvernance
IA face au régulateur GCC) :
  - sortie STRUCTURÉE et DÉTERMINISTE, construite à partir du graphe de compétences validé ;
  - AUCUNE donnée élève (PII) — on ne reçoit que des libellés de compétences ;
  - AUCUN appel LLM → zéro hallucination sur un mineur, rien à faire valider après coup.
"""
from __future__ import annotations

from typing import Dict, List

from src.restitution.diagnosis import Diagnosis


def explain_diagnosis(d: Diagnosis, label_en: Dict[str, str], label_ar: Dict[str, str]) -> dict:
    """Transforme un diagnostic causal en explication bilingue « pourquoi je travaille ça ».

    `d.chain` = [gap, …, root_cause]. On la lit racine → lacune : chaque maillon amont
    « débloque » le suivant. Sortie structurée (titre + étapes), prête à afficher.
    """
    le = lambda c: label_en.get(c, c)  # noqa: E731
    la = lambda c: label_ar.get(c, c)  # noqa: E731
    gap, root = d.gap, d.root_cause

    if d.is_self:
        return {
            "competency_code": gap,
            "is_self": True,
            "headline_en": f"We're working on “{le(gap)}” directly — nothing else is in the way.",
            "headline_ar": f"نعمل على «{la(gap)}» مباشرةً — لا شيء آخر يعيقك.",
            "steps": [],
            "why_en": "This skill has no missing building block beneath it, so practising it "
                      "head-on is the fastest way forward.",
            "why_ar": "هذه المهارة لا ينقصها أساس تحتها، لذا التدرّب عليها مباشرةً أسرع طريق للتقدّم.",
        }

    # racine → lacune (on inverse la chaîne qui part de la lacune)
    ordered = list(reversed(d.chain))  # [root, …, gap]
    steps: List[dict] = []
    for upstream, downstream in zip(ordered, ordered[1:]):
        steps.append({
            "from_code": upstream, "to_code": downstream,
            "reason_en": f"Getting solid on “{le(upstream)}” is what lets you tackle “{le(downstream)}”.",
            "reason_ar": f"إتقان «{la(upstream)}» هو ما يتيح لك معالجة «{la(downstream)}».",
        })

    return {
        "competency_code": gap,
        "is_self": False,
        "headline_en": f"We start with “{le(root)}” because it's the real reason “{le(gap)}” feels hard.",
        "headline_ar": f"نبدأ بـ«{la(root)}» لأنّها السبب الحقيقي وراء صعوبة «{la(gap)}».",
        "steps": steps,
        "why_en": f"Fix the root first and the rest of the chain up to “{le(gap)}” gets easier — "
                  "we measure to help you, not to score you.",
        "why_ar": f"عالِج الجذر أولًا، وستسهُل بقية السلسلة حتى «{la(gap)}» — نحن نقيس لنساعدك، لا لنضع لك درجة.",
    }
