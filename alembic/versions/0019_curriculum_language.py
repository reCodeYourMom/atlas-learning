"""curriculum + langue servie — C-0 (Lot C) et B2/B3 (Lot B)

C-0 (BLOQUANT PRÉ-PILOTE) : `response.language` + `assessment_session.locale`
(enum 'en'/'ar', NOT NULL, server_default 'en'). Sans la langue servie, aucune
analyse DIF EN/AR ne sera jamais possible sur le journal append-only du pilote
(pas de backfill). Les lignes existantes sont réputées anglaises (état de fait :
seule l'UI EN a servi des réponses avant cette migration).

B2 : `curriculum_standard` (standards CCSS-M / UK NC / MoE UAE) +
`competency_curriculum_map` (alignement type+confiance, provenance versionnée —
même pattern que competency_prerequisite). D-B4 : type+confiance remplacent
l'alignment_strength scalaire du DataModel §7.

B3 : `organization.curriculum_view` (défaut 'ATLAS' = vue neutre actuelle,
zéro régression pour les tenants existants).

DIALECTES (pattern 0016/0017) : sur Postgres, un type enum n'est PAS créé
automatiquement par ADD COLUMN → création explicite AVANT (checkfirst), puis
référence en `create_type=False` (idem pour `weight_source`, type PRÉEXISTANT
depuis 0001, que create_table tenterait sinon de recréer). Sur SQLite,
native_enum = VARCHAR sans contrainte : create/drop de types sont des no-ops.

Revision ID: 0019_curriculum_language
Revises: 0018_legal_hold
Create Date: 2026-07-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_curriculum_language"
down_revision: Union[str, None] = "0018_legal_hold"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# valeurs stockées = VALEURS des enums python (native_enum, src/models/base.py)
ENUMS = {
    "response_language": ("en", "ar"),
    "curriculum_view": ("ATLAS", "CCSS_M", "UK_NC", "MOE_UAE"),
    "curriculum_framework": ("CCSS_M", "UK_NC", "MOE_UAE"),
    "alignment_type": ("EXACT", "PARTIAL", "BROADER", "PREREQ", "ENRICH"),
    "mapping_confidence": ("H", "M"),
}


def _enum(name: str, is_pg: bool) -> sa.types.TypeEngine:
    """Référence de type portable : PG = type natif DÉJÀ créé (create_type=False),
    SQLite = sa.Enum rendu VARCHAR (aucun type à créer)."""
    if is_pg:
        return postgresql.ENUM(name=name, create_type=False)
    return sa.Enum(*ENUMS.get(name, ("expert", "empirical")), name=name)


def upgrade() -> None:
    from alembic import context

    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        # ADD COLUMN ne crée pas le type sur Postgres → création explicite d'abord.
        if context.is_offline_mode():
            # --sql (revue 2026-07-12) : `checkfirst` exige une connexion vivante →
            # DO block idempotent (duplicate_object ignoré), équivalent offline.
            for name, values in ENUMS.items():
                vals = ", ".join(f"''{v}''" for v in values)
                op.execute(
                    f"DO 'BEGIN CREATE TYPE {name} AS ENUM ({vals}); "
                    f"EXCEPTION WHEN duplicate_object THEN NULL; END'"
                )
        else:
            for name, values in ENUMS.items():
                sa.Enum(*values, name=name).create(bind, checkfirst=True)

    # --- C-0 : langue servie par réponse + locale de session ---
    with op.batch_alter_table("response") as batch:
        batch.add_column(sa.Column(
            "language", _enum("response_language", is_pg),
            nullable=False, server_default="en",
        ))
    with op.batch_alter_table("assessment_session") as batch:
        batch.add_column(sa.Column(
            "locale", _enum("response_language", is_pg),
            nullable=False, server_default="en",
        ))

    # --- B3 : framework d'affichage par tenant ---
    with op.batch_alter_table("organization") as batch:
        batch.add_column(sa.Column(
            "curriculum_view", _enum("curriculum_view", is_pg),
            nullable=False, server_default="ATLAS",
        ))

    # --- B2 : standards externes + crosswalk ---
    op.create_table(
        "curriculum_standard",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("framework", _enum("curriculum_framework", is_pg), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("label_en", sa.String(), nullable=False),
        sa.Column("label_ar", sa.String(), nullable=False),
        sa.Column("grade_hint", sa.String(), nullable=True),
        sa.UniqueConstraint("framework", "code", name="uq_curriculum_standard_framework_code"),
    )
    op.create_table(
        "competency_curriculum_map",
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("standard_id", sa.Uuid(), nullable=False),
        sa.Column("alignment_type", _enum("alignment_type", is_pg), nullable=False),
        sa.Column("confidence", _enum("mapping_confidence", is_pg), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("weight_source", _enum("weight_source", is_pg),
                  nullable=False, server_default="expert"),
        sa.Column("weight_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.PrimaryKeyConstraint("competency_id", "standard_id"),
        sa.ForeignKeyConstraint(["competency_id"], ["competency.id"], ondelete="CASCADE",
                                name="fk_ccm_competency"),
        sa.ForeignKeyConstraint(["standard_id"], ["curriculum_standard.id"], ondelete="CASCADE",
                                name="fk_ccm_standard"),
    )
    # lookup inverse (standard → compétences) ; le sens direct est couvert par la PK
    op.create_index("ix_ccm_standard", "competency_curriculum_map", ["standard_id"])


def downgrade() -> None:
    op.drop_index("ix_ccm_standard", table_name="competency_curriculum_map")
    op.drop_table("competency_curriculum_map")
    op.drop_table("curriculum_standard")
    with op.batch_alter_table("organization") as batch:
        batch.drop_column("curriculum_view")
    with op.batch_alter_table("assessment_session") as batch:
        batch.drop_column("locale")
    with op.batch_alter_table("response") as batch:
        batch.drop_column("language")
    from alembic import context

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # types créés PAR cette migration seulement — weight_source (0001) reste en place
        if context.is_offline_mode():
            for name in ENUMS:
                op.execute(f"DROP TYPE IF EXISTS {name}")
        else:
            for name, values in ENUMS.items():
                sa.Enum(*values, name=name).drop(bind, checkfirst=True)
