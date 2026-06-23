"""mfa totp — colonne totp_secret sur app_user (TOTP standard RFC 6238)

Revision ID: 0008_totp_secret
Revises: 0007_audit_log
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_totp_secret"
down_revision: Union[str, None] = "0007_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("app_user", sa.Column("totp_secret", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_user", "totp_secret")
