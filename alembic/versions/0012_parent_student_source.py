"""parent_student — source du lien (roster | staff) pour la coexistence des autorités

Revision ID: 0012_parent_student_source
Revises: 0011_roster_run_pending
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_parent_student_source"
down_revision: Union[str, None] = "0011_roster_run_pending"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Les liens existants viennent du rostering (Google Classroom).
    op.add_column("parent_student",
                  sa.Column("source", sa.String(), nullable=False, server_default="roster"))


def downgrade() -> None:
    op.drop_column("parent_student", "source")
