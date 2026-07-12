"""Modèles du crosswalk curriculaire (Lot B, B2 — DataModel §7 amendé D-B4).

CurriculumStandard : standard officiel d'un framework externe (CCSS-M, UK NC, MoE UAE).
CompetencyCurriculumMap : alignement compétence Atlas ↔ standard — type + confiance
(pas de force scalaire), même pattern de provenance que CompetencyPrerequisite.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import (
    AlignmentType,
    Base,
    CurriculumFramework,
    MappingConfidence,
    WeightSource,
    native_enum,
    uuid_pk,
)


class CurriculumStandard(Base):
    __tablename__ = "curriculum_standard"
    __table_args__ = (
        # `code` n'est unique QUE par framework ('Y5' UK vs un éventuel 'Y5' ailleurs).
        # MoE UAE n'a pas de codes officiels : `code` y est la clé composée
        # domaine+grade-band (ex. 'NUM_OPS/G4-G5') — jamais un pseudo-code inventé.
        UniqueConstraint("framework", "code", name="uq_curriculum_standard_framework_code"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    framework: Mapped[CurriculumFramework] = mapped_column(
        native_enum(CurriculumFramework, "curriculum_framework")
    )
    code: Mapped[str] = mapped_column(String)   # '4.NF.A.1' | 'Y5' | 'NUM_OPS/G4-G5'
    label_en: Mapped[str] = mapped_column(String)
    label_ar: Mapped[str] = mapped_column(String)
    grade_hint: Mapped[Optional[str]] = mapped_column(String, default=None)  # affichage ('G4', 'Y5', 'G4-G5')

    def __repr__(self) -> str:  # aide au debug, pas de magie
        return f"<CurriculumStandard {self.framework.value}:{self.code}>"


class CompetencyCurriculumMap(Base):
    __tablename__ = "competency_curriculum_map"

    competency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_standard.id", ondelete="CASCADE"), primary_key=True
    )

    alignment_type: Mapped[AlignmentType] = mapped_column(
        native_enum(AlignmentType, "alignment_type")
    )
    confidence: Mapped[MappingConfidence] = mapped_column(
        native_enum(MappingConfidence, "mapping_confidence")
    )
    note: Mapped[Optional[str]] = mapped_column(String, default=None)

    # même provenance versionnée que les arêtes du graphe (expert aujourd'hui,
    # empirique après calibration) — cf. CompetencyPrerequisite
    weight_source: Mapped[WeightSource] = mapped_column(
        native_enum(WeightSource, "weight_source"), default=WeightSource.EXPERT
    )
    weight_version: Mapped[int] = mapped_column(default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Map {self.competency_id}->{self.standard_id} {self.alignment_type}>"
