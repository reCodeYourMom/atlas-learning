"""audit_log — journal d'accès & actions (must-have V1 sécu)

Revision ID: 0007_audit_log
Revises: 0006_epic6_rbac
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_audit_log"
down_revision: Union[str, None] = "0006_epic6_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("details", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_school_id", "audit_log", ["school_id"])
    op.create_index("ix_audit_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_action", "audit_log", ["action"])
    op.create_index("ix_audit_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
