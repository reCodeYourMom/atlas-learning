"""role linguist — ajoute la valeur 'linguist' à l'enum RBAC `role`

Le linguiste est un STAFF Atlas GLOBAL (il relit/valide l'arabe de la banque d'items,
contenu non tenant-scopé). On étend donc l'enum de rôles.

PIÈGE POSTGRES (documenté) : sur Postgres, `role` est un TYPE ENUM natif — on ne peut
pas ajouter une valeur avec un simple INSERT/UPDATE, il faut `ALTER TYPE role ADD VALUE`.
Or, sur les versions PG < 12, `ADD VALUE` ne peut PAS s'exécuter dans un bloc
transactionnel (« ALTER TYPE ... ADD cannot run inside a transaction block »). Alembic
enveloppe chaque migration dans une transaction : on récupère donc la connexion,
COMMIT la transaction courante, puis on émet le `ADD VALUE` avec autocommit (PG ≥ 12
l'accepte aussi hors transaction, donc le chemin est sûr partout). `IF NOT EXISTS`
(PG ≥ 12) rend l'upgrade idempotent ; on l'omet ici pour rester compatible < 12 et on
protège plutôt par un garde d'existence.

SQLITE (dev/CI) : `native_enum()` n'émet PAS de CHECK constraint (create_constraint=False
par défaut, cf. src/models/base.py) — la colonne `role` est un simple VARCHAR. Aucune
modification de schéma n'est nécessaire, l'upgrade est un no-op sur SQLite. C'est ce
cas que testent test_migrations.py et test_linguist_role.py.

DOWNGRADE : Postgres ne sait pas retirer une valeur d'un enum. Le downgrade est donc un
no-op documenté (la valeur reste dans le type, sans usage). Aucune donnée n'est perdue et
la chaîne reste réversible du point de vue schéma.

Revision ID: 0017_role_linguist
Revises: 0016_timestamptz
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0017_role_linguist"
down_revision: Union[str, None] = "0016_timestamptz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite : `role` est un VARCHAR sans contrainte (native_enum sans CHECK) → rien à faire.
        return
    # La valeur existe déjà ? (upgrade rejoué / base déjà à niveau) → on ne fait rien.
    exists = bind.exec_driver_sql(
        "SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE t.typname = 'role' AND e.enumlabel = 'linguist'"
    ).first()
    if exists:
        return
    # `ADD VALUE` ne tourne pas dans une transaction sur PG < 12 : on sort du bloc
    # transactionnel d'Alembic (commit) puis on émet l'ALTER en autocommit.
    op.execute("COMMIT")
    bind.exec_driver_sql("ALTER TYPE role ADD VALUE 'linguist'")


def downgrade() -> None:
    # Postgres ne permet pas de RETIRER une valeur d'un enum ; SQLite n'a rien ajouté.
    # No-op assumé : la valeur 'linguist' reste dans le type mais sans membership l'utilisant.
    pass
