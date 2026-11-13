"""Voice call session orchestration."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_usage import features as ai_features
from app.ai_usage.metering import record_and_reconcile
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.voice_calling import OrganisationVoiceCallingSettings, VoiceCallSession, VoiceCallTurn
from app.tenancy.context import OrganisationContext
from app.voice_calling import assistant, providers


def _settings_row(session: Session, org_id: UUID) -> OrganisationVoiceCallingSettings:
    row = session.scalars(
        select(OrganisationVoiceCallingSettings).where(
            OrganisationVoiceCallingSettings.organisation_id == org_id
        )
    ).first()
    if row is None:
        row = OrganisationVoiceCallingSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_voice_addon_available(session: Session, settings: Settings, org_id: UUID) -> OrganisationVoiceCallingSettings:
    if not settings.voice_calling_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Voice calling add-on is not enabled platform-wide")
    row = _settings_row(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Voice calling is disabled for this organisation")
    if row.recording_enabled and not row.privacy_review_complete:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Recording requires completed privacy review")
    return row


def settings_to_dict(row: OrganisationVoiceCallingSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "provider_mode": row.provider_mode,
        "calling_hours": row.calling_hours,
        "supported_languages": row.supported_languages,
        "voice_id": row.voice_id,
        "max_call_duration_seconds": row.max_call_duration_seconds,
        "monthly_call_limit": row.monthly_call_limit,
        "monthly_minutes_limit": row.monthly_minutes_limit,
        "consent_required": row.consent_required,
        "recording_enabled": row.recording_enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "handover_enabled": row.handover_enabled,
        "provider_config": row.provider_config,
    }


def update_settings(
    session: Session,
    ctx: OrganisationContext,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = _settings_row(session, ctx.organisation_id)
    for key in (
        "enabled",
        "provider_mode",
        "calling_hours",
        "supported_languages",
        "voice_id",
        "max_call_duration_seconds",
        "monthly_call_limit",
        "monthly_minutes_limit",
        "consent_required",
        "recording_enabled",
        "privacy_review_complete",
        "handover_enabled",
        "provider_config",
    ):
        if key in payload and payload[key] is not None:
            setattr(row, key, payload[key])
    if row.recording_enabled and not row.privacy_review_complete:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot enable recording without privacy review")
    if row.provider_mode == "twilio" and not get_settings().voice_twilio_account_sid:
        row.provider_mode = "pending_approval"
    session.flush()
    record_event(
        session,
        action=audit_events.VOICE_CALLING_SETTINGS_UPDATE,
        resource_type="voice_calling_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Voice calling settings updated",
        metadata={"enabled": row.enabled, "provider_mode": row.provider_mode},
    )
    return settings_to_dict(row)


def _monthly_call_count(session: Session, org_id: UUID) -> int:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(
        session.scalar(
            select(func.count())
            .select_from(VoiceCallSession)
            .where(VoiceCallSession.organisation_id == org_id, VoiceCallSession.started_at >= start)
        )
        or 0
    )


def _enforce_limits(session: Session, row: OrganisationVoiceCallingSettings) -> None:
    if row.monthly_call_limit is not None:
        if _monthly_call_count(session, row.organisation_id) >= row.monthly_call_limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Monthly voice call limit reached")


def verify_webhook_signature(body: bytes, signature: str | None, settings: Settings) -> None:
    secret = settings.voice_webhook_signing_secret
    if not secret:
        return
    if not signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


def start_incoming_call(
    session: Session,
    *,
    organisation_id: UUID,
    language: str = "en-GB",
    provider_payload: dict[str, Any] | None = None,
) -> VoiceCallSession:
    settings = get_settings()
    org_row = assert_voice_addon_available(session, settings, organisation_id)
    _enforce_limits(session, org_row)
    if org_row.provider_mode not in {"test"}:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Live telephony provider not approved")
    call_id = providers.start_mock_call(direction="incoming")
    call = VoiceCallSession(
        organisation_id=organisation_id,
        direction="incoming",
        status="ringing",
        provider_call_id=call_id,
        language=language,
        session_metadata={"provider_payload": provider_payload or {}},
    )
    session.add(call)
    session.flush()
    record_event(
        session,
        action=audit_events.VOICE_CALLING_SESSION_START,
        resource_type="voice_call_session",
        resource_id=str(call.id),
        organisation_id=organisation_id,
        actor_user_id=None,
        actor_role="system",
        outcome=AuditOutcome.SUCCESS,
        summary="Incoming voice call started (test)",
        metadata={"direction": "incoming", "provider_call_id": call_id},
    )
    return call


def play_disclosure_and_consent(
    session: Session,
    ctx: OrganisationContext,
    session_id: UUID,
    *,
    consent: bool,
) -> dict[str, Any]:
    org_row = assert_voice_addon_available(session, get_settings(), ctx.organisation_id)
    call = session.get(VoiceCallSession, session_id)
    if call is None or call.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Call session not found")
    call.ai_disclosure_played = True
    if org_row.consent_required:
        call.consent_obtained = bool(consent)
        if not consent:
            call.status = "failed"
            call.failure_reason = "consent_declined"
            call.ended_at = datetime.now(timezone.utc)
            session.flush()
            return session_to_dict(call)
    call.status = "in_progress"
    session.flush()
    tts = providers.mock_text_to_speech(assistant.DISCLOSURE)
    return {**session_to_dict(call), "disclosure_audio": tts}


def process_turn(
    session: Session,
    ctx: OrganisationContext,
    session_id: UUID,
    *,
    audio_or_text: str,
) -> dict[str, Any]:
    org_row = assert_voice_addon_available(session, get_settings(), ctx.organisation_id)
    call = session.get(VoiceCallSession, session_id)
    if call is None or call.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Call session not found")
    if call.status not in {"in_progress", "ringing"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Call is not active")
    if org_row.consent_required and not call.consent_obtained:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Consent required before conversation")
    transcript = providers.mock_speech_to_text(audio_or_text)
    transcript = assistant.normalize_transcript(transcript)
    if not transcript:
        transcript = "unclear"
    reply, handover, reason = assistant.generate_response(transcript, language=call.language)
    turn_index = call.ai_turn_count + 1
    req_id = f"voice-{call.id}-{turn_index}"
    record_and_reconcile(
        session,
        request_id=req_id,
        organisation_id=ctx.organisation_id,
        execution_status="completed",
        feature_id=ai_features.FEATURE_VOICE_CALLING,
        workflow_id="voice_assistant_turn",
        user_id=ctx.user_id,
        provider="test",
        model_id="voice-assistant-rules",
        input_tokens=len(transcript.split()),
        output_tokens=len(reply.split()),
        metadata={"session_id": str(call.id)},
    )
    turn = VoiceCallTurn(
        session_id=call.id,
        organisation_id=ctx.organisation_id,
        turn_index=turn_index,
        user_text_summary=transcript[:500],
        assistant_text=reply,
        ai_request_id=req_id,
        handover_suggested=handover,
    )
    session.add(turn)
    call.ai_turn_count = turn_index
    call.status = "in_progress"
    if handover and org_row.handover_enabled and reason:
        call.handover_status = "pending"
        call.handover_reason = reason
        call.status = "handover_requested"
    session.flush()
    audio = providers.mock_text_to_speech(reply)
    return {
        "session": session_to_dict(call),
        "turn": turn_to_dict(turn),
        "response_audio": audio,
    }


def request_handover(
    session: Session,
    ctx: OrganisationContext,
    session_id: UUID,
    *,
    reason: str,
) -> dict[str, Any]:
    assert_voice_addon_available(session, get_settings(), ctx.organisation_id)
    call = session.get(VoiceCallSession, session_id)
    if call is None or call.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Call session not found")
    call.handover_status = "pending"
    call.handover_reason = reason[:64]
    call.status = "handover_requested"
    session.flush()
    record_event(
        session,
        action=audit_events.VOICE_CALLING_HANDOVER_REQUEST,
        resource_type="voice_call_session",
        resource_id=str(call.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Voice call human handover requested",
        metadata={"reason": reason},
    )
    return session_to_dict(call)


def end_call(session: Session, ctx: OrganisationContext, session_id: UUID) -> dict[str, Any]:
    call = session.get(VoiceCallSession, session_id)
    if call is None or call.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Call session not found")
    now = datetime.now(timezone.utc)
    call.ended_at = now
    call.status = "completed" if call.status != "failed" else call.status
    if call.started_at:
        call.duration_seconds = int((now - call.started_at).total_seconds())
    session.flush()
    return session_to_dict(call)


def session_to_dict(call: VoiceCallSession) -> dict[str, Any]:
    return {
        "id": str(call.id),
        "organisation_id": str(call.organisation_id),
        "direction": call.direction,
        "status": call.status,
        "provider_call_id": call.provider_call_id,
        "language": call.language,
        "consent_obtained": call.consent_obtained,
        "ai_disclosure_played": call.ai_disclosure_played,
        "handover_status": call.handover_status,
        "handover_reason": call.handover_reason,
        "duration_seconds": call.duration_seconds,
        "ai_turn_count": call.ai_turn_count,
        "failure_reason": call.failure_reason,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
    }


def turn_to_dict(turn: VoiceCallTurn) -> dict[str, Any]:
    return {
        "turn_index": turn.turn_index,
        "user_text_summary": turn.user_text_summary,
        "assistant_text": turn.assistant_text,
        "handover_suggested": turn.handover_suggested,
    }


def list_sessions(session: Session, org_id: UUID, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(VoiceCallSession)
        .where(VoiceCallSession.organisation_id == org_id)
        .order_by(VoiceCallSession.started_at.desc())
        .limit(limit)
    ).all()
    return [session_to_dict(r) for r in rows]


def dashboard_stats(session: Session, org_id: UUID) -> dict[str, Any]:
    row = _settings_row(session, org_id)
    total = session.scalar(
        select(func.count()).select_from(VoiceCallSession).where(VoiceCallSession.organisation_id == org_id)
    )
    failed = session.scalar(
        select(func.count())
        .select_from(VoiceCallSession)
        .where(VoiceCallSession.organisation_id == org_id, VoiceCallSession.status == "failed")
    )
    handovers = session.scalar(
        select(func.count())
        .select_from(VoiceCallSession)
        .where(
            VoiceCallSession.organisation_id == org_id,
            VoiceCallSession.handover_status != "none",
        )
    )
    return {
        "total_calls": int(total or 0),
        "failed_calls": int(failed or 0),
        "handover_calls": int(handovers or 0),
        "monthly_calls": _monthly_call_count(session, org_id),
        "provider": providers.provider_status(row.provider_mode).__dict__,
        "settings_enabled": row.enabled,
    }
