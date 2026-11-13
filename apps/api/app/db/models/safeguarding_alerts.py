"""F8.2 optional advanced safeguarding alerts models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganisationSafeguardingAlertSettings(Base):
    __tablename__ = "organisation_safeguarding_alert_settings"
    __table_args__ = (
        UniqueConstraint("organisation_id", name="uq_safeguarding_alert_settings_org"),
        CheckConstraint(
            "default_notification_channel IN ('in_app', 'email', 'push')",
            name="ck_safeguarding_alert_default_channel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    privacy_review_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_assist_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_notification_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="in_app")
    escalation_targets: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    emergency_guidance_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SafeguardingAlertCategory(Base):
    __tablename__ = "safeguarding_alert_categories"
    __table_args__ = (UniqueConstraint("organisation_id", "slug", name="uq_safeguarding_alert_category_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SafeguardingAlertRule(Base):
    __tablename__ = "safeguarding_alert_rules"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_safeguarding_alert_rule_priority",
        ),
        CheckConstraint(
            "notification_method IN ('in_app', 'email', 'push')",
            name="ck_safeguarding_alert_rule_notify",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alert_categories.id", ondelete="RESTRICT"), nullable=False
    )
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    responsible_team: Mapped[str] = mapped_column(String(64), nullable=False, default="support")
    notification_method: Mapped[str] = mapped_column(String(16), nullable=False, default="in_app")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SafeguardingAlert(Base):
    __tablename__ = "safeguarding_alerts"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_safeguarding_alerts_org_ref"),
        UniqueConstraint("organisation_id", "dedupe_key", name="uq_safeguarding_alerts_dedupe"),
        CheckConstraint(
            "status IN ('new', 'under_review', 'assigned', 'action_required', 'escalated', 'resolved', 'closed')",
            name="ck_safeguarding_alerts_status",
        ),
        CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_safeguarding_alerts_priority",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'rule', 'tenant_report', 'ai_suggestion')",
            name="ck_safeguarding_alerts_source_type",
        ),
        Index("ix_safeguarding_alerts_org_status", "organisation_id", "status"),
        Index("ix_safeguarding_alerts_org_priority", "organisation_id", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    reference_number: Mapped[str] = mapped_column(String(32), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alert_categories.id", ondelete="RESTRICT"), nullable=False
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alert_rules.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="staff")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    alert_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[list["SafeguardingAlertStatusHistory"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class SafeguardingAlertStatusHistory(Base):
    __tablename__ = "safeguarding_alert_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alerts.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    alert: Mapped["SafeguardingAlert"] = relationship(back_populates="history")


class SafeguardingAlertReview(Base):
    __tablename__ = "safeguarding_alert_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_type IN ('acknowledgement', 'assessment', 'supervisor', 'escalation_approval', 'closure')",
            name="ck_safeguarding_alert_review_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alerts.id", ondelete="CASCADE"), nullable=False
    )
    review_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SafeguardingAlertEscalation(Base):
    __tablename__ = "safeguarding_alert_escalations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alerts.id", ondelete="CASCADE"), nullable=False
    )
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_role: Mapped[str] = mapped_column(String(64), nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SafeguardingAlertAiSuggestion(Base):
    __tablename__ = "safeguarding_alert_ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alerts.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    suggestion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    uncertainty_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SafeguardingTenantReport(Base):
    __tablename__ = "safeguarding_tenant_reports"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_safeguarding_tenant_reports_ref"),
        CheckConstraint(
            "status IN ('received', 'linked', 'closed')",
            name="ck_safeguarding_tenant_reports_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    reference_number: Mapped[str] = mapped_column(String(32), nullable=False)
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alert_categories.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="SET NULL"), nullable=True
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safeguarding_alerts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
