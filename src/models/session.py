"""Session d'évaluation (Epic 4). Lie un élève à une suite de réponses adaptatives."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow, uuid_pk


class AssessmentSession(Base):
    __tablename__ = "assessment_session"

    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String, default="active")  # active | completed
    target_competency_ids: Mapped[Optional[list]] = mapped_column(JSON, default=None)
    stop_reason: Mapped[Optional[str]] = mapped_column(String, default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
