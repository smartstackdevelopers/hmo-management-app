"""F8.1 optional AI voice calling add-on tables.

Revision ID: 20261113_4900_f81
Revises: 20261112_4800_f74
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261113_4900_f81"
down_revision: Union[str, None] = "20261112_4800_f74"
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


def _enable_rls(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy(table)))


def upgrade() -> None:
    op.create_table(
        "organisation_voice_calling_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("provider_mode", sa.String(32), nullable=False, server_default="test"),
        sa.Column("calling_hours", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("supported_languages", postgresql.JSONB(), nullable=False, server_default=sa.text("'[\"en-GB\"]'::jsonb")),
        sa.Column("voice_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("max_call_duration_seconds", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("monthly_call_limit", sa.Integer(), nullable=True),
        sa.Column("monthly_minutes_limit", sa.Integer(), nullable=True),
        sa.Column("consent_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("recording_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("privacy_review_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("handover_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("provider_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", name="uq_voice_calling_settings_org"),
        sa.CheckConstraint(
            "provider_mode IN ('test', 'twilio', 'pending_approval')",
            name="ck_voice_calling_provider_mode",
        ),
    )
    op.create_table(
        "voice_call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ringing"),
        sa.Column("provider_call_id", sa.String(128), nullable=True),
        sa.Column("caller_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("caller_role", sa.String(64), nullable=True),
        sa.Column("language", sa.String(16), nullable=False, server_default="en-GB"),
        sa.Column("consent_obtained", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_disclosure_played", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("handover_status", sa.String(32), nullable=False, server_default="none"),
        sa.Column("handover_reason", sa.String(64), nullable=True),
        sa.Column("handover_assignee_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("ai_turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("session_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["caller_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["handover_assignee_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("direction IN ('incoming', 'outgoing')", name="ck_voice_call_direction"),
    )
    op.create_index("ix_voice_call_sessions_org_started", "voice_call_sessions", ["organisation_id", "started_at"])
    op.create_table(
        "voice_call_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("user_text_summary", sa.Text(), nullable=True),
        sa.Column("assistant_text", sa.Text(), nullable=True),
        sa.Column("stt_provider", sa.String(32), nullable=False, server_default="test"),
        sa.Column("tts_provider", sa.String(32), nullable=False, server_default="test"),
        sa.Column("ai_request_id", sa.String(128), nullable=True),
        sa.Column("handover_suggested", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["voice_call_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "turn_index", name="uq_voice_call_turn_session_idx"),
    )
    _enable_rls("organisation_voice_calling_settings")
    _enable_rls("voice_call_sessions")
    _enable_rls("voice_call_turns")


def downgrade() -> None:
    op.drop_table("voice_call_turns")
    op.drop_table("voice_call_sessions")
    op.drop_table("organisation_voice_calling_settings")
