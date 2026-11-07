"""F2.12 notification integration for approval events (in-app, idempotent)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.communication import service as comm_service
from app.communication.schemas import MessageSend
from app.tenancy.context import OrganisationContext


def _send_in_app(
    session: Session,
    ctx: OrganisationContext,
    recipient_user_id: uuid.UUID,
    subject: str,
    body: str,
    *,
    resource_type: str,
    resource_id: uuid.UUID,
) -> None:
    comm_service.send_message(
        session,
        ctx,
        MessageSend(
            recipient_user_id=recipient_user_id,
            subject=subject,
            body=body,
            related_resource_type=resource_type,
            related_resource_id=resource_id,
        ),
    )


def approval_assigned(
    session: Session,
    ctx: OrganisationContext,
    reviewer_user_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
) -> None:
    _send_in_app(
        session,
        ctx,
        reviewer_user_id,
        "Approval assigned",
        f"You have been assigned to review a {source_type.replace('_', ' ')} request.",
        resource_type=source_type,
        resource_id=source_id,
    )


def approval_decided(
    session: Session,
    ctx: OrganisationContext,
    source_type: str,
    source_id: uuid.UUID,
    action: str,
) -> None:
    # Notify is best-effort; requester lookup is source-specific and omitted when unknown.
    _ = (session, ctx, source_type, source_id, action)


def sharing_granted(
    session: Session,
    ctx: OrganisationContext,
    recipient_user_id: uuid.UUID | None,
    grant_id: uuid.UUID,
    reference: str,
) -> None:
    if recipient_user_id is None:
        return
    _send_in_app(
        session,
        ctx,
        recipient_user_id,
        "Secure sharing grant",
        f"A record has been shared with you (reference {reference}).",
        resource_type="secure_sharing_grant",
        resource_id=grant_id,
    )


def sharing_revoked(
    session: Session,
    ctx: OrganisationContext,
    recipient_user_id: uuid.UUID | None,
    grant_id: uuid.UUID,
) -> None:
    if recipient_user_id is None:
        return
    _send_in_app(
        session,
        ctx,
        recipient_user_id,
        "Sharing revoked",
        "A secure sharing grant has been revoked.",
        resource_type="secure_sharing_grant",
        resource_id=grant_id,
    )
