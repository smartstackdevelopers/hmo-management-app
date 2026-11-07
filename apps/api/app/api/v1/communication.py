"""F2.12 communication API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.communication import service as comm_service
from app.communication.schemas import (
    AnnouncementCreate,
    MessageReadPatch,
    MessageSend,
    OperationalSend,
    PreferenceUpdate,
    ReminderCreate,
    TemplateCreate,
    TemplateUpdate,
    TranslationRequest,
    TranslationReview,
)
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("/dashboard")
def comm_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.dashboard(session, org)


@router.get("/messages/inbox")
def inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.list_inbox(session, org, page=page, page_size=page_size, q=q)


@router.get("/messages/sent")
def sent(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.list_sent(session, org, page=page, page_size=page_size)


@router.post("/messages", status_code=201)
def send_message(
    body: MessageSend,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.send_message(session, org, body)


@router.get("/messages/{message_id}")
def get_message(
    message_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.get_message(session, org, message_id)


@router.patch("/messages/{message_id}/read")
def patch_read(
    message_id: uuid.UUID,
    body: MessageReadPatch,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.mark_message_read(session, org, message_id, body.read)


@router.get("/conversations/{conversation_id}/messages")
def conversation(
    conversation_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list:
    return comm_service.conversation_messages(session, org, conversation_id)


@router.post("/operational/send")
def operational_send(
    body: OperationalSend,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.operational_send(session, org, body)


@router.get("/deliveries")
def deliveries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.list_deliveries(session, org, page=page, page_size=page_size)


@router.get("/preferences")
def get_preferences(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    row = comm_service.get_or_create_prefs(session, org)
    return {
        "allow_in_app": row.allow_in_app,
        "allow_email": row.allow_email,
        "allow_sms": row.allow_sms,
        "marketing_opt_out": row.marketing_opt_out,
        "sms_suppressed": row.sms_suppressed,
    }


@router.patch("/preferences")
def patch_preferences(
    body: PreferenceUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.update_prefs(session, org, body)


@router.post("/reminders", status_code=201)
def create_reminder(
    body: ReminderCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.create_reminder(session, org, body)


@router.get("/reminders")
def list_reminders(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list:
    return comm_service.list_reminders(session, org)


@router.post("/reminders/{reminder_id}/cancel")
def cancel_reminder(
    reminder_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    comm_service.cancel_reminder(session, org, reminder_id)
    return {"ok": True}


@router.post("/announcements", status_code=201)
def create_announcement(
    body: AnnouncementCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.create_announcement(session, org, body)


@router.post("/announcements/{announcement_id}/publish")
def publish_announcement(
    announcement_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.publish_announcement(session, org, announcement_id)


@router.post("/announcements/{announcement_id}/cancel")
def cancel_ann(
    announcement_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    comm_service.cancel_announcement(session, org, announcement_id)
    return {"ok": True}


@router.get("/announcements")
def list_ann(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list:
    return comm_service.list_announcements(session, org)


@router.get("/announcements/{announcement_id}")
def get_ann(
    announcement_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.get_announcement(session, org, announcement_id)


@router.post("/translations/{target_type}/{target_id}", status_code=201)
def req_translation(
    target_type: str,
    target_id: uuid.UUID,
    body: TranslationRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.request_translation(session, org, target_type=target_type, target_id=target_id, body=body)


@router.patch("/translations/{translation_id}/review")
def review_translation(
    translation_id: uuid.UUID,
    body: TranslationReview,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.review_translation(session, org, translation_id, body)


@router.get("/templates")
def list_templates(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list:
    return comm_service.list_templates(session, org)


@router.post("/templates", status_code=201)
def create_template(
    body: TemplateCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.create_template(session, org, body)


@router.patch("/templates/{template_id}")
def patch_comm_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return comm_service.patch_template(session, org, template_id, body)
