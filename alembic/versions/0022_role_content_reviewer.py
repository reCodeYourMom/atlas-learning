"""role content_reviewer — ajoute la valeur 'content_reviewer' à l'enum RBAC `role`

La revue pédagogique EN (approve/reject) et l'activation finale (promote_to_active) n'avaient
NI rôle, NI identité : `scripts/review_items.py --reviewer <texte libre>`, sans compte, sans
audit. Le didacticien et l'expert contenu n'existaient que dans des fichiers Markdown.

`content_reviewer` est un STAFF Atlas GLOBAL (comme `linguist`) : il relit le contenu
anglais, rejette, et est le seul (avec super_admin) à pouvoir activer un item ou le sortir
de quarantaine. Aucun périmètre école : la banque n'est pas tenant-scopée.

Mécanique identique à 0017_role_linguist (ALTER TYPE ... ADD VALUE hors transaction sur
Postgres ; no-op sur SQLite où `role` est un VARCHAR sans CHECK ; downgrade no-op assumé).

Revision ID: 0022_role_content_reviewer
Revises: 0021_student_display_name
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0022_role_content_reviewer"
down_revision: Union[str, None] = "0021_student_display_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALUE = "content_reviewer"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    from alembic import context
    if context.is_offline_mode():
        op.execute("COMMIT")
        op.execute(f"ALTER TYPE role ADD VALUE IF NOT EXISTS '{VALUE}'")
        return
    exists = bind.exec_driver_sql(
        "SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        f"WHERE t.typname = 'role' AND e.enumlabel = '{VALUE}'"
    ).first()
    if exists:
        return
    op.execute("COMMIT")
    bind.exec_driver_sql(f"ALTER TYPE role ADD VALUE '{VALUE}'")


def downgrade() -> None:
    # Postgres ne retire pas une valeur d'enum ; SQLite n'a rien ajouté. No-op assumé.
    pass
