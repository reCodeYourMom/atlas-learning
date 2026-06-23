"""Remédiation ciblée (Epic 5, T5.6).

À partir d'une lacune diagnostiquée (T5.3), produit un exercice ciblé — en servant
d'abord la CAUSE RACINE (prérequis HARD le plus amont). Réutilise le pipeline de
génération T2 : sortie validée `ItemContent`, AUCUNE donnée élève dans le prompt.

Génération APRÈS mesure, jamais pour la mesure.
"""
from __future__ import annotations

from typing import Optional

from src.items.generation import GeneratedItem, generate_items
from src.llm.client import LLMClient
from src.models.base import AnswerFormat
from src.restitution.diagnosis import Diagnosis


def remediation_target_code(diagnosis: Diagnosis) -> str:
    """Code de la compétence à remédier : la cause racine (cohérent avec T5.3)."""
    return diagnosis.root_cause


def generate_remediation(
    target_competency,
    client: LLMClient,
    *,
    context: Optional[dict] = None,
    answer_format: AnswerFormat = AnswerFormat.MCQ,
) -> Optional[GeneratedItem]:
    """Génère un exercice de remédiation pour `target_competency` (souvent la racine).

    `target_competency` : objet compétence (code, label_en, cognitive_level, difficulty_prior).
    Garde-fou PII et validation `ItemContent` hérités de generate_items (T2.2).
    """
    targets = [context or {"purpose": "remediation"}]
    items = generate_items(target_competency, targets, client,
                           answer_format=answer_format, n_per_target=1)
    return items[0] if items else None
