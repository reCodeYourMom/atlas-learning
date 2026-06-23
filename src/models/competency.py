"""Modèles du référentiel : Competency (nœud) et CompetencyPrerequisite (arête).

T1.1 — modèles seulement. Pas de moteur, pas d'API.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import (
    Base,
    CognitiveLevel,
    CompetencyStatus,
    EdgeType,
    Subject,
    TimestampMixin,
    WeightSource,
    native_enum,
    uuid_pk,
)


class Competency(Base, TimestampMixin):
    __tablename__ = "competency"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(unique=True, index=True)
    # ex. MATH.G4.NF.ADD_UNLIKE_LCM — identifiant stable, lisible, versionnable

    label_en: Mapped[str] = mapped_column()
    label_ar: Mapped[str] = mapped_column()
    description: Mapped[Optional[str]] = mapped_column(default=None)

    subject: Mapped[Subject] = mapped_column(native_enum(Subject, "subject"))
    grade: Mapped[int] = mapped_column(index=True)
    cognitive_level: Mapped[Optional[CognitiveLevel]] = mapped_column(
        native_enum(CognitiveLevel, "cognitive_level"), default=None
    )

    difficulty_prior: Mapped[float] = mapped_column()
    status: Mapped[CompetencyStatus] = mapped_column(
        native_enum(CompetencyStatus, "competency_status"),
        default=CompetencyStatus.DRAFT,
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    def __repr__(self) -> str:  # aide au debug, pas de magie
        return f"<Competency {self.code} G{self.grade}>"


class CompetencyPrerequisite(Base):
    __tablename__ = "competency_prerequisite"
    __table_args__ = (
        # garde-fou DB minimal : pas d'auto-référence (le validateur DAG applicatif fait le reste)
        CheckConstraint("source_id <> target_id", name="ck_no_self_loop"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True
    )  # le prérequis
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True
    )  # le dépendant

    edge_type: Mapped[EdgeType] = mapped_column(native_enum(EdgeType, "edge_type"))
    correlation_strength: Mapped[float] = mapped_column()  # [0..1], poids de propagation

    weight_source: Mapped[WeightSource] = mapped_column(
        native_enum(WeightSource, "weight_source"), default=WeightSource.EXPERT
    )
    weight_version: Mapped[int] = mapped_column(default=1)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Edge {self.source_id}->{self.target_id} {self.edge_type}>"
