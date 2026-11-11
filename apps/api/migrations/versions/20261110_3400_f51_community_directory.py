"""F5.1 community directory verification and service detail fields.

Extends ``community_services`` with verification workflow columns and adds
``community_service_verification_events`` for audit history. No service rows
are seeded.

Revision ID: 20261110_3400_f51
Revises: 20261110_3300_f46
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3400_f51"
down_revision: Union[str, None] = "20261110_3300_f46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _policy(table: str) -> str:
    return f"""
    CREATE POLICY hmore_org_isolation ON {table}
      FOR ALL
      USING (
        current_setting('app.rls_bypass', true) = 'on'
        OR organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
      )
      WITH CHECK (
        current_setting('app.rls_bypass', true) = 'on'
        OR organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
      );
    """


def upgrade() -> None:
    op.add_column("community_services", sa.Column("opening_days", sa.Text(), nullable=True))
    op.add_column("community_services", sa.Column("referral_requirements", sa.Text(), nullable=True))
    op.add_column("community_services", sa.Column("service_instructions", sa.Text(), nullable=True))
    op.add_column(
        "community_services",
        sa.Column("clothing_service_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "community_services",
        sa.Column(
            "verification_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending_verification",
        ),
    )
    op.add_column(
        "community_services",
        sa.Column("information_source", sa.String(length=255), nullable=True),
    )
    op.add_column("community_services", sa.Column("verification_notes", sa.Text(), nullable=True))
    op.add_column(
        "community_services",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_services",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "community_services",
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "community_services",
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_check_constraint(
        "ck_community_services_verification_status",
        "community_services",
        "verification_status IN ("
        "'pending_verification', 'verified', 'needs_review', 'outdated', 'inactive'"
        ")",
    )
    op.create_check_constraint(
        "ck_community_services_clothing_service_type",
        "community_services",
        "clothing_service_type IS NULL OR clothing_service_type IN ("
        "'provides_clothing', 'accepts_donations', 'both'"
        ")",
    )
    op.create_foreign_key(
        "fk_community_services_created_by_user_id",
        "community_services",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_services_updated_by_user_id",
        "community_services",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_services_verified_by_user_id",
        "community_services",
        "users",
        ["verified_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_community_services_org_category_status",
        "community_services",
        ["organisation_id", "category", "verification_status"],
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_community_services_org_name_lower "
            "ON community_services (organisation_id, lower(name), category)"
        )
    )

    op.create_table(
        "community_service_verification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["community_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "to_status IN ("
            "'pending_verification', 'verified', 'needs_review', 'outdated', 'inactive'"
            ")",
            name="ck_cs_verification_events_to_status",
        ),
    )
    op.create_index(
        "ix_cs_verification_events_organisation_id",
        "community_service_verification_events",
        ["organisation_id"],
    )
    op.create_index(
        "ix_cs_verification_events_service_created",
        "community_service_verification_events",
        ["service_id", "created_at"],
    )
    op.execute(sa.text("ALTER TABLE community_service_verification_events ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE community_service_verification_events FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("community_service_verification_events")))


def downgrade() -> None:
    op.execute(
        sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON community_service_verification_events")
    )
    op.drop_table("community_service_verification_events")
    op.drop_index("ix_community_services_org_name_lower", table_name="community_services")
    op.drop_index("ix_community_services_org_category_status", table_name="community_services")
    op.drop_constraint("fk_community_services_verified_by_user_id", "community_services", type_="foreignkey")
    op.drop_constraint("fk_community_services_updated_by_user_id", "community_services", type_="foreignkey")
    op.drop_constraint("fk_community_services_created_by_user_id", "community_services", type_="foreignkey")
    op.drop_constraint("ck_community_services_clothing_service_type", "community_services", type_="check")
    op.drop_constraint("ck_community_services_verification_status", "community_services", type_="check")
    op.drop_column("community_services", "verified_by_user_id")
    op.drop_column("community_services", "updated_by_user_id")
    op.drop_column("community_services", "created_by_user_id")
    op.drop_column("community_services", "verified_at")
    op.drop_column("community_services", "verification_notes")
    op.drop_column("community_services", "information_source")
    op.drop_column("community_services", "verification_status")
    op.drop_column("community_services", "clothing_service_type")
    op.drop_column("community_services", "service_instructions")
    op.drop_column("community_services", "referral_requirements")
    op.drop_column("community_services", "opening_days")
