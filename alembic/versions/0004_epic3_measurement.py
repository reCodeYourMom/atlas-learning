"""epic3 measurement — school, student, response, student_competency_ability

Revision ID: 0004_epic3_measurement
Revises: 0003_item_ar_nullable
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_epic3_measurement"
down_revision: Union[str, None] = "0003_item_ar_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "school",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
    )
    op.create_table(
        "student",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("external_ref", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"], ondelete="CASCADE",
                                name="fk_student_school"),
    )
    op.create_index("ix_student_school_id", "student", ["school_id"])

    op.create_table(
        "response",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"], ondelete="CASCADE", name="fk_resp_school"),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="CASCADE", name="fk_resp_student"),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="RESTRICT", name="fk_resp_item"),
    )
    for col in ("school_id", "student_id", "item_id", "competency_id"):
        op.create_index(f"ix_response_{col}", "response", [col])

    op.create_table(
        "student_competency_ability",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("ability_elo", sa.Float(), nullable=False),
        sa.Column("n_direct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_measured_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("student_id", "competency_id"),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="CASCADE", name="fk_sca_student"),
        sa.ForeignKeyConstraint(["competency_id"], ["competency.id"], ondelete="CASCADE", name="fk_sca_comp"),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"], ondelete="CASCADE", name="fk_sca_school"),
    )
    op.create_index("ix_sca_school_id", "student_competency_ability", ["school_id"])


def downgrade() -> None:
    op.drop_table("student_competency_ability")
    op.drop_table("response")
    op.drop_index("ix_student_school_id", table_name="student")
    op.drop_table("student")
    op.drop_table("school")
