"""Helper de journalisation d'audit (must-have V1 sécu).

`log_action` ajoute une entrée APPEND-ONLY à la session courante (le commit appartient
à l'appelant → l'audit s'inscrit dans la même transaction que l'action auditée).
Ne journalise JAMAIS de PII (énoncés, réponses élève) — seulement qui/quoi/quand.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from src.models.audit import AuditLog
from src.models.base import utcnow


def log_action(
    session: Session,
    *,
    action: str,
    school_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    entry = AuditLog(
        action=action, school_id=school_id, user_id=user_id,
        resource_type=resource_type, resource_id=resource_id,
        details=details or {}, created_at=utcnow(),
    )
    session.add(entry)
    return entry
