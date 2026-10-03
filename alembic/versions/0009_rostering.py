"""rostering — external_ref (org/school/classroom/app_user) + tenant_integration + roster_run

Revision ID: 0009_rostering
Revises: 0008_totp_secret
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_rostering"
down_revision: Union[str, None] = "0008_totp_secret"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- IDs externes (réconciliation rostering, upsert idempotent) ---
    op.add_column("organization", sa.Column("domain", sa.String(), nullable=True))
    op.add_column("organization", sa.Column("external_ref", sa.String(), nullable=True))
    op.add_column("organization", sa.Column("seats", sa.Integer(), nullable=True))
    op.create_index("ix_organization_domain", "organization", ["domain"], unique=True)

    op.add_column("school", sa.Column("external_ref", sa.String(), nullable=True))
    op.create_index("ix_school_external_ref", "school", ["external_ref"])

    op.add_column("classroom", sa.Column("external_ref", sa.String(), nullable=True))
    op.create_index("ix_classroom_external_ref", "classroom", ["external_ref"])

    op.add_column("app_user", sa.Column("external_ref", sa.String(), nullable=True))
    op.create_index("ix_app_user_external_ref", "app_user", ["external_ref"])

    # --- Intégration d'annuaire par organisation ---
    op.create_table(
        "tenant_integration",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="google"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("admin_email", sa.String(), nullable=True),
        sa.Column("customer_id", sa.String(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tenant_integration_organization_id", "tenant_integration",
                    ["organization_id"], unique=True)

    # --- Journal des synchronisations (audit) ---
    op.create_table(
        "roster_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ok"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deactivated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_roster_run_organization_id", "roster_run", ["organization_id"])


def downgrade() -> None:
    op.drop_table("roster_run")
    op.drop_table("tenant_integration")
    op.drop_index("ix_app_user_external_ref", table_name="app_user")
    op.drop_column("app_user", "external_ref")
    op.drop_index("ix_classroom_external_ref", table_name="classroom")
    op.drop_column("classroom", "external_ref")
    op.drop_index("ix_school_external_ref", table_name="school")
    op.drop_column("school", "external_ref")
    op.drop_index("ix_organization_domain", table_name="organization")
    op.drop_column("organization", "seats")
    op.drop_column("organization", "external_ref")
    op.drop_column("organization", "domain")
