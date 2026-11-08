"""F3.15 organisation AI feature flags and pilot enablement.

Safe migration strategy:
- Creates flag + history tables with RLS.
- Seeds existing organisations with enabled=true for previously generally-available
  AI features (preserves current access — does not silently revoke).
- Tenant Assistant is seeded enabled+pilot only when TENANT_ASSISTANT_PILOT_ORGANISATION_IDS
  lists the organisation; otherwise remains missing/disabled (fail closed).
- New organisations receive no automatic unrestricted enablement (application seed
  assigns disabled defaults).

Revision ID: 20261107_2800_f315
Revises: 20261107_2700_f314
"""

from __future__ import annotations

import os
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261107_2800_f315"
down_revision: Union[str, None] = "20261107_2700_f314"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Features that were already available org-wide before F3.15 (preserve access).
_PRESERVE_ENABLED = (
    "ai.agent.notes_analysis",
    "ai.workflow.case_summaries",
    "ai.workflow.document_checker",
    "ai.agent.support_planning",
    "ai.agent.housing_application",
    "ai.agent.compliance",
    "ai.agent.duplicate_detection",
    "ai.workflow.operational_search",
    "ai.workflow.report_draft",
    "ai.activity.transparency",
)


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


def _pilot_org_ids() -> list[str]:
    raw = (os.environ.get("TENANT_ASSISTANT_PILOT_ORGANISATION_IDS") or "").strip()
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.append(part)
    return out


def upgrade() -> None:
    op.create_table(
        "organisation_ai_feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_id", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pilot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organisation_id", "feature_id", name="uq_org_ai_feature_flags_org_feature"),
    )
    op.create_index("ix_org_ai_feature_flags_org", "organisation_ai_feature_flags", ["organisation_id"])
    op.create_index("ix_org_ai_feature_flags_feature", "organisation_ai_feature_flags", ["feature_id"])
    op.create_index(
        "ix_org_ai_feature_flags_org_enabled",
        "organisation_ai_feature_flags",
        ["organisation_id", "enabled"],
    )
    op.execute(sa.text("ALTER TABLE organisation_ai_feature_flags ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE organisation_ai_feature_flags FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("organisation_ai_feature_flags")))

    op.create_table(
        "organisation_ai_feature_flag_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_id", sa.String(100), nullable=False),
        sa.Column("flag_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_enabled", sa.Boolean(), nullable=True),
        sa.Column("previous_pilot_enabled", sa.Boolean(), nullable=True),
        sa.Column("new_enabled", sa.Boolean(), nullable=False),
        sa.Column("new_pilot_enabled", sa.Boolean(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("event_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["flag_id"], ["organisation_ai_feature_flags.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_org_ai_ff_history_org_feature",
        "organisation_ai_feature_flag_history",
        ["organisation_id", "feature_id", "created_at"],
    )
    op.create_index(
        "ix_org_ai_ff_history_org_created",
        "organisation_ai_feature_flag_history",
        ["organisation_id", "created_at"],
    )
    op.execute(sa.text("ALTER TABLE organisation_ai_feature_flag_history ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE organisation_ai_feature_flag_history FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy("organisation_ai_feature_flag_history")))

    # Preserve access for existing orgs (bypass RLS for seed).
    conn = op.get_bind()
    conn.execute(sa.text("SELECT set_config('app.rls_bypass', 'on', true)"))
    orgs = conn.execute(sa.text("SELECT id FROM organisations")).fetchall()
    pilot_ids = set(_pilot_org_ids())

    insert_flag = sa.text(
        """
        INSERT INTO organisation_ai_feature_flags
          (id, organisation_id, feature_id, enabled, pilot_enabled, change_reason, revision, metadata_json)
        VALUES
          (:id, :org_id, :feature_id, :enabled, :pilot, :reason, 1, '{}'::jsonb)
        ON CONFLICT (organisation_id, feature_id) DO NOTHING
        """
    )
    insert_hist = sa.text(
        """
        INSERT INTO organisation_ai_feature_flag_history
          (id, organisation_id, feature_id, flag_id, previous_enabled, previous_pilot_enabled,
           new_enabled, new_pilot_enabled, change_reason, action, revision)
        VALUES
          (:hid, :org_id, :feature_id, :flag_id, NULL, NULL, :enabled, :pilot, :reason, 'migration_seed', 1)
        """
    )

    for (org_id,) in orgs:
        for feature_id in _PRESERVE_ENABLED:
            flag_id = uuid.uuid4()
            conn.execute(
                insert_flag,
                {
                    "id": flag_id,
                    "org_id": org_id,
                    "feature_id": feature_id,
                    "enabled": True,
                    "pilot": False,
                    "reason": "f315_migration_preserve_existing_access",
                },
            )
            conn.execute(
                insert_hist,
                {
                    "hid": uuid.uuid4(),
                    "org_id": org_id,
                    "feature_id": feature_id,
                    "flag_id": flag_id,
                    "enabled": True,
                    "pilot": False,
                    "reason": "f315_migration_preserve_existing_access",
                },
            )

        # Tenant Assistant: only env-listed pilot orgs.
        org_str = str(org_id)
        if org_str in pilot_ids:
            flag_id = uuid.uuid4()
            conn.execute(
                insert_flag,
                {
                    "id": flag_id,
                    "org_id": org_id,
                    "feature_id": "ai.agent.tenant_assistant",
                    "enabled": True,
                    "pilot": True,
                    "reason": "f315_migration_from_tenant_assistant_env_allowlist",
                },
            )
            conn.execute(
                insert_hist,
                {
                    "hid": uuid.uuid4(),
                    "org_id": org_id,
                    "feature_id": "ai.agent.tenant_assistant",
                    "flag_id": flag_id,
                    "enabled": True,
                    "pilot": True,
                    "reason": "f315_migration_from_tenant_assistant_env_allowlist",
                },
            )


def downgrade() -> None:
    for table in (
        "organisation_ai_feature_flag_history",
        "organisation_ai_feature_flags",
    ):
        op.execute(sa.text(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}"))
        op.drop_table(table)
