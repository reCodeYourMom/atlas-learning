"""Génération de la version arabe d'un item (T2.4).

La machine PROPOSE la traduction (modèle arabe natif ALLaM par défaut),
le linguiste humain VALIDE (gate `ar_validated`, voir review.py).

Modèle par défaut : `allam-2-7b` (ALLaM, SDAIA) — arabe natif, aligné GCC.
Client injectable → swappable (Jais/Fanar) sans toucher au pipeline.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import ValidationError

from src.llm.client import LLMClient
from src.models.base import AnswerFormat
from src.models.item import ItemContent

ALLAM_MODEL = "allam-2-7b"


class TranslationError(Exception):
    """Sortie de traduction inexploitable (JSON invalide ou contenu non conforme)."""


_SYSTEM = (
    "You translate K-12 mathematics test items from English to Modern Standard Arabic (الفصحى). "
    "Keep ALL numbers, fractions and mathematical symbols identical and untranslated. "
    "Translate only the natural-language wording. Preserve the order of options. "
    "Output STRICT JSON only — no prose, no markdown. "
    'Schema: {"stem": string, "options": [string, ...], "answer": string}.'
)


def _build_prompt(content_en: dict) -> str:
    return (
        "Translate this item to Arabic. The `answer` must stay equal to the matching option.\n"
        f"{json.dumps(content_en, ensure_ascii=False)}\n\nReturn JSON only."
    )


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _norm_digits(s: str) -> str:
    return (s or "").translate(_AR_DIGITS)


def ar_math_preserved(content_en: dict, content_ar: Optional[dict]) -> bool:
    """Fidélité math EN↔AR (déterministe) : la réponse et l'ensemble des options
    doivent être IDENTIQUES (chiffres normalisés arabes/latins). Le texte (stem) n'est
    pas comparé — c'est le travail du linguiste. Sert à flaguer les traductions qui
    auraient altéré un nombre, à prioriser pour la revue.
    """
    if not content_ar:
        return False
    if _norm_digits(content_en.get("answer", "")) != _norm_digits(content_ar.get("answer", "")):
        return False
    en_opts = {_norm_digits(o) for o in (content_en.get("options") or [])}
    ar_opts = {_norm_digits(o) for o in (content_ar.get("options") or [])}
    return en_opts == ar_opts


def ar_coverage(session) -> dict:
    """Couverture arabe de la banque d'items — rend la « descente » de l'AR MESURABLE.

    Prérequis de vente KSA (bench, Mouvement 02) : on veut prouver que l'arabe est dans le
    contenu (questions validées par un linguiste), pas seulement dans le chrome. Agrégat
    bank-level (les items ne sont pas scopés école).
    """
    from sqlalchemy import select
    from src.models.base import ItemStatus
    from src.models.item import Item

    items = list(session.execute(select(Item).where(Item.deleted_at.is_(None))).scalars())
    total = len(items)
    with_ar = sum(1 for it in items if it.content_ar)
    validated = sum(1 for it in items if it.ar_validated and it.content_ar)
    active = sum(1 for it in items if it.status == ItemStatus.ACTIVE)
    math_ok = sum(1 for it in items
                  if it.content_ar and ar_math_preserved(it.content_en, it.content_ar))
    return {
        "total_items": total,
        "with_ar": with_ar,
        "ar_validated": validated,
        "active": active,
        "math_preserved": math_ok,
        "pct_validated": round(validated / total, 3) if total else 0.0,
    }


def translate_to_arabic(
    content_en: dict,
    client: LLMClient,
    *,
    answer_format: Optional[AnswerFormat] = None,
    temperature: float = 0.2,
) -> dict:
    """Propose `content_ar` à partir de `content_en`. Valide ItemContent + règle MCQ.

    Ne persiste rien : la sortie part en validation linguiste (review.set_arabic).
    """
    raw = client.complete_json(_SYSTEM, _build_prompt(content_en), temperature=temperature)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise TranslationError(f"JSON invalide : {e}") from e

    try:
        content = ItemContent.model_validate(data)
    except ValidationError as e:
        raise TranslationError(f"Contenu AR non conforme : {e}") from e

    if answer_format == AnswerFormat.MCQ:
        opts = content.options or []
        if len(opts) < 2 or content.answer not in opts:
            raise TranslationError("MCQ AR : `answer` doit faire partie des options.")

    return content.model_dump(exclude_none=True)
