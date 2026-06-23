"""Journal d'audit (must-have V1 sécu, PRD). Accès & actions auditables.

APPEND-ONLY : ni update, ni delete. Porte school_id pour la traçabilité tenant.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(default=None, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(default=None, index=True)
    action: Mapped[str] = mapped_column(String, index=True)        # ex. "session.create", "classroom.view_gaps"
    resource_type: Mapped[Optional[str]] = mapped_column(String, default=None)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(default=None)
    details: Mapped[dict] = mapped_column(JSON, default=dict)      # contexte non-PII
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
