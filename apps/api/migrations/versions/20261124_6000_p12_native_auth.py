"""Prompt 12 native authentication tables and user account fields.

Revision ID: 20261124_6000_p12
Revises: 20261123_5900_f812
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261124_6000_p12"
down_revision: Union[str, None] = "20261123_5900_f812"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

account_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "suspended",
    "disabled",
    name="account_status",
    create_type=False,
)
registration_request_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "cancelled",
    name="registration_request_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE account_status AS ENUM "
            "('pending','approved','rejected','suspended','disabled'); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE registration_request_status AS ENUM "
            "('pending','approved','rejected','cancelled'); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
    )

    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "account_status",
            account_status,
            nullable=False,
            server_default="approved",
        ),
    )
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "registration_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_role", postgresql.ENUM(name="hmore_role", create_type=False), nullable=False),
        sa.Column(
            "status",
            registration_request_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("invitation_code", sa.String(64), nullable=True),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("privacy_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "decided_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_registration_requests_user_id", "registration_requests", ["user_id"])
    op.create_index("ix_registration_requests_organisation_id", "registration_requests", ["organisation_id"])

    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_hash", sa.String(128), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_auth_refresh_tokens_user_id", "auth_refresh_tokens", ["user_id"])
    op.create_index("ix_auth_refresh_tokens_expires_at", "auth_refresh_tokens", ["expires_at"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "auth_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipient_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "registration_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("registration_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="registration"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_auth_notifications_recipient_user_id", "auth_notifications", ["recipient_user_id"])

    op.create_table(
        "auth_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "subject_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "registration_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("registration_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_auth_audit_events_created_at", "auth_audit_events", ["created_at"])
    op.create_index("ix_auth_audit_events_event_type", "auth_audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("auth_audit_events")
    op.drop_table("auth_notifications")
    op.drop_table("password_reset_tokens")
    op.drop_table("auth_refresh_tokens")
    op.drop_table("registration_requests")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "account_status")
    op.drop_column("users", "password_hash")
    op.execute(sa.text("DROP TYPE IF EXISTS registration_request_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS account_status"))
