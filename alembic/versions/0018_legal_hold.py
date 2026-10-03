"""legal hold — colonnes de suspension de purge sur school et student

Réponse à l'avis juridique rétention (2026-07-08) : la purge automatique à J+30
(RETENTION_DAYS, plafonné à 30) doit s'effacer devant un LEGAL HOLD — obligation de
conservation, litige, ou instruction documentée du controller (l'école). On ajoute :
- `student.legal_hold` (timestamptz) + `student.legal_hold_reason` : hold individuel ;
- `school.legal_hold` (timestamptz) + `school.legal_hold_reason` : hold tenant-large
  (instruction controller / litige école) qui protège TOUS les élèves de l'école.
`purge_retention` exclut tout élève dont `legal_hold` (propre) OU celui de son école est
posé. Colonnes nullables (défaut = pas de hold), aucune donnée à convertir.

Revision ID: 0018_legal_hold
Revises: 0017_role_linguist
Create Date: 2026-07-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_legal_hold"
down_revision: Union[str, None] = "0017_role_linguist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("school", "student")


def upgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("legal_hold", sa.DateTime(timezone=True), nullable=True))
            batch.add_column(sa.Column("legal_hold_reason", sa.String(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("legal_hold_reason")
            batch.drop_column("legal_hold")
