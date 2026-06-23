"""epic2 item — table item + enums item_status / answer_format

Revision ID: 0002_epic2_item
Revises: 0001_epic1_referentiel
Create Date: 2026-06-21

T2.1 AC#1 : `alembic upgrade head` crée la table + enums sans erreur.
content_*/context_tags/provenance en JSONB (Postgres) / JSON (SQLite).
FK competency_id ON DELETE RESTRICT (AC#4).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_epic2_item"
down_revision: Union[str, None] = "0001_epic1_referentiel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

item_status = sa.Enum(
    "ai_generated", "human_reviewed", "linguist_validated", "active", "quarantined",
    name="item_status",
)
answer_format = sa.Enum("MCQ", "NUMERIC", "SHORT", name="answer_format")

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "item",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("content_en", json_type, nullable=False),
        sa.Column("content_ar", json_type, nullable=False),
        sa.Column("answer_format", answer_format, nullable=False),
        sa.Column("difficulty_prior", sa.Float(), nullable=False),
        sa.Column("difficulty_elo", sa.Float(), nullable=False),
        sa.Column("n_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_tags", json_type, nullable=False),
        sa.Column("status", item_status, nullable=False, server_default="ai_generated"),
        sa.Column("provenance", json_type, nullable=False),
        sa.Column("ar_validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["competency_id"], ["competency.id"], ondelete="RESTRICT",
            name="fk_item_competency",
        ),
    )
    op.create_index("ix_item_competency_id", "item", ["competency_id"])


def downgrade() -> None:
    op.drop_index("ix_item_competency_id", table_name="item")
    op.drop_table("item")
    for e in (answer_format, item_status):
        e.drop(op.get_bind(), checkfirst=True)
