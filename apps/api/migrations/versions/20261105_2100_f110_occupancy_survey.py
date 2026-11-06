"""F1.10 occupancy site-survey tables with organisation RLS.

Revision ID: 20261105_2100_f110
Revises: 20261105_2000_f18
Create Date: 2026-11-05 21:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261105_2100_f110"
down_revision: Union[str, None] = "20261105_2000_f18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_TABLES = (
    "occupancy_site_surveys",
    "occupancy_survey_room_assessments",
    "occupancy_survey_findings",
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
    op.create_table(
        "occupancy_site_surveys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("survey_date", sa.Date(), nullable=True),
        sa.Column("surveyor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("surveyor_display_name", sa.String(length=255), nullable=True),
        sa.Column("site_contact_notes", sa.Text(), nullable=True),
        sa.Column("building_assessment", postgresql.JSONB(), nullable=True),
        sa.Column("facilities_assessment", postgresql.JSONB(), nullable=True),
        sa.Column("health_safety_assessment", postgresql.JSONB(), nullable=True),
        sa.Column("accessibility_assessment", postgresql.JSONB(), nullable=True),
        sa.Column("camera_feasibility_notes", postgresql.JSONB(), nullable=True),
        sa.Column("feasibility_status", sa.String(length=64), nullable=True),
        sa.Column("feasibility_summary", sa.Text(), nullable=True),
        sa.Column("missing_information", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["organisation_id"], ["organisations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["surveyor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_occupancy_site_surveys_organisation_id",
        "occupancy_site_surveys",
        ["organisation_id"],
    )
    op.create_index(
        "ix_occupancy_site_surveys_property_id", "occupancy_site_surveys", ["property_id"]
    )
    op.create_index("ix_occupancy_site_surveys_status", "occupancy_site_surveys", ["status"])
    op.create_index(
        "ix_occupancy_site_surveys_feasibility_status",
        "occupancy_site_surveys",
        ["feasibility_status"],
    )

    op.create_table(
        "occupancy_survey_room_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("room_label", sa.String(length=100), nullable=False),
        sa.Column("assessment", postgresql.JSONB(), nullable=False),
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
            ["organisation_id"], ["organisations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"], ["occupancy_site_surveys.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_occupancy_survey_room_assessments_organisation_id",
        "occupancy_survey_room_assessments",
        ["organisation_id"],
    )
    op.create_index(
        "ix_occupancy_survey_room_assessments_survey_id",
        "occupancy_survey_room_assessments",
        ["survey_id"],
    )
    op.create_index(
        "ix_occupancy_survey_room_assessments_room_id",
        "occupancy_survey_room_assessments",
        ["room_id"],
    )

    op.create_table(
        "occupancy_survey_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("related_room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("responsible_notes", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("evidence_file_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["organisation_id"], ["organisations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"], ["occupancy_site_surveys.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["related_room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"], ["file_metadata.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_occupancy_survey_findings_organisation_id",
        "occupancy_survey_findings",
        ["organisation_id"],
    )
    op.create_index(
        "ix_occupancy_survey_findings_survey_id", "occupancy_survey_findings", ["survey_id"]
    )
    op.create_index(
        "ix_occupancy_survey_findings_category", "occupancy_survey_findings", ["category"]
    )
    op.create_index(
        "ix_occupancy_survey_findings_status", "occupancy_survey_findings", ["status"]
    )

    for table in ORG_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(POLICY_SQL.format(table=table))
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO hmore_app")


def downgrade() -> None:
    for table in reversed(ORG_TABLES):
        op.execute(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("occupancy_survey_findings")
    op.drop_table("occupancy_survey_room_assessments")
    op.drop_table("occupancy_site_surveys")
