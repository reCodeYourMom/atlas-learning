"""item.content_ar nullable — l'AR est rempli en T2.4 (après revue EN T2.3)

Revision ID: 0003_item_ar_nullable
Revises: 0002_epic2_item
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_item_ar_nullable"
down_revision: Union[str, None] = "0002_epic2_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("item") as batch:
        batch.alter_column("content_ar", existing_type=json_type, nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("item") as batch:
        batch.alter_column("content_ar", existing_type=json_type, nullable=False)
