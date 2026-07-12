"""student_classroom — inscription élève↔classe en M:N (classes de spécialité)

Revision ID: 0010_student_classroom
Revises: 0009_rostering
Create Date: 2026-06-21

`Student.classroom_id` devient la classe principale (homeroom) ; les inscriptions
complètes (principale + spécialités) vivent dans cette table. Backfill : chaque élève
ayant une classe principale est inscrit dans student_classroom.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_student_classroom"
down_revision: Union[str, None] = "0009_rostering"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_classroom",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_id", "classroom_id"),
    )
    # Backfill : l'inscription principale existante devient une ligne M:N.
    op.execute(
        "INSERT INTO student_classroom (student_id, classroom_id) "
        "SELECT id, classroom_id FROM student WHERE classroom_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_table("student_classroom")
