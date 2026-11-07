"""F3.10 Tenant Assistant conversations. Answers only from approved content."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TenantAssistantConversation(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_assistant_conversations"
    __table_args__ = (
        Index("ix_tenant_assistant_conv_org_user", "organisation_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantAssistantMessage(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_assistant_messages"
    __table_args__ = (
        Index("ix_tenant_assistant_msg_conv", "conversation_id", "created_at"),
        Index("ix_tenant_assistant_msg_org_user", "organisation_id", "user_id"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    content_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_applicable")
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False, default="ai.agent.tenant_assistant")
    escalation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cache_status: Mapped[str | None] = mapped_column(String(32), nullable=True)


class TenantAssistantRateWindow(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Simple per-tenant hourly request counter for the pilot."""

    __tablename__ = "tenant_assistant_rate_windows"
    __table_args__ = (
        Index(
            "uq_tenant_assistant_rate_window",
            "organisation_id",
            "user_id",
            "window_start",
            unique=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
