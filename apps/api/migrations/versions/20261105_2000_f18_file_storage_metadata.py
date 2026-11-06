"""F1.8 extend file_metadata for private storage lifecycle fields.

Revision ID: 20261105_2000_f18
Revises: 20261105_1900_f17
Create Date: 2026-11-05 20:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_2000_f18"
down_revision: Union[str, None] = "20261105_1900_f17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_metadata",
        sa.Column(
            "storage_provider",
            sa.String(length=32),
            nullable=False,
            server_default="memory",
        ),
    )
    op.add_column(
        "file_metadata",
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "file_metadata",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "file_metadata",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_file_metadata_status", "file_metadata", ["status"])


def downgrade() -> None:
    op.drop_index("ix_file_metadata_status", table_name="file_metadata")
    op.drop_column("file_metadata", "deleted_at")
    op.drop_column("file_metadata", "status")
    op.drop_column("file_metadata", "checksum_sha256")
    op.drop_column("file_metadata", "storage_provider")
