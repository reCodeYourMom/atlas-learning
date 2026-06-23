"""Tables de mesure (Epic 3, DataModel §5).

School/Student : socle tenant minimal (RBAC complet = Epic 6).
Response : événement brut, APPEND-ONLY.
StudentCompetencyAbility : état Elo par élève × compétence (direct + propagé).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class School(Base):
    __tablename__ = "school"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), default=None, index=True
    )
    external_ref: Mapped[Optional[str]] = mapped_column(String, index=True, default=None)  # orgUnit id
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Student(Base):
    __tablename__ = "student"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), index=True
    )
    # Classe principale (homeroom). L'ensemble des inscriptions vit dans student_classroom
    # (M:N) — un élève peut suivre des classes de spécialité en plus de sa classe principale.
    classroom_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("classroom.id", ondelete="SET NULL"), default=None, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL"), default=None, index=True
    )
    external_ref: Mapped[Optional[str]] = mapped_column(String, default=None)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Response(Base):
    """Événement de réponse — append-only (ni update, ni delete)."""
    __tablename__ = "response"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item.id", ondelete="RESTRICT"), index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(index=True)  # dénormalisé (query rapide)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(default=None)  # FK session = Epic 4
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class StudentCompetencyAbility(Base, TimestampMixin):
    __tablename__ = "student_competency_ability"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student.id", ondelete="CASCADE"), primary_key=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), index=True
    )

    ability_elo: Mapped[float] = mapped_column(Float)
    n_direct: Mapped[int] = mapped_column(Integer, default=0)       # réponses DIRECTES
    confidence: Mapped[float] = mapped_column(Float, default=0.0)   # [0..1]
    last_measured_at: Mapped[Optional[datetime]] = mapped_column(default=None)
