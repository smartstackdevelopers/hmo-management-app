"""F6.7 Council Portal add-on models — isolated from core HMoreRole (exactly six)."""

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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CouncilPortalOfficer(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Add-on council officer identity for an organisation — NOT an HMoreRole membership."""

    __tablename__ = "council_portal_officers"
    __table_args__ = (
        UniqueConstraint("organisation_id", "user_id", name="uq_council_portal_officers_org_user"),
        CheckConstraint(
            "status IN ('invited', 'active', 'suspended', 'revoked')",
            name="ck_council_portal_officer_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Add-on role label only — never written into organisation_memberships.role / hmore_role enum
    addon_role_label: Mapped[str] = mapped_column(
        String(64), nullable=False, default="council_officer", server_default="council_officer"
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    council_organisation_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CouncilPortalShare(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Authorised share of a housing application (and optional evidence) with council officers."""

    __tablename__ = "council_portal_shares"
    __table_args__ = (
        Index("ix_council_portal_shares_org_app", "organisation_id", "application_id"),
        Index("ix_council_portal_shares_org_status", "organisation_id", "status"),
        CheckConstraint(
            "resource_type IN ('housing_application', 'evidence_pack')",
            name="ck_council_portal_share_resource",
        ),
        CheckConstraint(
            "status IN ('active', 'revoked', 'expired')",
            name="ck_council_portal_share_status",
        ),
        UniqueConstraint(
            "organisation_id",
            "application_id",
            "resource_type",
            "resource_id",
            name="uq_council_portal_share_resource",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("housing_applications.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, default="housing_application")
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    # Scopes: application_status, evidence_meta, approval_history, reports_summary — never raw tenant caseload
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    include_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    include_approval_history: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class CouncilPortalAccessLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "council_portal_access_logs"
    __table_args__ = (Index("ix_council_portal_access_org_at", "organisation_id", "created_at"),)

    officer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    share_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("council_portal_shares.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
