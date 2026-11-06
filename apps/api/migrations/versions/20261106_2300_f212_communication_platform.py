"""F2.12 communication platform: messaging, deliveries, announcements, templates, preferences, RLS.

Revision ID: 20261106_2300_f212
Revises: 20261106_2200_f211
Create Date: 2026-11-06 23:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261106_2300_f212"
down_revision: Union[str, None] = "20261106_2200_f211"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "communication_templates",
    "communication_user_preferences",
    "communication_messages",
    "communication_message_recipients",
    "communication_announcements",
    "communication_announcement_recipients",
    "communication_deliveries",
    "communication_translations",
    "communication_scheduled_reminders",
)

POLICY_SQL = """
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
    # Align F2.2 reminder channel with F2.12 delivery channels (legacy rows used "log").
    op.execute("UPDATE reminder_records SET channel = 'in_app' WHERE channel = 'log'")
    op.alter_column(
        "reminder_records",
        "channel",
        existing_type=sa.String(length=32),
        server_default=sa.text("'in_app'"),
    )

    op.create_table(
        "communication_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("allowed_placeholders", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "code", name="uq_comm_templates_org_code"),
    )
    op.create_index("ix_comm_templates_org", "communication_templates", ["organisation_id"])

    op.create_table(
        "communication_user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allow_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_sms", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("marketing_opt_out", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sms_suppressed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "user_id", name="uq_comm_prefs_org_user"),
    )
    op.create_index("ix_comm_prefs_user", "communication_user_preferences", ["user_id"])

    op.create_table(
        "communication_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(32), nullable=False, server_default="direct"),
        sa.Column("related_resource_type", sa.String(64), nullable=True),
        sa.Column("related_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "message_type IN ('direct', 'thread_reply', 'system')",
            name="ck_comm_messages_type",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_comm_messages_org_conv", "communication_messages", ["organisation_id", "conversation_id"]
    )
    op.create_index(
        "ix_comm_messages_sender", "communication_messages", ["organisation_id", "sender_user_id"]
    )

    op.create_table(
        "communication_message_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["communication_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("message_id", "recipient_user_id", name="uq_comm_msg_recipient"),
    )
    op.create_index(
        "ix_comm_msg_recipient_inbox",
        "communication_message_recipients",
        ["organisation_id", "recipient_user_id", "read_at"],
    )

    op.create_table(
        "communication_announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("audience", sa.String(64), nullable=False),
        sa.Column("audience_user_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("channels", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'cancelled', 'expired')",
            name="ck_comm_ann_status",
        ),
        sa.CheckConstraint(
            "priority IN ('normal', 'high', 'emergency')",
            name="ck_comm_ann_priority",
        ),
        sa.CheckConstraint(
            "audience IN ("
            "'organisation_all', 'staff_only', 'tenants_only', 'landlords_only', 'custom_users'"
            ")",
            name="ck_comm_ann_audience",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_comm_ann_org_ref"),
    )

    op.create_table(
        "communication_announcement_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("announcement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("in_app_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["announcement_id"], ["communication_announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_comm_ann_user"),
    )
    op.create_index(
        "ix_comm_ann_user",
        "communication_announcement_recipients",
        ["organisation_id", "user_id"],
    )

    op.create_table(
        "communication_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_name", sa.String(64), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "channel IN ('in_app', 'email', 'sms')",
            name="ck_comm_del_channel",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'created', 'queued', 'attempted', 'provider_accepted', 'delivered', "
            "'failed', 'retrying', 'cancelled'"
            ")",
            name="ck_comm_del_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "idempotency_key", name="uq_comm_del_idempotency"),
    )
    op.create_index(
        "ix_comm_del_pending",
        "communication_deliveries",
        ["organisation_id", "status", "scheduled_at"],
    )

    op.create_table(
        "communication_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_field", sa.String(32), nullable=False),
        sa.Column("source_language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("target_language", sa.String(16), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("provider_name", sa.String(64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'reviewed')",
            name="ck_comm_trn_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "target_type", "target_id", "target_field", "target_language", name="uq_comm_trn_target_lang"
        ),
    )

    op.create_table(
        "communication_scheduled_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reminder_kind", sa.String(64), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'cancelled', 'failed')",
            name="ck_comm_sch_rem_status",
        ),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "idempotency_key", name="uq_comm_sch_rem_idempotency"),
    )
    op.create_index(
        "ix_comm_sch_rem_due",
        "communication_scheduled_reminders",
        ["organisation_id", "scheduled_at", "status"],
    )

    for table in ORG_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(POLICY_SQL.format(table=table))
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO hmore_app")


def downgrade() -> None:
    for table in reversed(ORG_TABLES):
        op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON {table} FROM hmore_app")
        op.execute(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("communication_scheduled_reminders")
    op.drop_table("communication_translations")
    op.drop_table("communication_deliveries")
    op.drop_table("communication_announcement_recipients")
    op.drop_table("communication_announcements")
    op.drop_table("communication_message_recipients")
    op.drop_table("communication_messages")
    op.drop_table("communication_user_preferences")
    op.drop_table("communication_templates")
