"""F7.4 performance benchmark runs and audit query index.

Revision ID: 20261112_4800_f74
Revises: 20261112_4700_f73
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261112_4800_f74"
down_revision: Union[str, None] = "20261112_4700_f73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "performance_benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment_label", sa.String(64), nullable=False, server_default="ci"),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_count_per_journey", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("concurrent_health_users", sa.Integer(), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_perf_runs_started", "performance_benchmark_runs", ["started_at"])

    op.create_table(
        "performance_journey_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("benchmark_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_key", sa.String(64), nullable=False),
        sa.Column("category", sa.String(8), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p50_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p95_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p99_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status_codes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["benchmark_run_id"], ["performance_benchmark_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_perf_journey_run", "performance_journey_results", ["benchmark_run_id", "journey_key"])

    op.create_index(
        "ix_audit_events_org_created_at",
        "audit_events",
        ["organisation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_org_created_at", table_name="audit_events")
    op.drop_table("performance_journey_results")
    op.drop_table("performance_benchmark_runs")
