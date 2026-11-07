"""F2.10 structured support plans: goals, milestones, reviews, exports."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organisation import Organisation
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class TenantSupportPlan(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_support_plans"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_support_plans_org_ref"),
        Index("ix_tenant_support_plans_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('draft', 'active', 'under_review', 'on_hold', 'completed', 'closed')",
            name="ck_tenant_support_plans_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_worker_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="SET NULL"), nullable=True
    )
    supersedes_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="SET NULL"), nullable=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()
    tenant: Mapped["Tenant"] = relationship()


class SupportPlanContributor(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_contributors"
    __table_args__ = (
        UniqueConstraint("plan_id", "user_id", name="uq_support_plan_contributors_plan_user"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )


class SupportPlanGoal(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_goals"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_support_plan_goals_org_ref"),
        Index("ix_support_plan_goals_plan", "plan_id", "status"),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'at_risk', 'achieved', 'on_hold', 'cancelled')",
            name="ck_support_plan_goals_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_support_plan_goals_priority",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    intended_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    progress_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()


class SupportPlanGoalChange(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_goal_changes"
    __table_args__ = (Index("ix_support_plan_goal_changes_goal", "goal_id", "created_at"),)

    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_plan_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupportPlanGoalProgressNote(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_goal_progress_notes"
    __table_args__ = (Index("ix_support_plan_goal_progress_goal", "goal_id", "created_at"),)

    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_plan_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    show_to_tenant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class SupportPlanMilestone(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_milestones"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_support_plan_milestones_org_ref"),
        Index("ix_support_plan_milestones_goal", "goal_id", "target_date"),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'delayed', 'cancelled')",
            name="ck_support_plan_milestones_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_plan_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()


class SupportPlanMilestoneChange(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_milestone_changes"
    __table_args__ = (Index("ix_support_plan_milestone_changes_ms", "milestone_id", "created_at"),)

    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_plan_milestones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupportPlanReview(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_reviews"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_support_plan_reviews_org_ref"),
        Index("ix_support_plan_reviews_plan_date", "plan_id", "review_date"),
        CheckConstraint(
            "review_type IN ('weekly', 'monthly')",
            name="ck_support_plan_reviews_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'in_progress', 'finalised', 'superseded')",
            name="ck_support_plan_reviews_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_type: Mapped[str] = mapped_column(String(16), nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    goals_reviewed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    milestones_reviewed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    progress_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenges: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_plan_changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()
    tenant: Mapped["Tenant"] = relationship()


class SupportPlanHistoryEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_history_events"
    __table_args__ = (Index("ix_support_plan_history_plan", "plan_id", "created_at"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    related_entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class SupportPlanProgressExport(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "support_plan_progress_exports"
    __table_args__ = (
        Index("ix_support_plan_exports_plan", "plan_id", "created_at"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_support_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="RESTRICT"), nullable=False
    )
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    include_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organisation: Mapped["Organisation"] = relationship()
