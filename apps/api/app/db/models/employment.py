"""F5.3 tenant employment preparation: skills, CVs, applications, roadmap."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TenantSkillAssessment(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_skill_assessments"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_skill_assessments_tenant"),
        CheckConstraint("status IN ('in_progress', 'completed')", name="ck_tenant_skill_assessments_status"),
        Index("ix_tenant_skill_assessments_org", "organisation_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress", server_default="in_progress")
    skills_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    experiences_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    education_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    qualifications_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    certificates_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    languages_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    career_interests_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preferred_work_types_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    employment_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff_support_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class TenantCv(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_cvs"
    __table_args__ = (
        CheckConstraint(
            "template_id IN ("
            "'simple_professional', 'modern_professional', 'entry_level', "
            "'skills_based', 'experienced_worker'"
            ")",
            name="ck_tenant_cvs_template",
        ),
        Index("ix_tenant_cvs_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="simple_professional", server_default="simple_professional"
    )
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    section_order_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    pdf_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="SET NULL"), nullable=True
    )


class TenantJobApplication(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_job_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'interested', 'preparing', 'applied', 'acknowledged', "
            "'interview_scheduled', 'interview_completed', 'offer_received', "
            "'rejected', 'withdrawn'"
            ")",
            name="ck_tenant_job_applications_status",
        ),
        Index(
            "ix_tenant_job_applications_org_tenant_status",
            "organisation_id",
            "tenant_id",
            "status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linked_cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_cvs.id", ondelete="SET NULL"), nullable=True
    )
    contact_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="interested", server_default="interested")
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class TenantJobApplicationEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    __tablename__ = "tenant_job_application_events"
    __table_args__ = (
        Index("ix_tenant_job_application_events_app_created", "application_id", "created_at"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_job_applications.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TenantCareerGoal(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_career_goals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="ck_tenant_career_goals_status",
        ),
        Index("ix_tenant_career_goals_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_activities_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    progress_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenantInterviewNote(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_interview_notes"
    __table_args__ = (Index("ix_tenant_interview_notes_org_tenant", "organisation_id", "tenant_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_job_applications.id", ondelete="SET NULL"), nullable=True
    )
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_to_ask: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
