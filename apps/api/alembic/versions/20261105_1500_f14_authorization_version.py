"""F1.4 add users.authorization_version for stale role/session detection.

Revision ID: 20261105_1500_f14
Revises: 20261105_1200_f12
Create Date: 2026-11-05 15:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_1500_f14"
down_revision: Union[str, None] = "20261105_1200_f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "authorization_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Incremented when role memberships change so clients refresh authz state.",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "authorization_version")
