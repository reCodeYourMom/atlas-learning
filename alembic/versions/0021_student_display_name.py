"""student.display_name — nom affiché de l'élève

Jusqu'ici un élève n'avait AUCUN champ nom : les vues enseignant affichaient
`external_ref` (l'identifiant de l'annuaire source, ex. « S1 », « STU-40912 »). Lisible
par une machine, illisible par un professeur — et intenable dans une démo où l'on parle
d'élèves réels devant un directeur académique.

`display_name` est le nom tel que l'établissement veut le voir affiché, alimenté par le
rostering (Google/OneRoster : `name.fullName` / `givenName familyName`) ou saisi par
l'école. Il ne remplace PAS `external_ref`, qui reste l'ancre d'identité durable et
immuable côté annuaire — un élève peut être renommé sans changer d'identité.

Nullable : les élèves existants gardent NULL, et les vues retombent sur `external_ref`.

Revision ID: 0021_student_display_name
Revises: 0020_enrich_kind
Create Date: 2026-09-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_student_display_name"
down_revision: Union[str, None] = "0020_enrich_kind"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("student") as batch:
        batch.add_column(sa.Column("display_name", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("student") as batch:
        batch.drop_column("display_name")
