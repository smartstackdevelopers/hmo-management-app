"""F3.10 Tenant Assistant: ask only against approved content; no operational actions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.core.config import Settings, get_settings
from app.db.models.tenant_assistant import (
    TenantAssistantConversation,
    TenantAssistantMessage,
    TenantAssistantRateWindow,
)
from app.tenant_assistant import access as ta_access
from app.tenant_assistant.ai_client import ask_grounded
from app.tenant_assistant.content import (
    detect_escalation,
    items_as_dicts,
    load_approved_content,
    select_relevant,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

NOTICE = (
    "Information only — the Tenant Assistant answers from approved organisation content "
    "and does not make official operational decisions."
)

SUPPORT_GUIDANCE = (
    "I cannot confirm an answer from approved content for this question. "
    "Please contact your organisation support team through the HMore messages or "
    "announcements channels available to you."
)

ESCALATION_MESSAGES = {
    "emergency_or_safety": (
        "If you are in immediate danger, contact emergency services. "
        "I can only share organisation emergency guidance when it is approved for tenant use. "
        "Please also contact your support team through HMore."
    ),
    "housing_decision": (
        "I cannot decide housing eligibility, approvals, or allocations. "
        "Please contact your housing support team through HMore."
    ),
    "other_tenant": "I cannot discuss another tenant's information.",
    "safeguarding": "Please contact your support team directly about safeguarding concerns.",
    "private_records": "I cannot access private case notes or staff records.",
    "record_change": "I cannot change support plans, appointments, or personal records.",
    "complaint_escalation": (
        "I cannot submit a complaint for you. Use the HMore complaints flow or contact your support team."
    ),
    "human_support": SUPPORT_GUIDANCE,
}


def _denied(ctx: OrganisationContext) -> None:
    record_event_independent(
        action=audit_events.AI_TENANT_ASSISTANT_DENIED,
        resource_type="tenant_assistant",
        resource_id="",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Tenant Assistant access denied",
        metadata={},
    )


def _guard(ctx: OrganisationContext, fn):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx)
        raise


def availability(ctx: OrganisationContext, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    allowed = ta_access.pilot_org_ids(settings)
    enabled = bool(allowed) and ctx.organisation_id in allowed
    return {
        "available": enabled,
        "pilot_configured": bool(allowed),
        "notice": NOTICE,
        "makes_official_decisions": False,
    }


def _enforce_rate(session: Session, ctx: OrganisationContext, settings: Settings) -> None:
    limit = settings.tenant_assistant_hourly_limit
    window_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    row = session.scalar(
        select(TenantAssistantRateWindow).where(
            TenantAssistantRateWindow.organisation_id == ctx.organisation_id,
            TenantAssistantRateWindow.user_id == ctx.user_id,
            TenantAssistantRateWindow.window_start == window_start,
        )
    )
    if row is None:
        row = TenantAssistantRateWindow(
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            window_start=window_start,
            request_count=0,
        )
        session.add(row)
        session.flush()
    if row.request_count >= limit:
        record_event(
            session,
            action=audit_events.AI_TENANT_ASSISTANT_RATE_LIMITED,
            resource_type="tenant_assistant",
            resource_id=str(ctx.user_id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.DENIED,
            summary="Tenant Assistant rate limit reached",
            metadata={"limit": limit},
            raise_on_error=False,
        )
        raise HTTPException(status_code=429, detail="Tenant Assistant rate limit reached. Try again later.")
    row.request_count += 1
    session.flush()


def _get_or_create_conversation(
    session: Session, ctx: OrganisationContext, conversation_id: uuid.UUID | None
) -> TenantAssistantConversation:
    if conversation_id is not None:
        row = session.get(TenantAssistantConversation, conversation_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        assert_same_organisation(ctx, row.organisation_id)
        if row.user_id != ctx.user_id:
            raise HTTPException(status_code=403, detail="Conversation not available")
        return row
    row = TenantAssistantConversation(
        organisation_id=ctx.organisation_id,
        user_id=ctx.user_id,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def _message_public(row: TenantAssistantMessage) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "conversation_id": str(row.conversation_id),
        "role": row.role,
        "body": row.body,
        "source_refs": row.source_refs_json or [],
        "ai_status": row.ai_status,
        "escalation": row.escalation,
        "cache_status": row.cache_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def ask(
    session: Session,
    ctx: OrganisationContext,
    *,
    question: str,
    conversation_id: uuid.UUID | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    _guard(ctx, lambda: ta_access.require_tenant_ask(ctx))
    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_TENANT_ASSISTANT

    require_feature_available(session, ctx, FEATURE_TENANT_ASSISTANT)
    _guard(ctx, lambda: ta_access.require_pilot_enabled(ctx, settings, session=session))
    text = (question or "").strip()
    if len(text) < 3 or len(text) > 2000:
        raise HTTPException(status_code=422, detail="Question must be between 3 and 2000 characters")

    _enforce_rate(session, ctx, settings)
    conversation = _get_or_create_conversation(session, ctx, conversation_id)

    user_msg = TenantAssistantMessage(
        organisation_id=ctx.organisation_id,
        conversation_id=conversation.id,
        user_id=ctx.user_id,
        role="user",
        body=text,
        source_refs_json=[],
        ai_status="not_applicable",
    )
    session.add(user_msg)
    session.flush()

    record_event(
        session,
        action=audit_events.AI_TENANT_ASSISTANT_REQUESTED,
        resource_type="tenant_assistant_conversation",
        resource_id=str(conversation.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Tenant Assistant question received",
        metadata={"message_id": str(user_msg.id)},
        raise_on_error=False,
    )

    escalation = detect_escalation(text)
    items, fingerprint = load_approved_content(session, ctx.organisation_id, ctx.user_id)
    relevant = select_relevant(text, items) if not escalation else []
    source_refs = [
        {
            "content_id": item.content_id,
            "source_type": item.source_type,
            "title": item.title,
            "version_token": item.version_token,
        }
        for item in relevant
    ]

    if escalation:
        answer = ESCALATION_MESSAGES.get(escalation, SUPPORT_GUIDANCE)
        # For emergency escalation, attach approved emergency content when present.
        if escalation == "emergency_or_safety":
            emergency = [i for i in items if i.source_type == "maintenance_emergency_content"]
            if emergency:
                relevant = emergency[:2]
                source_refs = [
                    {
                        "content_id": item.content_id,
                        "source_type": item.source_type,
                        "title": item.title,
                        "version_token": item.version_token,
                    }
                    for item in relevant
                ]
                answer = (
                    ESCALATION_MESSAGES[escalation]
                    + "\n\nApproved emergency guidance on file:\n"
                    + "\n".join(f"- {item.title}: {item.body[:400]}" for item in relevant)
                )
        ai_status = "skipped_escalation"
        cache_status = None
        prompt_id = prompt_version = provider = model_id = None
        record_event(
            session,
            action=audit_events.AI_TENANT_ASSISTANT_ESCALATED,
            resource_type="tenant_assistant_conversation",
            resource_id=str(conversation.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Tenant Assistant escalated to human-support guidance",
            metadata={"escalation": escalation},
            raise_on_error=False,
        )
    elif not relevant:
        answer = SUPPORT_GUIDANCE
        ai_status = "no_content"
        cache_status = None
        prompt_id = prompt_version = provider = model_id = None
        record_event(
            session,
            action=audit_events.AI_TENANT_ASSISTANT_NO_CONTENT,
            resource_type="tenant_assistant_conversation",
            resource_id=str(conversation.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Tenant Assistant found no relevant approved content",
            metadata={"fingerprint": fingerprint},
            raise_on_error=False,
        )
    else:
        record_event(
            session,
            action=audit_events.AI_TENANT_ASSISTANT_CONTENT_RETRIEVED,
            resource_type="tenant_assistant_conversation",
            resource_id=str(conversation.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Tenant Assistant retrieved approved content",
            metadata={"count": len(relevant), "fingerprint": fingerprint},
            raise_on_error=False,
        )
        ai_response: dict | None = None
        try:
            response = ask_grounded(
                settings,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value,
                question=text,
                approved_snippets=items_as_dicts(relevant),
            )
            ai_response = response if isinstance(response, dict) else None
            result = response.get("result") if isinstance(response, dict) else None
            if not isinstance(result, dict):
                raise HTTPException(status_code=502, detail="Invalid AI response")
            answer = str(result.get("answer") or "").strip()
            if len(answer) < 10:
                raise HTTPException(status_code=502, detail="Invalid AI response")
            # Grounding check: refuse answers that clearly invent eligibility decisions.
            lowered = answer.lower()
            if any(
                phrase in lowered
                for phrase in (
                    "you are eligible",
                    "application is approved",
                    "application is rejected",
                    "i have contacted staff",
                    "i have submitted a complaint",
                )
            ):
                answer = SUPPORT_GUIDANCE
                ai_status = "rejected_ungrounded"
            else:
                ai_status = "completed"
            prompt_id = result.get("prompt_id")
            prompt_version = result.get("prompt_version")
            provider = result.get("provider")
            model_id = result.get("model_id")
            cache_status = result.get("cache_status")
            record_event(
                session,
                action=audit_events.AI_TENANT_ASSISTANT_COMPLETED,
                resource_type="tenant_assistant_conversation",
                resource_id=str(conversation.id),
                organisation_id=ctx.organisation_id,
                actor_user_id=ctx.user_id,
                actor_role=ctx.role.value,
                outcome=AuditOutcome.SUCCESS,
                summary="Tenant Assistant response generated",
                metadata={"ai_status": ai_status, "cache_status": cache_status},
                raise_on_error=False,
            )
        except HTTPException as exc:
            if exc.status_code == 402:
                answer = "The organisation AI usage limit has been reached. Please try again later or contact support."
                ai_status = "skipped_budget"
                action = audit_events.AI_TENANT_ASSISTANT_BUDGET
            else:
                answer = SUPPORT_GUIDANCE
                ai_status = "failed"
                action = audit_events.AI_TENANT_ASSISTANT_FAILED
            prompt_id = prompt_version = provider = model_id = None
            cache_status = None
            record_event(
                session,
                action=action,
                resource_type="tenant_assistant_conversation",
                resource_id=str(conversation.id),
                organisation_id=ctx.organisation_id,
                actor_user_id=ctx.user_id,
                actor_role=ctx.role.value,
                outcome=AuditOutcome.FAILURE if ai_status == "failed" else AuditOutcome.SUCCESS,
                summary="Tenant Assistant AI unavailable",
                metadata={"status_code": exc.status_code},
                raise_on_error=False,
            )

    assistant_msg = TenantAssistantMessage(
        organisation_id=ctx.organisation_id,
        conversation_id=conversation.id,
        user_id=ctx.user_id,
        role="assistant",
        body=answer,
        source_refs_json=source_refs,
        content_fingerprint=fingerprint,
        ai_status=ai_status,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
        escalation=escalation,
        cache_status=cache_status,
    )
    session.add(assistant_msg)
    conversation.last_message_at = datetime.now(timezone.utc)
    session.flush()

    # F3.14 — initiator-scoped activity with retrieval coverage when sources exist.
    from app.ai_transparency.service import attach_transparency, record_local_activity

    ta_request_id = None
    if "ai_response" in locals() and isinstance(ai_response, dict):
        ta_request_id = ai_response.get("request_id")
    if not ta_request_id:
        ta_request_id = f"ta-{assistant_msg.id}"
    conf_kind = "retrieval_coverage" if source_refs else "unavailable"
    conf_detail = {"sources_used": len(source_refs)} if source_refs else None
    if ai_status == "failed":
        exec_status = "failed"
    elif ai_status == "skipped_budget":
        exec_status = "rejected_budget"
    else:
        exec_status = "completed"
    activity = attach_transparency(
        session,
        request_id=str(ta_request_id),
        organisation_id=ctx.organisation_id,
        source_refs=source_refs,
        confidence_kind=conf_kind,
        confidence_detail=conf_detail,
        human_approval_status="not_applicable",
        output_ref={"type": "tenant_assistant_message", "id": str(assistant_msg.id)},
        operation_type="tenant_assistant",
        visibility="initiator",
    )
    if activity is None:
        activity = record_local_activity(
            session,
            organisation_id=ctx.organisation_id,
            request_id=str(ta_request_id),
            feature_id="ai.agent.tenant_assistant",
            workflow_id="tenant_assistant",
            user_id=ctx.user_id,
            execution_status=exec_status,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=provider,
            model_id=model_id,
            source_refs=source_refs,
            confidence_kind=conf_kind,
            confidence_detail=conf_detail,
            human_approval_status="not_applicable",
            output_ref={"type": "tenant_assistant_message", "id": str(assistant_msg.id)},
            operation_type="tenant_assistant",
            visibility="initiator",
        )

    return {
        "conversation_id": str(conversation.id),
        "question_message_id": str(user_msg.id),
        "message": _message_public(assistant_msg),
        "notice": NOTICE,
        "makes_official_decisions": False,
        "approved_content_count": len(relevant),
        "content_fingerprint": fingerprint,
        "activity_id": str(activity.id) if activity is not None else None,
    }


def list_conversations(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    _guard(ctx, lambda: ta_access.require_tenant_read(ctx))
    _guard(ctx, lambda: ta_access.require_pilot_enabled(ctx, session=session))
    rows = list(
        session.scalars(
            select(TenantAssistantConversation)
            .where(
                TenantAssistantConversation.organisation_id == ctx.organisation_id,
                TenantAssistantConversation.user_id == ctx.user_id,
            )
            .order_by(TenantAssistantConversation.updated_at.desc())
            .limit(20)
        )
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "status": row.status,
                "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
            }
            for row in rows
        ],
        "notice": NOTICE,
    }


def get_conversation(session: Session, ctx: OrganisationContext, conversation_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: ta_access.require_tenant_read(ctx))
    _guard(ctx, lambda: ta_access.require_pilot_enabled(ctx, session=session))
    row = session.get(TenantAssistantConversation, conversation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    assert_same_organisation(ctx, row.organisation_id)
    if row.user_id != ctx.user_id and ctx.role.value != "super_admin":
        raise HTTPException(status_code=403, detail="Conversation not available")
    messages = list(
        session.scalars(
            select(TenantAssistantMessage)
            .where(
                TenantAssistantMessage.conversation_id == conversation_id,
                TenantAssistantMessage.organisation_id == ctx.organisation_id,
            )
            .order_by(TenantAssistantMessage.created_at.asc())
        )
    )
    # Extra isolation: never return another tenant's messages even if IDs leak.
    if any(m.user_id != row.user_id for m in messages):
        raise HTTPException(status_code=500, detail="Conversation integrity error")
    return {
        "id": str(row.id),
        "status": row.status,
        "messages": [_message_public(m) for m in messages],
        "notice": NOTICE,
        "makes_official_decisions": False,
    }
