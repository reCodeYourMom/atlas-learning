"""consumed_token — anti-rejeu des liens magiques (revue sécurité 2026-07-07)

Les liens magiques (parent / super-admin) étaient annoncés « single-use » mais restaient
rejouables jusqu'à expiration (aucun état serveur). Chaque lien porte désormais un `jti`
aléatoire signé ; à la connexion, le `jti` est inséré ici — la clé primaire (unicité)
rend la consommation ATOMIQUE : le second usage lève IntegrityError → refusé.
`expires_at` sert à la purge des lignes devenues inutiles (scripts/purge_retention.py).

Revision ID: 0014_consumed_token
Revises: 0013_drop_direct_auth
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_consumed_token"
down_revision: Union[str, None] = "0013_drop_direct_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consumed_token",
        sa.Column("jti", sa.String(), primary_key=True),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        # timezone=True dès la création : aligné sur src/models/token.py — la table est
        # neuve (jamais déployée), inutile de la re-altérer en 0016.
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consumed_token_expires_at", "consumed_token", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_consumed_token_expires_at", table_name="consumed_token")
    op.drop_table("consumed_token")
