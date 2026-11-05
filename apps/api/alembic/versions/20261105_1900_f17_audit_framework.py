"""F1.7 extend audit_events and emergency_access_grants for audit framework.

Revision ID: 20261105_1900_f17
Revises: 20261105_1800_f16
Create Date: 2026-11-05 19:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_1900_f17"
down_revision: Union[str, None] = "20261105_1800_f16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("actor_role", sa.String(length=64), nullable=True))
    op.add_column(
        "audit_events",
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="success"),
    )
    op.add_column(
        "audit_events", sa.Column("correlation_id", sa.String(length=100), nullable=True)
    )
    op.add_column("audit_events", sa.Column("source", sa.String(length=100), nullable=True))
    op.create_index("ix_audit_events_outcome", "audit_events", ["outcome"])
    op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])

    # Append-oriented: app role may insert/select but not update/delete audit rows.
    op.execute("REVOKE UPDATE, DELETE ON audit_events FROM hmore_app")
    op.execute("GRANT SELECT, INSERT ON audit_events TO hmore_app")

    # Organisation-scoped RLS for audit rows (null org = platform; visible with bypass only).
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY hmore_org_isolation ON audit_events
          FOR ALL
          USING (
            current_setting('app.rls_bypass', true) = 'on'
            OR (
              organisation_id IS NOT NULL
              AND organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
            )
          )
          WITH CHECK (
            current_setting('app.rls_bypass', true) = 'on'
            OR (
              organisation_id IS NOT NULL
              AND organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
            )
          );
        """
    )

    op.add_column(
        "emergency_access_grants",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="requested"),
    )
    op.add_column(
        "emergency_access_grants",
        sa.Column("resource_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "emergency_access_grants",
        sa.Column("resource_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "emergency_access_grants",
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "emergency_access_grants",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_emergency_access_approved_by_user_id",
        "emergency_access_grants",
        "users",
        ["approved_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_emergency_access_grants_status", "emergency_access_grants", ["status"])


def downgrade() -> None:
    op.drop_index("ix_emergency_access_grants_status", table_name="emergency_access_grants")
    op.drop_constraint(
        "fk_emergency_access_approved_by_user_id",
        "emergency_access_grants",
        type_="foreignkey",
    )
    op.drop_column("emergency_access_grants", "activated_at")
    op.drop_column("emergency_access_grants", "approved_by_user_id")
    op.drop_column("emergency_access_grants", "resource_id")
    op.drop_column("emergency_access_grants", "resource_type")
    op.drop_column("emergency_access_grants", "status")

    op.execute("DROP POLICY IF EXISTS hmore_org_isolation ON audit_events")
    op.execute("ALTER TABLE audit_events NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON audit_events TO hmore_app")

    op.drop_index("ix_audit_events_correlation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_type", table_name="audit_events")
    op.drop_index("ix_audit_events_outcome", table_name="audit_events")
    op.drop_column("audit_events", "source")
    op.drop_column("audit_events", "correlation_id")
    op.drop_column("audit_events", "outcome")
    op.drop_column("audit_events", "actor_role")
