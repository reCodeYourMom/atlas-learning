"""epic1 referentiel — competency + competency_prerequisite + enums

Revision ID: 0001_epic1_referentiel
Revises:
Create Date: 2026-06-21

T1.1 AC#1 : `alembic upgrade head` crée les 2 tables + enums sans erreur.
Portable Postgres (enums natifs) / SQLite (VARCHAR + CHECK auto).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_epic1_referentiel"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# enums métier (créés automatiquement par create_table sur Postgres)
subject = sa.Enum("MATH", name="subject")
cognitive_level = sa.Enum("RECALL", "APPLY", "REASON", name="cognitive_level")
competency_status = sa.Enum("draft", "active", "deprecated", name="competency_status")
edge_type = sa.Enum("HARD", "SOFT", name="edge_type")
weight_source = sa.Enum("expert", "empirical", name="weight_source")


def upgrade() -> None:
    op.create_table(
        "competency",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("label_en", sa.String(), nullable=False),
        sa.Column("label_ar", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("subject", subject, nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("cognitive_level", cognitive_level, nullable=True),
        sa.Column("difficulty_prior", sa.Float(), nullable=False),
        sa.Column("status", competency_status, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_competency_code", "competency", ["code"], unique=True)
    op.create_index("ix_competency_grade", "competency", ["grade"])

    op.create_table(
        "competency_prerequisite",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("edge_type", edge_type, nullable=False),
        sa.Column("correlation_strength", sa.Float(), nullable=False),
        sa.Column("weight_source", weight_source, nullable=False, server_default="expert"),
        sa.Column("weight_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"], ["competency.id"], ondelete="CASCADE",
            name="fk_prereq_source",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"], ["competency.id"], ondelete="CASCADE",
            name="fk_prereq_target",
        ),
        sa.PrimaryKeyConstraint("source_id", "target_id"),
        sa.CheckConstraint("source_id <> target_id", name="ck_no_self_loop"),
    )
    op.create_index("ix_prereq_source", "competency_prerequisite", ["source_id"])
    op.create_index("ix_prereq_target", "competency_prerequisite", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_prereq_target", table_name="competency_prerequisite")
    op.drop_index("ix_prereq_source", table_name="competency_prerequisite")
    op.drop_table("competency_prerequisite")
    op.drop_index("ix_competency_grade", table_name="competency")
    op.drop_index("ix_competency_code", table_name="competency")
    op.drop_table("competency")
    for e in (weight_source, edge_type, competency_status, cognitive_level, subject):
        e.drop(op.get_bind(), checkfirst=True)
