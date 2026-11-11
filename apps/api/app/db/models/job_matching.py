"""F5.4 job matching listings, matches, preferences and training."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class JobListing(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "job_listings"
    __table_args__ = (
        UniqueConstraint("organisation_id", "source_name", "external_id", name="uq_job_listings_org_source_ext"),
        Index("ix_job_listings_org_active", "organisation_id", "is_active"),
    )

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salary_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_skills_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_qualifications_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    experience_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    search_document: Mapped[str] = mapped_column(Text, nullable=False, default="")
    embedding_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class TrainingOpportunity(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "training_opportunities"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_training_opportunities_verification",
        ),
        UniqueConstraint("organisation_id", "source_name", "external_id", name="uq_training_org_source_ext"),
        Index("ix_training_opportunities_org_active", "organisation_id", "is_active"),
    )

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_free_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    related_skills_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unverified", server_default="unverified"
    )


class TenantJobMatchPreferences(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_job_match_preferences"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_job_match_preferences_tenant"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    preferred_categories_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preferred_locations_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preferred_employment_types_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preferred_experience_levels_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    career_interests_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preferred_hours: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_cvs.id", ondelete="SET NULL"), nullable=True
    )


class TenantJobMatch(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    __tablename__ = "tenant_job_matches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "job_id", name="uq_tenant_job_matches_tenant_job"),
        Index("ix_tenant_job_matches_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reasons_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    matching_skills_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_skills_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_cvs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TenantSavedJob(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    __tablename__ = "tenant_saved_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "job_id", name="uq_tenant_saved_jobs_tenant_job"),
        Index("ix_tenant_saved_jobs_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TenantSavedTraining(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_saved_training"
    __table_args__ = (
        CheckConstraint("status IN ('saved', 'in_progress', 'completed')", name="ck_tenant_saved_training_status"),
        UniqueConstraint("tenant_id", "training_id", name="uq_tenant_saved_training_tenant_training"),
        Index("ix_tenant_saved_training_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    training_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="saved", server_default="saved")
