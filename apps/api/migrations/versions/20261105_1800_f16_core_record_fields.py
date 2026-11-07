"""F1.6 extend tenant and room baseline fields for CRUD.

Revision ID: 20261105_1800_f16
Revises: 20261105_1700_f15
Create Date: 2026-11-05 18:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_1800_f16"
down_revision: Union[str, None] = "20261105_1700_f15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("tenancy_reference", sa.String(length=100), nullable=True))
    op.add_column("tenants", sa.Column("consent_notes", sa.Text(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tenants", sa.Column("preferences", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("needs_goals", sa.Text(), nullable=True))
    op.create_index("ix_tenants_tenancy_reference", "tenants", ["tenancy_reference"])

    op.add_column("rooms", sa.Column("room_type", sa.String(length=100), nullable=True))
    op.add_column("rooms", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rooms", "notes")
    op.drop_column("rooms", "room_type")
    op.drop_index("ix_tenants_tenancy_reference", table_name="tenants")
    op.drop_column("tenants", "needs_goals")
    op.drop_column("tenants", "preferences")
    op.drop_column("tenants", "consent_given_at")
    op.drop_column("tenants", "consent_notes")
    op.drop_column("tenants", "tenancy_reference")
