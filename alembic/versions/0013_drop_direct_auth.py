"""drop direct auth — SSO obligatoire : retire password_hash / totp_secret / mfa_enabled

Suite à la revue sécurité DSI : authentification 100 % IdP (OIDC), plus de comptes
directs ni de MFA TOTP applicative (MFA portée par l'IdP). On supprime donc les colonnes
d'auth locale de `app_user`. L'identité reste ancrée sur `external_ref` (id IdP/annuaire).

Revision ID: 0013_drop_direct_auth
Revises: 0012_parent_student_source
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_drop_direct_auth"
down_revision: Union[str, None] = "0012_parent_student_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = ("password_hash", "totp_secret", "mfa_enabled")


def upgrade() -> None:
    # batch_alter_table : portable SQLite (recrée la table) ET Postgres (DROP COLUMN natif).
    with op.batch_alter_table("app_user") as batch:
        for col in _COLS:
            batch.drop_column(col)


def downgrade() -> None:
    with op.batch_alter_table("app_user") as batch:
        batch.add_column(sa.Column("password_hash", sa.String(), nullable=True))
        batch.add_column(sa.Column("totp_secret", sa.String(), nullable=True))
        batch.add_column(sa.Column("mfa_enabled", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))
