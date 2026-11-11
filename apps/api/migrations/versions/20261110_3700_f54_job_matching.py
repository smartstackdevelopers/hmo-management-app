"""F5.4 AI job matching: listings, matches, saved items, preferences, training.

No seeded fake jobs. External sources hydrate listings when credentials exist.

Revision ID: 20261110_3700_f54
Revises: 20261110_3600_f53
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3700_f54"
down_revision: Union[str, None] = "20261110_3600_f53"
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
        "job_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("source_name", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("employer_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("employment_type", sa.String(64), nullable=True),
        sa.Column("salary_text", sa.String(255), nullable=True),
        sa.Column("required_skills_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("required_qualifications_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("experience_requirements", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("search_document", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "source_name", "external_id", name="uq_job_listings_org_source_ext"),
    )
    op.create_index("ix_job_listings_org_active", "job_listings", ["organisation_id", "is_active"])
    op.create_index("ix_job_listings_org_title", "job_listings", ["organisation_id", "title"])
    op.execute(
        sa.text(
            "CREATE INDEX ix_job_listings_search_trgm ON job_listings "
            "USING gin (to_tsvector('english', coalesce(search_document, '')))"
        )
    )
    _enable_rls("job_listings")

    op.create_table(
        "training_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("provider_name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("eligibility", sa.Text(), nullable=True),
        sa.Column("duration", sa.String(255), nullable=True),
        sa.Column("cost_text", sa.String(255), nullable=True),
        sa.Column("is_free_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source_name", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("related_skills_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_training_opportunities_verification",
        ),
        sa.UniqueConstraint("organisation_id", "source_name", "external_id", name="uq_training_org_source_ext"),
    )
    op.create_index("ix_training_opportunities_org_active", "training_opportunities", ["organisation_id", "is_active"])
    _enable_rls("training_opportunities")

    op.create_table(
        "tenant_job_match_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preferred_categories_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_locations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_employment_types_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_experience_levels_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("career_interests_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_hours", sa.String(64), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("selected_cv_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_cv_id"], ["tenant_cvs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_job_match_preferences_tenant"),
    )
    op.create_index("ix_tenant_job_match_preferences_org", "tenant_job_match_preferences", ["organisation_id"])
    _enable_rls("tenant_job_match_preferences")

    op.create_table(
        "tenant_job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("matching_skills_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("missing_skills_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("cv_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cv_id"], ["tenant_cvs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "job_id", name="uq_tenant_job_matches_tenant_job"),
    )
    op.create_index("ix_tenant_job_matches_org_tenant", "tenant_job_matches", ["organisation_id", "tenant_id"])
    _enable_rls("tenant_job_matches")

    op.create_table(
        "tenant_saved_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job_listings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "job_id", name="uq_tenant_saved_jobs_tenant_job"),
    )
    op.create_index("ix_tenant_saved_jobs_org_tenant", "tenant_saved_jobs", ["organisation_id", "tenant_id"])
    _enable_rls("tenant_saved_jobs")

    op.create_table(
        "tenant_saved_training",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("training_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="saved"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["training_id"], ["training_opportunities.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('saved', 'in_progress', 'completed')", name="ck_tenant_saved_training_status"),
        sa.UniqueConstraint("tenant_id", "training_id", name="uq_tenant_saved_training_tenant_training"),
    )
    op.create_index("ix_tenant_saved_training_org_tenant", "tenant_saved_training", ["organisation_id", "tenant_id"])
    _enable_rls("tenant_saved_training")


def downgrade() -> None:
    for table in (
        "tenant_saved_training",
        "tenant_saved_jobs",
        "tenant_job_matches",
        "tenant_job_match_preferences",
        "training_opportunities",
        "job_listings",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
