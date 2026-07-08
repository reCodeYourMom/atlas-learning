"""Jetons de lien magique consommés (anti-rejeu, revue sécurité 2026-07-07).

Un lien magique (parent / super-admin) porte un `jti` aléatoire signé. À la connexion,
le `jti` est INSÉRÉ ici : la clé primaire arbitre la course — le second usage lève
IntegrityError → 401. `expires_at` permet de purger les lignes devenues inutiles
(un jeton expiré est déjà rejeté par la signature/expiration, cf. rbac/auth.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class ConsumedToken(Base):
    __tablename__ = "consumed_token"

    jti: Mapped[str] = mapped_column(String, primary_key=True)   # unicité = consommation atomique
    purpose: Mapped[str] = mapped_column(String)                 # parent_login | admin_login
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)  # purge des jti expirés
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
