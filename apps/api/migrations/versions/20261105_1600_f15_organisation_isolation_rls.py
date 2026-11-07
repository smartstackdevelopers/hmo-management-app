"""F1.5 enable FORCE RLS on organisation-scoped business tables.

Revision ID: 20261105_1600_f15
Revises: 20261105_1500_f14
Create Date: 2026-11-05 16:00:00

Application code must SET LOCAL app.organisation_id or app.rls_bypass per
transaction. Table owners are still subject to policies via FORCE ROW LEVEL SECURITY.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20261105_1600_f15"
down_revision: Union[str, None] = "20261105_1500_f14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_SCOPED_TABLES = (
    "tenants",
    "properties",
    "rooms",
    "file_metadata",
    "emergency_access_grants",
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
    for table in ORG_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(POLICY_SQL.format(table=table))


def downgrade() -> None:
    for table in ORG_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS hmore_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
