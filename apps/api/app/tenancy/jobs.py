"""Organisation-safe foundations for Celery / background jobs (F1.5).

Full Celery automation belongs to later phases. This module defines the payload
contract and validation so jobs cannot process foreign organisation records.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.user import User
from sqlalchemy import select


@dataclass(frozen=True)
class JobOrganisationContext:
    organisation_id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    correlation_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["organisation_id"] = str(self.organisation_id)
        if self.actor_user_id is not None:
            payload["actor_user_id"] = str(self.actor_user_id)
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> JobOrganisationContext:
        if not isinstance(payload, dict):
            raise ValueError("Job payload must be an object")
        raw_org = payload.get("organisation_id")
        if not raw_org:
            raise ValueError("Job payload missing organisation_id")
        try:
            organisation_id = uuid.UUID(str(raw_org))
        except ValueError as exc:
            raise ValueError("Invalid organisation_id in job payload") from exc
        actor_raw = payload.get("actor_user_id")
        actor_user_id = uuid.UUID(str(actor_raw)) if actor_raw else None
        return cls(
            organisation_id=organisation_id,
            actor_user_id=actor_user_id,
            correlation_id=payload.get("correlation_id"),
        )


def validate_job_organisation_context(
    session: Session,
    payload: dict[str, Any],
) -> JobOrganisationContext:
    """Validate job org context against the database. Never trust payload alone for authz."""
    ctx = JobOrganisationContext.from_payload(payload)

    if ctx.actor_user_id is not None:
        user = session.get(User, ctx.actor_user_id)
        if user is None:
            raise ValueError("Job actor user not found")
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == ctx.actor_user_id,
                OrganisationMembership.organisation_id == ctx.organisation_id,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        super_admin = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == ctx.actor_user_id,
                OrganisationMembership.role == HMoreRole.SUPER_ADMIN,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        if membership is None and super_admin is None:
            raise PermissionError("Job actor is not authorized for this organisation")

    return ctx
