"""Modèle Item (T2.1) — 1 item mesure UNE seule compétence.

Règle stricte (data model §4) : un item multi-compétences pollue le signal Elo.
Le contenu (content_en / content_ar) est du JSONB validé par Pydantic à l'écriture.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from .base import (
    AnswerFormat,
    Base,
    ItemStatus,
    TimestampMixin,
    native_enum,
    uuid_pk,
)

# JSONB sur Postgres (prod), JSON sur SQLite (dev/CI) — même API côté Python.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class ItemContent(BaseModel):
    """Forme validée du contenu d'un item. Champs métier requis : stem + answer.

    `extra="allow"` : tolère des clés additionnelles (ex. `format`) sans les perdre.
    """
    model_config = ConfigDict(extra="allow")

    stem: str
    options: Optional[List[str]] = None  # pour MCQ
    answer: str


def _default_elo(context) -> float:  # noqa: ANN001
    """difficulty_elo = difficulty_prior à la création si non fourni (AC3)."""
    return context.get_current_parameters()["difficulty_prior"]


class Item(Base, TimestampMixin):
    __tablename__ = "item"

    id: Mapped[uuid.UUID] = uuid_pk()
    competency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="RESTRICT"), index=True
    )  # RESTRICT : interdit de supprimer une compétence qui a des items vivants

    content_en: Mapped[dict] = mapped_column(JSONType)
    # content_ar reste vide jusqu'à la traduction T2.4 (revue EN d'abord, T2.3).
    content_ar: Mapped[Optional[dict]] = mapped_column(JSONType, default=None)
    answer_format: Mapped[AnswerFormat] = mapped_column(
        native_enum(AnswerFormat, "answer_format")
    )

    difficulty_prior: Mapped[float] = mapped_column()
    difficulty_elo: Mapped[float] = mapped_column(default=_default_elo)
    n_responses: Mapped[int] = mapped_column(default=0)

    context_tags: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[ItemStatus] = mapped_column(
        native_enum(ItemStatus, "item_status"), default=ItemStatus.AI_GENERATED
    )
    provenance: Mapped[dict] = mapped_column(JSONType, default=dict)
    ar_validated: Mapped[bool] = mapped_column(default=False)

    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    @validates("content_en", "content_ar")
    def _validate_content(self, key: str, value):
        # content_ar peut être None/vide tant que la traduction T2.4 n'est pas faite.
        if key == "content_ar" and not value:
            return value
        # contenu non conforme à ItemContent → rejet (pydantic.ValidationError)
        ItemContent.model_validate(value)
        return value

    def __repr__(self) -> str:
        return f"<Item {self.id} comp={self.competency_id} {self.answer_format}>"
