"""epic4 session — assessment_session

Revision ID: 0005_epic4_session
Revises: 0004_epic3_measurement
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_epic4_session"
down_revision: Union[str, None] = "0004_epic3_measurement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "assessment_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("target_competency_ids", json_type, nullable=True),
        sa.Column("stop_reason", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"], ondelete="CASCADE", name="fk_sess_school"),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="CASCADE", name="fk_sess_student"),
    )
    op.create_index("ix_session_school_id", "assessment_session", ["school_id"])
    op.create_index("ix_session_student_id", "assessment_session", ["student_id"])


def downgrade() -> None:
    op.drop_table("assessment_session")
