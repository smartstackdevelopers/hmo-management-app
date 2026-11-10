"""F4.5 client idempotency keys for offline sync retries.

Revises the F4.3 push revision. Does not change daily logs, visits, tasks,
or maintenance tables. A repeated Idempotency-Key from the same user and
organisation returns the first successful response instead of inserting again.

``resource_id`` stays null only while the request transaction is still
running. The row is filled in before commit. A rollback removes the claim,
so a failed attempt does not block a later retry.

Revision ID: 20261110_3200_f45
Revises: 20261110_3000_f43
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_3200_f45"
down_revision: Union[str, None] = "20261110_3000_f43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_POLICY = """
CREATE POLICY hmore_org_isolation ON client_idempotency_keys
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
        "client_idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(128), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("response_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organisation_id",
            "user_id",
            "scope",
            "key",
            name="uq_client_idempotency_org_user_scope_key",
        ),
    )
    op.create_index(
        "ix_client_idempotency_keys_organisation_id",
        "client_idempotency_keys",
        ["organisation_id"],
    )
    op.execute(sa.text("ALTER TABLE client_idempotency_keys ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE client_idempotency_keys FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_POLICY))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON client_idempotency_keys TO hmore_app"))


def downgrade() -> None:
    op.execute(sa.text("REVOKE SELECT, INSERT, UPDATE, DELETE ON client_idempotency_keys FROM hmore_app"))
    op.execute(sa.text("DROP POLICY IF EXISTS hmore_org_isolation ON client_idempotency_keys"))
    op.execute(sa.text("ALTER TABLE client_idempotency_keys NO FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE client_idempotency_keys DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_client_idempotency_keys_organisation_id", table_name="client_idempotency_keys")
    op.drop_table("client_idempotency_keys")
