"""competency_curriculum_map.enrich_kind — deux wordings ENRICH (M-4, décision 2026-07-12)

Un ENRICH peut vouloir dire deux choses : Atlas mesure la compétence UN GRADE PLUS TÔT
que le standard (« taught earlier than {code} » — un argument), ou l'exigence est
ABSENTE du standard (« beyond {code} expectations »). Le wording produit doit les
distinguer. `enrich_kind ∈ {grade, requirement}` (NULL pour tout ce qui n'est pas ENRICH).
Colonne nullable simple → ADD COLUMN portable SQLite/Postgres, pas de batch/offline.

Revision ID: 0020_enrich_kind
Revises: 0019_curriculum_language
Create Date: 2026-07-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_enrich_kind"
down_revision: Union[str, None] = "0019_curriculum_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "competency_curriculum_map",
        sa.Column("enrich_kind", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("competency_curriculum_map", "enrich_kind")
