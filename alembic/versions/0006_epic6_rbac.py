"""epic6 rbac — organization, classroom, app_user, membership + liens ; extend school/student

Revision ID: 0006_epic6_rbac
Revises: 0005_epic4_session
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_epic6_rbac"
down_revision: Union[str, None] = "0005_epic4_session"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

role = sa.Enum("super_admin", "it_admin", "ped_admin", "teacher", "parent", "student", name="role")


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_app_user_email", "app_user", ["email"], unique=True)

    op.create_table(
        "classroom",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"], ondelete="CASCADE", name="fk_class_school"),
    )
    op.create_index("ix_classroom_school_id", "classroom", ["school_id"])

    op.create_table(
        "membership",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("school_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE", name="fk_mem_user"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE", name="fk_mem_org"),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"], ondelete="CASCADE", name="fk_mem_school"),
    )
    for c in ("user_id", "organization_id", "school_id"):
        op.create_index(f"ix_membership_{c}", "membership", [c])

    op.create_table(
        "teacher_classroom",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "classroom_id"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE", name="fk_tc_user"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"], ondelete="CASCADE", name="fk_tc_class"),
    )
    op.create_table(
        "parent_student",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "student_id"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE", name="fk_ps_user"),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="CASCADE", name="fk_ps_student"),
    )

    with op.batch_alter_table("school") as b:
        b.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        b.create_foreign_key("fk_school_org", "organization", ["organization_id"], ["id"], ondelete="CASCADE")

    with op.batch_alter_table("student") as b:
        b.add_column(sa.Column("classroom_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        b.create_foreign_key("fk_student_classroom", "classroom", ["classroom_id"], ["id"], ondelete="SET NULL")
        b.create_foreign_key("fk_student_user", "app_user", ["user_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("student") as b:
        b.drop_constraint("fk_student_user", type_="foreignkey")
        b.drop_constraint("fk_student_classroom", type_="foreignkey")
        b.drop_column("deleted_at")
        b.drop_column("user_id")
        b.drop_column("classroom_id")
    with op.batch_alter_table("school") as b:
        b.drop_constraint("fk_school_org", type_="foreignkey")
        b.drop_column("deleted_at")
        b.drop_column("organization_id")
    op.drop_table("parent_student")
    op.drop_table("teacher_classroom")
    op.drop_table("membership")
    op.drop_table("classroom")
    op.drop_index("ix_app_user_email", table_name="app_user")
    op.drop_table("app_user")
    op.drop_table("organization")
    role.drop(op.get_bind(), checkfirst=True)
