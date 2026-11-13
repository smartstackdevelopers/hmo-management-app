"""F8.1 optional AI voice calling API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context
from app.voice_calling import service as voice_service

router = APIRouter(prefix="/voice-calling", tags=["voice-calling"])


class SettingsUpdateBody(BaseModel):
    enabled: bool | None = None
    provider_mode: str | None = None
    calling_hours: dict[str, Any] | None = None
    supported_languages: list[str] | None = None
    voice_id: str | None = None
    max_call_duration_seconds: int | None = Field(default=None, ge=60, le=7200)
    monthly_call_limit: int | None = Field(default=None, ge=1)
    monthly_minutes_limit: int | None = Field(default=None, ge=1)
    consent_required: bool | None = None
    recording_enabled: bool | None = None
    privacy_review_complete: bool | None = None
    handover_enabled: bool | None = None
    provider_config: dict[str, Any] | None = None


class ConsentBody(BaseModel):
    consent: bool


class TurnBody(BaseModel):
    audio_or_text: str = Field(min_length=1, max_length=4000)


class HandoverBody(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


class WebhookBody(BaseModel):
    organisation_id: uuid.UUID
    language: str = "en-GB"
    event: str = "incoming"


@router.get("/settings")
def get_settings(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_READ)
    from app.db.models.voice_calling import OrganisationVoiceCallingSettings
    from sqlalchemy import select

    row = session.scalars(
        select(OrganisationVoiceCallingSettings).where(
            OrganisationVoiceCallingSettings.organisation_id == ctx.organisation_id
        )
    ).first()
    if row is None:
        return voice_service.settings_to_dict(voice_service._settings_row(session, ctx.organisation_id))
    return voice_service.settings_to_dict(row)


@router.patch("/settings")
def patch_settings(
    body: SettingsUpdateBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_MANAGE)
    return voice_service.update_settings(session, ctx, body.model_dump(exclude_unset=True))


@router.get("/dashboard")
def dashboard(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_READ)
    return voice_service.dashboard_stats(session, ctx.organisation_id)


@router.get("/calls")
def list_calls(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_READ)
    return voice_service.list_sessions(session, ctx.organisation_id)


@router.post("/calls/incoming/test")
def start_test_incoming(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
    language: str = "en-GB",
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_TENANT_USE)
    call = voice_service.start_incoming_call(session, organisation_id=ctx.organisation_id, language=language)
    return voice_service.session_to_dict(call)


@router.post("/calls/{session_id}/consent")
def consent_step(
    session_id: uuid.UUID,
    body: ConsentBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_TENANT_USE)
    return voice_service.play_disclosure_and_consent(session, ctx, session_id, consent=body.consent)


@router.post("/calls/{session_id}/turn")
def conversation_turn(
    session_id: uuid.UUID,
    body: TurnBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_TENANT_USE)
    return voice_service.process_turn(session, ctx, session_id, audio_or_text=body.audio_or_text)


@router.post("/calls/{session_id}/handover")
def handover(
    session_id: uuid.UUID,
    body: HandoverBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.VOICE_CALLING_HANDOVER_MANAGE)
    return voice_service.request_handover(session, ctx, session_id, reason=body.reason)


@router.post("/calls/{session_id}/end")
def end_call(
    session_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    if ctx.authorization.has_permission(Permission.VOICE_CALLING_TENANT_USE) or ctx.authorization.has_permission(
        Permission.VOICE_CALLING_HANDOVER_MANAGE
    ):
        return voice_service.end_call(session, ctx, session_id)
    require_permission(ctx.authorization, Permission.VOICE_CALLING_READ)
    return voice_service.end_call(session, ctx, session_id)


@router.post("/webhooks/incoming")
def webhook_incoming(
    body: WebhookBody,
    session: Session = Depends(get_session),
    x_voice_signature: str | None = Header(default=None, alias="X-Voice-Signature"),
) -> dict[str, Any]:
    import json

    from app.core.config import get_settings
    from app.audit import events as audit_events
    from app.audit.service import AuditOutcome, record_event

    settings = get_settings()
    payload = json.dumps(body.model_dump(mode="json"), sort_keys=True).encode()
    voice_service.verify_webhook_signature(payload, x_voice_signature, settings)
    call = voice_service.start_incoming_call(
        session,
        organisation_id=body.organisation_id,
        language=body.language,
        provider_payload={"event": body.event},
    )
    record_event(
        session,
        action=audit_events.VOICE_CALLING_WEBHOOK_RECEIVED,
        resource_type="voice_call_session",
        resource_id=str(call.id),
        organisation_id=body.organisation_id,
        actor_user_id=None,
        actor_role="webhook",
        outcome=AuditOutcome.SUCCESS,
        summary="Voice webhook accepted (test path)",
        metadata={"event": body.event},
    )
    return {"session_id": str(call.id), "status": call.status}
