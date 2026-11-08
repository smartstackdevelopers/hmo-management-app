"""F3.14 AI activity logs, confidence/sources metadata, wrong-answer feedback.

Revision ID: 20261107_2700_f314
Revises: 20261107_2600_f313
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2700_f314"
down_revision: Union[str, None] = "20261107_2600_f313"
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
    op.create_table(
        "ai_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("usage_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("initiating_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feature_id", sa.String(100), nullable=False),
        sa.Column("workflow_id", sa.String(100), nullable=False),
        sa.Column("agent_name", sa.String(128), nullable=False),
        sa.Column("operation_type", sa.String(64), nullable=False, server_default="ai_operation"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_status", sa.String(32), nullable=False),
        sa.Column("prompt_id", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("routing_info_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("cost_status", sa.String(32), nullable=True),
        sa.Column("source_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("sources_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("output_ref_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("human_approval_status", sa.String(32), nullable=False, server_default="not_applicable"),
        sa.Column("error_category", sa.String(64), nullable=True),
        sa.Column("confidence_kind", sa.String(64), nullable=False, server_default="unavailable"),
        sa.Column(
            "confidence_label",
            sa.String(255),
            nullable=False,
            server_default="Confidence unavailable",
        ),
        sa.Column(
            "confidence_detail_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("visibility", sa.String(32), nullable=False, server_default="staff"),
        sa.Column("metadata_safe_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usage_record_id"], ["ai_usage_records.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("request_id", name="uq_ai_activity_logs_request_id"),
        sa.CheckConstraint(
            "execution_status IN ('completed','failed','rejected_budget','cancelled','started')",
            name="ck_ai_activity_execution_status",
        ),
        sa.CheckConstraint(
            "confidence_kind IN ("
            "'unavailable','retrieval_coverage','deterministic_validation',"
            "'human_reviewed','model_reported')",
            name="ck_ai_activity_confidence_kind",
        ),
        sa.CheckConstraint(
            "visibility IN ('staff','initiator')",
            name="ck_ai_activity_visibility",
        ),
        sa.CheckConstraint(
            "human_approval_status IN ("
            "'not_applicable','pending','approved','rejected','unknown')",
            name="ck_ai_activity_human_approval",
        ),
    )
    op.create_index(
        "ix_ai_activity_org_created", "ai_activity_logs", ["organisation_id", "created_at"]
    )
    op.create_index(
        "ix_ai_activity_org_feature", "ai_activity_logs", ["organisation_id", "feature_id"]
    )
    op.create_index(
        "ix_ai_activity_org_status", "ai_activity_logs", ["organisation_id", "execution_status"]
    )
    op.create_index(
        "ix_ai_activity_org_user", "ai_activity_logs", ["organisation_id", "initiating_user_id"]
    )
    op.create_index(
        "ix_ai_activity_org_visibility", "ai_activity_logs", ["organisation_id", "visibility"]
    )
    op.execute(sa.text("ALTER TABLE ai_activity_logs ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE ai_activity_logs FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("ai_activity_logs")))

    op.create_table(
        "ai_wrong_answer_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporting_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("assigned_reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["activity_id"], ["ai_activity_logs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporting_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "category IN ("
            "'incorrect_information','incomplete_answer','misleading_answer',"
            "'unsupported_claim','missing_source','outdated_information','other')",
            name="ck_ai_feedback_category",
        ),
        sa.CheckConstraint(
            "review_status IN ('submitted','under_review','resolved','rejected')",
            name="ck_ai_feedback_review_status",
        ),
    )
    op.create_index(
        "ix_ai_feedback_org_status",
        "ai_wrong_answer_feedback",
        ["organisation_id", "review_status"],
    )
    op.create_index(
        "ix_ai_feedback_org_activity",
        "ai_wrong_answer_feedback",
        ["organisation_id", "activity_id"],
    )
    op.create_index(
        "ix_ai_feedback_org_created",
        "ai_wrong_answer_feedback",
        ["organisation_id", "created_at"],
    )
    op.create_index(
        "ix_ai_feedback_org_category",
        "ai_wrong_answer_feedback",
        ["organisation_id", "category"],
    )
    op.execute(sa.text("ALTER TABLE ai_wrong_answer_feedback ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE ai_wrong_answer_feedback FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("ai_wrong_answer_feedback")))

    op.create_table(
        "ai_feedback_review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("event_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["feedback_id"], ["ai_wrong_answer_feedback.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_ai_feedback_events_feedback",
        "ai_feedback_review_events",
        ["feedback_id", "created_at"],
    )
    op.create_index(
        "ix_ai_feedback_events_org",
        "ai_feedback_review_events",
        ["organisation_id", "created_at"],
    )
    op.execute(sa.text("ALTER TABLE ai_feedback_review_events ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE ai_feedback_review_events FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("ai_feedback_review_events")))


def downgrade() -> None:
    for table in (
        "ai_feedback_review_events",
        "ai_wrong_answer_feedback",
        "ai_activity_logs",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
