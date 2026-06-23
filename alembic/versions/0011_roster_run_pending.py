"""roster_run — pending_deactivations (garde-fou de déprovisioning bloquant)

Revision ID: 0011_roster_run_pending
Revises: 0010_student_classroom
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_roster_run_pending"
down_revision: Union[str, None] = "0010_student_classroom"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("roster_run",
                  sa.Column("pending_deactivations", sa.Integer(),
                            nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("roster_run", "pending_deactivations")
