"""F1.2 initial Phase 1 PostgreSQL schema with pgvector readiness.

Revision ID: 20261105_1200_f12
Revises:
Create Date: 2026-11-05 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261105_1200_f12"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

hmore_role = postgresql.ENUM(
    "super_admin",
    "organisation_admin",
    "landlord",
    "tenant",
    "support_worker",
    "maintenance_contractor",
    name="hmore_role",
    create_type=False,
)
membership_status = postgresql.ENUM(
    "active",
    "invited",
    "suspended",
    name="membership_status",
    create_type=False,
)
record_status = postgresql.ENUM(
    "active",
    "archived",
    name="record_status",
    create_type=False,
)


def upgrade() -> None:
    # Extension only. No embedding tables in F1.2.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    hmore_role.create(op.get_bind(), checkfirst=True)
    membership_status.create(op.get_bind(), checkfirst=True)
    record_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organisations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            record_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_organisations_slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "external_subject",
            sa.String(length=255),
            nullable=True,
            comment="Stable subject from the managed identity provider when F1.3 lands.",
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("external_subject", name="uq_users_external_subject"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "organisation_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", hmore_role, nullable=False),
        sa.Column(
            "status",
            membership_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_memberships_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memberships_user_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(role = 'super_admin' AND organisation_id IS NULL) "
            "OR (role <> 'super_admin' AND organisation_id IS NOT NULL)",
            name="ck_membership_super_admin_org_scope",
        ),
        sa.UniqueConstraint(
            "user_id",
            "organisation_id",
            name="uq_membership_user_organisation",
        ),
    )
    op.create_index(
        "ix_organisation_memberships_user_id",
        "organisation_memberships",
        ["user_id"],
    )
    op.create_index(
        "ix_organisation_memberships_organisation_id",
        "organisation_memberships",
        ["organisation_id"],
    )
    op.create_index(
        "ix_memberships_organisation_role",
        "organisation_memberships",
        ["organisation_id", "role"],
    )
    op.create_index(
        "uq_membership_one_super_admin_per_user",
        "organisation_memberships",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("role = 'super_admin'"),
    )

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preferred_name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            record_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_tenants_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_tenants_user_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_tenants_organisation_id", "tenants", ["organisation_id"])
    op.create_index("ix_tenants_user_id", "tenants", ["user_id"])

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("postcode", sa.String(length=20), nullable=False),
        sa.Column(
            "country_code",
            sa.String(length=2),
            nullable=False,
            server_default="GB",
        ),
        sa.Column("landlord_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            record_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_properties_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["landlord_user_id"],
            ["users.id"],
            name="fk_properties_landlord_user_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_properties_organisation_id", "properties", ["organisation_id"])
    op.create_index("ix_properties_landlord_user_id", "properties", ["landlord_user_id"])

    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("floor_label", sa.String(length=50), nullable=True),
        sa.Column("max_occupancy", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            record_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_rooms_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name="fk_rooms_property_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("property_id", "label", name="uq_rooms_property_label"),
    )
    op.create_index("ix_rooms_organisation_id", "rooms", ["organisation_id"])
    op.create_index("ix_rooms_property_id", "rooms", ["property_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_audit_events_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_events_actor_user_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_audit_events_organisation_id", "audit_events", ["organisation_id"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    op.create_table(
        "emergency_access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_emergency_access_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_emergency_access_actor_user_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_emergency_access_grants_organisation_id",
        "emergency_access_grants",
        ["organisation_id"],
    )
    op.create_index(
        "ix_emergency_access_grants_actor_user_id",
        "emergency_access_grants",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_emergency_access_grants_expires_at",
        "emergency_access_grants",
        ["expires_at"],
    )

    op.create_table(
        "file_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=150), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_file_metadata_organisation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_file_metadata_uploaded_by_user_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("storage_key", name="uq_file_metadata_storage_key"),
    )
    op.create_index("ix_file_metadata_organisation_id", "file_metadata", ["organisation_id"])
    op.create_index(
        "ix_file_metadata_uploaded_by_user_id",
        "file_metadata",
        ["uploaded_by_user_id"],
    )


def downgrade() -> None:
    op.drop_table("file_metadata")
    op.drop_table("emergency_access_grants")
    op.drop_table("audit_events")
    op.drop_table("rooms")
    op.drop_table("properties")
    op.drop_table("tenants")
    op.drop_table("organisation_memberships")
    op.drop_table("users")
    op.drop_table("organisations")

    record_status.drop(op.get_bind(), checkfirst=True)
    membership_status.drop(op.get_bind(), checkfirst=True)
    hmore_role.drop(op.get_bind(), checkfirst=True)

    # Leave the vector extension installed. Dropping it can fail if another
    # database object depends on it and is not required to reverse the schema.
