"""F2.13 organisation workflows: approval config, custom forms, secure sharing."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

class OrganisationApprovalWorkflow(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "org_approval_workflows"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_org_approval_workflows_org_code"),
        CheckConstraint(
            "status IN ('draft', 'active', 'inactive')",
            name="ck_org_approval_workflows_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    process_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_approval_workflow_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    versions: Mapped[list[OrganisationApprovalWorkflowVersion]] = relationship(
        back_populates="workflow",
        foreign_keys="OrganisationApprovalWorkflowVersion.workflow_id",
    )


class OrganisationApprovalWorkflowVersion(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "org_approval_workflow_versions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "version_number", name="uq_org_approval_wf_ver"),
        Index("ix_org_approval_wf_ver_workflow", "workflow_id", "version_number"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_approval_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    reviewer_roles_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow: Mapped[OrganisationApprovalWorkflow] = relationship(
        back_populates="versions",
        foreign_keys=[workflow_id],
    )


class OrganisationApprovalAssignment(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Optional reviewer assignment for aggregated inbox items without native reviewer fields."""

    __tablename__ = "org_approval_assignments"
    __table_args__ = (
        UniqueConstraint("organisation_id", "source_type", "source_id", name="uq_org_approval_assign"),
        Index("ix_org_approval_assign_reviewer", "organisation_id", "reviewer_user_id"),
    )

    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganisationCustomForm(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "org_custom_forms"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_org_custom_forms_org_code"),
        CheckConstraint(
            "status IN ('draft', 'published', 'inactive')",
            name="ck_org_custom_forms_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_custom_form_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_approval_workflows.id", ondelete="SET NULL"),
        nullable=True,
    )

    versions: Mapped[list[OrganisationCustomFormVersion]] = relationship(
        back_populates="form",
        foreign_keys="OrganisationCustomFormVersion.form_id",
    )


class OrganisationCustomFormVersion(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "org_custom_form_versions"
    __table_args__ = (
        UniqueConstraint("form_id", "version_number", name="uq_org_custom_form_ver"),
        Index("ix_org_custom_form_ver_form", "form_id", "version_number"),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("org_custom_forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    form: Mapped[OrganisationCustomForm] = relationship(
        back_populates="versions",
        foreign_keys=[form_id],
    )


class OrganisationCustomFormSubmission(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "org_custom_form_submissions"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_org_form_sub_org_ref"),
        Index("ix_org_form_sub_form_status", "form_id", "status"),
        CheckConstraint(
            "status IN ('draft', 'pending', 'under_review', 'additional_information_required', "
            "'approved', 'rejected', 'cancelled', 'expired')",
            name="ck_org_form_sub_status",
        ),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("org_custom_forms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    form_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_custom_form_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workflow_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_approval_workflow_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    submitter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    answers_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(48), nullable=False, default="draft")
    assigned_reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecureSharingGrant(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "secure_sharing_grants"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_secure_sharing_org_ref"),
        Index("ix_secure_sharing_resource", "resource_type", "resource_id"),
        Index("ix_secure_sharing_recipient", "recipient_user_id", "expires_at"),
        CheckConstraint(
            "status IN ('active', 'expired', 'revoked')",
            name="ck_secure_sharing_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class SecureSharingAccessLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "secure_sharing_access_logs"
    __table_args__ = (Index("ix_secure_sharing_access_grant", "grant_id", "created_at"),)

    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("secure_sharing_grants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    accessor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
