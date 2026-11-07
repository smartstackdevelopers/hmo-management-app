"""Organisation workflows dashboard aggregates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.org_workflows import OrganisationCustomFormSubmission, SecureSharingGrant
from app.org_workflows.access import require_inbox_read
from app.org_workflows.inbox import collect_inbox_items
from app.tenancy.context import OrganisationContext


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_inbox_read(ctx)
    items = collect_inbox_items(session, ctx, include_completed=False)
    pending = [i for i in items if i.get("status") in {"pending", "submitted", "under_review", "awaiting_approval", "awaiting_information"}]
    info_req = [i for i in items if i.get("status") in {"information_required", "additional_information_required", "awaiting_information"}]
    overdue = [i for i in items if i.get("is_overdue")]
    active_sharing = session.scalar(
        select(func.count())
        .select_from(SecureSharingGrant)
        .where(
            SecureSharingGrant.organisation_id == ctx.organisation_id,
            SecureSharingGrant.status == "active",
        )
    ) or 0
    pending_subs = session.scalar(
        select(func.count())
        .select_from(OrganisationCustomFormSubmission)
        .where(
            OrganisationCustomFormSubmission.organisation_id == ctx.organisation_id,
            OrganisationCustomFormSubmission.status.in_(("pending", "under_review", "additional_information_required")),
        )
    ) or 0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pending_approvals": len(pending),
        "awaiting_review": len([i for i in items if i.get("status") == "under_review"]),
        "additional_information_requests": len(info_req),
        "overdue_approvals": len(overdue),
        "active_secure_sharing_grants": active_sharing,
        "pending_form_submissions": pending_subs,
        "recent_pending": pending[:8],
    }
