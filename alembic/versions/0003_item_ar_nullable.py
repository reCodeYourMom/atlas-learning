"""item.content_ar nullable — l'AR est rempli en T2.4 (après revue EN T2.3)

Revision ID: 0003_item_ar_nullable
Revises: 0002_epic2_item
Create Date: 2026-06-21

`copy_from` (revue 2026-07-12) : en batch mode SQLite, ALTER COLUMN = recréation de
table, qui exige le schéma courant. Sans `copy_from`, Alembic le REFLÈTE depuis une
connexion vivante — impossible en mode offline (`upgrade head --sql`), qui échouait
ici (exit 255). Le schéma fourni est la table `item` telle que créée par 0002, index
et FK inclus (sinon la recréation online les perdrait silencieusement). Sur Postgres,
batch = passthrough : `copy_from` est ignoré.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_item_ar_nullable"
down_revision: Union[str, None] = "0002_epic2_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

item_status = sa.Enum(
    "ai_generated", "human_reviewed", "linguist_validated", "active", "quarantined",
    name="item_status",
)
answer_format = sa.Enum("MCQ", "NUMERIC", "SHORT", name="answer_format")


def _item_table(*, content_ar_nullable: bool) -> sa.Table:
    """La table `item` AVANT modification (état 0002, à la nullabilité près)."""
    return sa.Table(
        "item",
        sa.MetaData(),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("content_en", json_type, nullable=False),
        sa.Column("content_ar", json_type, nullable=content_ar_nullable),
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
        sa.Index("ix_item_competency_id", "competency_id"),
    )


def upgrade() -> None:
    with op.batch_alter_table(
        "item", copy_from=_item_table(content_ar_nullable=False)
    ) as batch:
        batch.alter_column("content_ar", existing_type=json_type, nullable=True)


def downgrade() -> None:
    with op.batch_alter_table(
        "item", copy_from=_item_table(content_ar_nullable=True)
    ) as batch:
        batch.alter_column("content_ar", existing_type=json_type, nullable=False)
