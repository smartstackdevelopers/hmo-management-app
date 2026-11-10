"""F4.3 push devices and push as a communication delivery channel.

Revises the F4.1 tenant-mobile revision. Does not change tenant catalogue
tables. Adds push_device_tokens, allow_push on communication preferences,
and allows channel ``push`` on communication_deliveries.

``sending`` and ``sent`` are push-only delivery statuses. ``sent`` means the
Expo ticket status was ok. It does not mean a handset displayed the notification.

Revision ID: 20261110_3000_f43
Revises: 20261110_2900_f41
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3000_f43"
down_revision: Union[str, None] = "20261110_2900_f41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_POLICY = """
CREATE POLICY hmore_org_isolation ON push_device_tokens
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

_CHANNEL_WITH_PUSH = "channel IN ('in_app', 'email', 'sms', 'push')"
_CHANNEL_BEFORE = "channel IN ('in_app', 'email', 'sms')"
_STATUS_WITH_PUSH = (
    "status IN ("
    "'created', 'queued', 'sending', 'sent', 'attempted', 'provider_accepted', 'delivered', "
    "'failed', 'retrying', 'cancelled'"
    ")"
)
_STATUS_BEFORE = (
    "status IN ("
    "'created', 'queued', 'attempted', 'provider_accepted', 'delivered', "
    "'failed', 'retrying', 'cancelled'"
    ")"
)


def upgrade() -> None:
    op.create_table(
        "push_device_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expo_push_token", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("app_version", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("disabled_reason", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "platform IN ('ios', 'android', 'web')",
            name="ck_push_device_tokens_platform",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("expo_push_token", name="uq_push_device_tokens_expo_token"),
    )
    op.create_index("ix_push_device_tokens_organisation_id", "push_device_tokens", ["organisation_id"])
    op.create_index(
        "ix_push_device_tokens_org_user_active",
        "push_device_tokens",
        ["organisation_id", "user_id", "is_active"],
    )
    op.execute(sa.text("ALTER TABLE push_device_tokens ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE push_device_tokens FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_POLICY))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON push_device_tokens TO hmore_app"))

    op.add_column(
        "communication_user_preferences",
        sa.Column("allow_push", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.drop_constraint("ck_comm_del_channel", "communication_deliveries", type_="check")
    op.create_check_constraint("ck_comm_del_channel", "communication_deliveries", _CHANNEL_WITH_PUSH)
    op.drop_constraint("ck_comm_del_status", "communication_deliveries", type_="check")
    op.create_check_constraint("ck_comm_del_status", "communication_deliveries", _STATUS_WITH_PUSH)


def downgrade() -> None:
    op.drop_constraint("ck_comm_del_status", "communication_deliveries", type_="check")
    op.create_check_constraint("ck_comm_del_status", "communication_deliveries", _STATUS_BEFORE)
    op.drop_constraint("ck_comm_del_channel", "communication_deliveries", type_="check")
    op.create_check_constraint("ck_comm_del_channel", "communication_deliveries", _CHANNEL_BEFORE)
    op.drop_column("communication_user_preferences", "allow_push")

    op.execute(sa.text("REVOKE SELECT, INSERT, UPDATE, DELETE ON push_device_tokens FROM hmore_app"))
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON push_device_tokens"))
    op.execute(sa.text("ALTER TABLE push_device_tokens NO FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE push_device_tokens DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_push_device_tokens_org_user_active", table_name="push_device_tokens")
    op.drop_index("ix_push_device_tokens_organisation_id", table_name="push_device_tokens")
    op.drop_table("push_device_tokens")
