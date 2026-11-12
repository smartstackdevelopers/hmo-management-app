"""F6.4 Integration Hub foundation models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Integration(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "provider_key",
            name="uq_integrations_org_provider",
        ),
        Index("ix_integrations_org_category", "organisation_id", "category"),
        Index("ix_integrations_org_status", "organisation_id", "connection_status"),
        CheckConstraint(
            "category IN ('council', 'hr', 'finance', 'community_service')",
            name="ck_integrations_category",
        ),
        CheckConstraint(
            "auth_type IN ('api_key', 'bearer', 'oauth2', 'none')",
            name="ck_integrations_auth_type",
        ),
        CheckConstraint(
            "connection_status IN ("
            "'not_configured', 'configured', 'connected', 'failed', 'disabled'"
            ")",
            name="ck_integrations_connection_status",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str] = mapped_column(String(32), nullable=False, default="api_key")
    # Non-secret config (scopes, timeout, oauth client_id only — never client_secret here)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Fernet ciphertext for secrets blob (api_key / bearer / oauth client_secret / refresh)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    credentials_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_configured")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_connection_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IntegrationFieldMapping(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "integration_field_mappings"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "integration_id",
            "version",
            name="uq_integration_field_mappings_version",
        ),
        CheckConstraint("version >= 1", name="ck_integration_field_mappings_version"),
    )

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="default")
    mappings_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IntegrationSyncJob(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "integration_sync_jobs"
    __table_args__ = (
        Index("ix_integration_sync_jobs_integration", "integration_id", "created_at"),
        UniqueConstraint(
            "organisation_id",
            "idempotency_key",
            name="uq_integration_sync_jobs_idempotency",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_integration_sync_jobs_status",
        ),
        CheckConstraint(
            "direction IN ('import', 'export', 'bidirectional', 'health_check')",
            name="ck_integration_sync_jobs_direction",
        ),
    )

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(32), nullable=False, default="health_check")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class IntegrationActivityLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "integration_activity_logs"
    __table_args__ = (
        Index("ix_integration_activity_logs_integration", "integration_id", "created_at"),
    )

    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
