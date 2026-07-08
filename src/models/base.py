"""Base SQLAlchemy 2.0 + enums du référentiel Atlas Learning.

Conventions projet :
- UUID en PK
- timestamptz (created_at / updated_at)
- enums Postgres natifs
- soft delete via deleted_at

Convention temporelle (revue 2026-07-07 — intégrité d'audit / résidence UAE) :
- TOUT timestamp est produit par `utcnow()` (aware, UTC) — jamais `datetime.now()`
  naïf (heure locale du serveur : ambigu, non auditable) ;
- TOUTE colonne timestamp est `DateTime(timezone=True)` (timestamptz sur Postgres) ;
- SQLite (dev/CI) ne stocke pas l'offset et RESTITUE des datetimes NAÏFS même sur
  colonne tz-aware : un naïf relu de la base est PAR CONVENTION de l'UTC. Toute
  comparaison/soustraction avec un datetime aware passe par `ensure_utc()` —
  sinon TypeError (mélange naïf/aware).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """« Maintenant » AWARE en UTC — l'unique source d'horodatage du projet.

    Remplace tous les `datetime.now()` naïfs (heure locale) : les timestamps de
    mesure/audit/session doivent être non ambigus pour l'audit et le mandat
    timestamptz (résidence UAE de données de mineurs).
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalise en aware-UTC un datetime relu de la base (ou fourni par l'appelant).

    Patron unique du projet : Postgres (timestamptz) restitue des datetimes aware ;
    SQLite (dev/CI) restitue des datetimes NAÏFS même sur colonne tz-aware — comme
    tout est écrit en UTC (cf. `utcnow`), un naïf est réinterprété UTC tel quel.
    Un aware non-UTC est converti. À appliquer AVANT toute comparaison/soustraction
    avec un datetime aware (expiration, stopping, rétention, fenêtres d'analyse).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def native_enum(enum_cls, name: str) -> SAEnum:
    """Colonne enum qui stocke la VALEUR du membre (ex. 'active'), pas son nom.

    Aligne le stockage sur les valeurs du data model (draft/active, expert/empirical)
    et garantit la cohérence avec les labels des enums natifs Postgres créés par Alembic.
    Sans ça, SQLAlchemy persisterait le nom du membre ('ACTIVE') → rejet par Postgres.
    """
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


# --- Enums métier ---

class Subject(str, enum.Enum):
    MATH = "MATH"


class CognitiveLevel(str, enum.Enum):
    RECALL = "RECALL"
    APPLY = "APPLY"
    REASON = "REASON"


class CompetencyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class EdgeType(str, enum.Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class WeightSource(str, enum.Enum):
    EXPERT = "expert"
    EMPIRICAL = "empirical"


class ItemStatus(str, enum.Enum):
    AI_GENERATED = "ai_generated"
    HUMAN_REVIEWED = "human_reviewed"
    LINGUIST_VALIDATED = "linguist_validated"
    ACTIVE = "active"
    QUARANTINED = "quarantined"


class AnswerFormat(str, enum.Enum):
    MCQ = "MCQ"
    NUMERIC = "NUMERIC"
    SHORT = "SHORT"


class Role(str, enum.Enum):
    SUPER_ADMIN = "super_admin"   # Atlas/éditeur — accès illimité
    IT_ADMIN = "it_admin"         # SSO, sécurité globale (gate d'achat)
    PED_ADMIN = "ped_admin"       # établissement : licences, analytics école
    TEACHER = "teacher"           # ses classes
    PARENT = "parent"             # lecture seule sur son enfant
    STUDENT = "student"           # ses propres activités


# Helpers de colonnes communes (mixin léger, pas d'abstraction magique)
def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
