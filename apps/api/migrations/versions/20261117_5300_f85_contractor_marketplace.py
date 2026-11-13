"""F8.5 optional contractor marketplace add-on.

Revision ID: 20261117_5300_f85
Revises: 20261116_5200_f84
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261117_5300_f85"
down_revision: Union[str, None] = "20261116_5200_f84"
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
        "organisation_contractor_marketplace_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("privacy_review_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("show_contact_to_landlords", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reminder_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", name="uq_contractor_marketplace_settings_org"),
    )
    op.create_table(
        "contractor_service_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "slug", name="uq_contractor_category_slug"),
    )
    op.create_table(
        "contractor_directory_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("business_description", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(64), nullable=True),
        sa.Column("service_category_slugs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("operating_locations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("service_coverage", sa.Text(), nullable=True),
        sa.Column("availability_notes", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("account_status", sa.String(32), nullable=False, server_default="inactive"),
        sa.Column("insurance_expiry", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contractor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "contractor_user_id", name="uq_contractor_profile_user"),
        sa.CheckConstraint(
            "verification_status IN ('draft', 'submitted', 'under_review', 'approved', 'rejected', 'suspended')",
            name="ck_contractor_verification_status",
        ),
        sa.CheckConstraint(
            "account_status IN ('inactive', 'active', 'suspended')",
            name="ck_contractor_account_status",
        ),
    )
    op.create_table(
        "contractor_verification_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["contractor_directory_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject', 'request_evidence', 'suspend')",
            name="ck_contractor_review_decision",
        ),
    )
    op.create_table(
        "contractor_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["contractor_directory_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["file_metadata.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "marketplace_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(32), nullable=False),
        sa.Column("maintenance_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("preferred_start_date", sa.Date(), nullable=True),
        sa.Column("quotations_requested", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("assigned_contractor_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maintenance_request_id"], ["maintenance_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_contractor_profile_id"], ["contractor_directory_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "reference_number", name="uq_marketplace_jobs_ref"),
        sa.CheckConstraint(
            "status IN ('draft', 'requested', 'quotation_pending', 'quotation_received', 'awaiting_approval', "
            "'assigned', 'in_progress', 'completed', 'verified', 'cancelled')",
            name="ck_marketplace_jobs_status",
        ),
    )
    op.create_table(
        "marketplace_quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quotation_reference", sa.String(64), nullable=False),
        sa.Column("labour_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("material_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("additional_charges", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("proposed_start_date", sa.Date(), nullable=True),
        sa.Column("estimated_completion_date", sa.Date(), nullable=True),
        sa.Column("work_description", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["marketplace_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contractor_profile_id"], ["contractor_directory_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organisation_id", "quotation_reference", name="uq_marketplace_quotation_ref"),
        sa.CheckConstraint(
            "status IN ('submitted', 'under_review', 'approved', 'rejected', 'withdrawn')",
            name="ck_marketplace_quotation_status",
        ),
    )
    op.create_table(
        "marketplace_job_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("materials_used", sa.Text(), nullable=True),
        sa.Column("outstanding_work", sa.Text(), nullable=True),
        sa.Column("contractor_declaration", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="awaiting_review"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["marketplace_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "review_status IN ('awaiting_review', 'approved', 'rejected', 'additional_work_required')",
            name="ck_marketplace_completion_review",
        ),
    )
    op.create_table(
        "marketplace_contractor_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_quality", sa.Integer(), nullable=True),
        sa.Column("timeliness", sa.Integer(), nullable=True),
        sa.Column("communication", sa.Integer(), nullable=True),
        sa.Column("professional_conduct", sa.Integer(), nullable=True),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("moderation_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["marketplace_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "moderation_status IN ('pending', 'published', 'disputed', 'retracted')",
            name="ck_marketplace_feedback_moderation",
        ),
    )
    tables = (
        "organisation_contractor_marketplace_settings",
        "contractor_service_categories",
        "contractor_directory_profiles",
        "contractor_verification_reviews",
        "contractor_documents",
        "marketplace_jobs",
        "marketplace_quotations",
        "marketplace_job_completions",
        "marketplace_contractor_feedback",
    )
    for table in tables:
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("marketplace_contractor_feedback")
    op.drop_table("marketplace_job_completions")
    op.drop_table("marketplace_quotations")
    op.drop_table("marketplace_jobs")
    op.drop_table("contractor_documents")
    op.drop_table("contractor_verification_reviews")
    op.drop_table("contractor_directory_profiles")
    op.drop_table("contractor_service_categories")
    op.drop_table("organisation_contractor_marketplace_settings")
