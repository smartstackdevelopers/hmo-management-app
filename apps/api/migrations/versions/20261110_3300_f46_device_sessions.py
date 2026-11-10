"""F4.6 mobile device sessions for remote sign-out.

Revises the F4.5 idempotency revision. Adds ``mobile_device_sessions`` with
organisation row-level security. The table records installation ids and
revocation state. It does not store biometric templates or access tokens.

A revoked or lost installation cannot be reactivated. The client generates a
new installation id after the next full Auth0 login.

Revision ID: 20261110_3300_f46
Revises: 20261110_3200_f45
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3300_f46"
down_revision: Union[str, None] = "20261110_3200_f45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_POLICY = """
CREATE POLICY hmore_org_isolation ON mobile_device_sessions
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
        "mobile_device_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("app_version", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "user_id",
            "installation_id",
            name="uq_mobile_device_sessions_user_installation",
        ),
        sa.CheckConstraint(
            "platform IN ('ios', 'android', 'web')",
            name="ck_mobile_device_sessions_platform",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'lost')",
            name="ck_mobile_device_sessions_status",
        ),
    )
    op.create_index(
        "ix_mobile_device_sessions_organisation_id",
        "mobile_device_sessions",
        ["organisation_id"],
    )
    op.create_index(
        "ix_mobile_device_sessions_user_id",
        "mobile_device_sessions",
        ["user_id"],
    )
    op.execute(sa.text("ALTER TABLE mobile_device_sessions ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE mobile_device_sessions FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_POLICY))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON mobile_device_sessions TO hmore_app"))


def downgrade() -> None:
    op.execute(sa.text("REVOKE SELECT, INSERT, UPDATE, DELETE ON mobile_device_sessions FROM hmore_app"))
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON mobile_device_sessions"))
    op.execute(sa.text("ALTER TABLE mobile_device_sessions NO FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE mobile_device_sessions DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_mobile_device_sessions_user_id", table_name="mobile_device_sessions")
    op.drop_index("ix_mobile_device_sessions_organisation_id", table_name="mobile_device_sessions")
    op.drop_table("mobile_device_sessions")
