"""F2.12 organisation communication: in-app, email/SMS outbox, announcements, templates, preferences."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organisation import Organisation
    from app.db.models.user import User


class CommunicationTemplate(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_templates"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_comm_templates_org_code"),
        Index("ix_comm_templates_org", "organisation_id"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_template: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_placeholders: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    organisation: Mapped["Organisation"] = relationship()


class CommunicationUserPreference(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_user_preferences"
    __table_args__ = (
        UniqueConstraint("organisation_id", "user_id", name="uq_comm_prefs_org_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    allow_in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_sms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_push: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marketing_opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship()


class CommunicationMessage(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        Index("ix_comm_messages_org_conv", "organisation_id", "conversation_id"),
        Index("ix_comm_messages_sender", "organisation_id", "sender_user_id"),
        CheckConstraint(
            "message_type IN ('direct', 'thread_reply', 'system')",
            name="ck_comm_messages_type",
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="direct")
    related_resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    sender: Mapped["User"] = relationship()


class CommunicationMessageRecipient(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_message_recipients"
    __table_args__ = (
        UniqueConstraint("message_id", "recipient_user_id", name="uq_comm_msg_recipient"),
        Index("ix_comm_msg_recipient_inbox", "organisation_id", "recipient_user_id", "read_at"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communication_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    message: Mapped["CommunicationMessage"] = relationship()
    recipient: Mapped["User"] = relationship()


class CommunicationAnnouncement(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_announcements"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_comm_ann_org_ref"),
        CheckConstraint(
            "status IN ('draft', 'published', 'cancelled', 'expired')",
            name="ck_comm_ann_status",
        ),
        CheckConstraint(
            "priority IN ('normal', 'high', 'emergency')",
            name="ck_comm_ann_priority",
        ),
        CheckConstraint(
            "audience IN ('organisation_all', 'staff_only', 'tenants_only', 'landlords_only', 'custom_users')",
            name="ck_comm_ann_audience",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    audience: Mapped[str] = mapped_column(String(64), nullable=False)
    audience_user_ids: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    channels: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()


class CommunicationAnnouncementRecipient(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_announcement_recipients"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_comm_ann_user"),
        Index("ix_comm_ann_user", "organisation_id", "user_id"),
    )

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communication_announcements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    in_app_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    announcement: Mapped["CommunicationAnnouncement"] = relationship()
    user: Mapped["User"] = relationship()


class CommunicationDelivery(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Outbox row per channel attempt; status machine for F2.12."""

    __tablename__ = "communication_deliveries"
    __table_args__ = (
        UniqueConstraint("organisation_id", "idempotency_key", name="uq_comm_del_idempotency"),
        Index("ix_comm_del_pending", "organisation_id", "status", "scheduled_at"),
        CheckConstraint(
            "channel IN ('in_app', 'email', 'sms', 'push')",
            name="ck_comm_del_channel",
        ),
        CheckConstraint(
            "status IN ("
            "'created', 'queued', 'sending', 'sent', 'attempted', 'provider_accepted', 'delivered', "
            "'failed', 'retrying', 'cancelled'"
            ")",
            name="ck_comm_del_status",
        ),
    )

    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)

    recipient: Mapped["User"] = relationship()


class CommunicationTranslation(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "communication_translations"
    __table_args__ = (
        UniqueConstraint(
            "target_type", "target_id", "target_field", "target_language", name="uq_comm_trn_target_lang"
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'reviewed')",
            name="ck_comm_trn_status",
        ),
    )

    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    target_field: Mapped[str] = mapped_column(String(32), nullable=False)
    source_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    target_language: Mapped[str] = mapped_column(String(16), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CommunicationScheduledReminder(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Org-scoped scheduled comm reminder — processed into CommunicationDelivery rows."""

    __tablename__ = "communication_scheduled_reminders"
    __table_args__ = (
        Index("ix_comm_sch_rem_due", "organisation_id", "scheduled_at", "status"),
        UniqueConstraint("organisation_id", "idempotency_key", name="uq_comm_sch_rem_idempotency"),
        CheckConstraint("status IN ('pending', 'sent', 'cancelled', 'failed')", name="ck_comm_sch_rem_status"),
    )

    reminder_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
