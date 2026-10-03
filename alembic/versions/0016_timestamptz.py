"""timestamptz — toutes les colonnes timestamp passent en timezone-aware (revue 2026-07-07)

Les colonnes de mesure/audit/session étaient des TIMESTAMP SANS timezone, remplies par
des datetime.now() NAÏFS (heure locale du serveur) : horodatage ambigu → défaut
d'intégrité pour l'audit et la résidence UAE de données de mineurs (mandat timestamptz).
Le code n'écrit plus que de l'UTC aware (src/models/base.py : utcnow / ensure_utc) ;
cette migration aligne le schéma : DateTime(timezone=True) partout.

Postgres : ALTER ... TYPE timestamptz USING "colonne AT TIME ZONE 'UTC'" — les valeurs
existantes (naïves) sont RÉINTERPRÉTÉES comme de l'UTC. Choix assumé et documenté :
les seules bases antérieures sont dev/démo (données rejouables) ; un éventuel décalage
d'heure locale sur ces données historiques est acceptable.
SQLite (dev/CI) : batch recrée la table ; le type stocké ne change pas (TEXT), la
sémantique tz vit dans le type SQLAlchemy — rien à convertir.

Revision ID: 0016_timestamptz
Revises: 0015_uq_response_session_item
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_timestamptz"
down_revision: Union[str, None] = "0015_uq_response_session_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Toutes les colonnes timestamp du schéma à la révision 0015 (modèles = source de vérité).
# NB : consumed_token (0014) est déjà créée en DateTime(timezone=True) — rien à re-altérer.
TIMESTAMP_COLUMNS = {
    "competency": ["created_at", "updated_at", "deleted_at"],
    "competency_prerequisite": ["created_at"],
    "item": ["created_at", "updated_at", "deleted_at"],
    "school": ["deleted_at"],
    "student": ["deleted_at"],
    "response": ["created_at"],
    "student_competency_ability": ["last_measured_at", "created_at", "updated_at"],
    "assessment_session": ["started_at", "ended_at"],
    "organization": ["deleted_at"],
    "classroom": ["deleted_at"],
    "app_user": ["created_at", "updated_at", "deleted_at"],
    "tenant_integration": ["last_sync_at", "created_at", "updated_at"],
    "roster_run": ["started_at", "finished_at"],
    "audit_log": ["created_at"],
}


def _alter_all(from_type: sa.types.TypeEngine, to_type: sa.types.TypeEngine,
               using_suffix: str) -> None:
    """batch_alter_table : ALTER natif sur Postgres, recréation de table sur SQLite.

    `postgresql_using` est un kwarg dialecte : ignoré par SQLite, appliqué par Postgres
    (réinterprétation explicite des valeurs — jamais la timezone de session du serveur).
    """
    for table, columns in TIMESTAMP_COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for col in columns:
                batch_op.alter_column(
                    col,
                    type_=to_type,
                    existing_type=from_type,
                    postgresql_using=f"{col} {using_suffix}",
                )


def upgrade() -> None:
    # naïf (réinterprété UTC) → timestamptz
    _alter_all(sa.DateTime(), sa.DateTime(timezone=True), "AT TIME ZONE 'UTC'")


def downgrade() -> None:
    # timestamptz → naïf : on garde le mur d'horloge UTC (symétrique de l'upgrade).
    _alter_all(sa.DateTime(timezone=True), sa.DateTime(), "AT TIME ZONE 'UTC'")
