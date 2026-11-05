from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FileMetadata(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Metadata for private object storage. Bytes are not stored in PostgreSQL."""

    __tablename__ = "file_metadata"

    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    storage_provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="memory",
        server_default="memory",
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
