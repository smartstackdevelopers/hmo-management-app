"""F8.7 benefits navigator service."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.benefits_navigator import access
from app.benefits_navigator.ai_client import ask_benefits_navigator
from app.benefits_navigator.constants import ADDON_DISCLAIMER, AI_NOTICE, DEFAULT_CATEGORIES, DEFAULT_CHECKLIST_ITEMS
from app.benefits_navigator.eligibility import evaluate_rule
from app.core.config import Settings, get_settings
from app.db.models.benefits_navigator import (
    BenefitsAiNavigatorMessage,
    BenefitsAssessmentSession,
    BenefitsCategory,
    BenefitsDirectoryRecord,
    BenefitsDocumentChecklist,
    BenefitsEligibilityRule,
    BenefitsOfficialSource,
    BenefitsSavedGuidance,
    BenefitsStaffConsentGrant,
    OrganisationBenefitsNavigatorSettings,
)
from app.db.models.catalogue import CommunityService
from app.db.models.enums import HMoreRole
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationBenefitsNavigatorSettings:
    row = session.scalars(
        select(OrganisationBenefitsNavigatorSettings).where(
            OrganisationBenefitsNavigatorSettings.organisation_id == org_id
        )
    ).first()
    if row is None:
        row = OrganisationBenefitsNavigatorSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationBenefitsNavigatorSettings:
    if not settings.benefits_navigator_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Benefits navigator add-on disabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Benefits navigator disabled for organisation")
    return row


def settings_dict(row: OrganisationBenefitsNavigatorSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "ai_assistant_enabled": row.ai_assistant_enabled,
        "reminder_config": row.reminder_config,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationBenefitsNavigatorSettings:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_MANAGE)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    for key in ("enabled", "privacy_review_complete", "ai_assistant_enabled"):
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))
    if data.get("reminder_config") is not None:
        row.reminder_config = data["reminder_config"]
    session.flush()
    record_event(
        session,
        action=audit_events.BENEFITS_NAVIGATOR_SETTINGS_UPDATE,
        resource_type="benefits_navigator_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Benefits navigator settings updated",
    )
    return row


def ensure_categories(session: Session, org_id: UUID) -> None:
    if session.scalar(select(func.count()).select_from(BenefitsCategory).where(BenefitsCategory.organisation_id == org_id)):
        return
    for idx, (slug, name) in enumerate(DEFAULT_CATEGORIES):
        session.add(BenefitsCategory(organisation_id=org_id, slug=slug, name=name, sort_order=idx))
    session.flush()


def _benefit_dict(r: BenefitsDirectoryRecord) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "category_slug": r.category_slug,
        "benefit_name": r.benefit_name,
        "description": r.description,
        "eligibility_information": r.eligibility_information,
        "application_guidance": r.application_guidance,
        "required_evidence": r.required_evidence,
        "application_link": r.application_link,
        "geographic_coverage": r.geographic_coverage,
        "last_verified_at": r.last_verified_at.isoformat() if r.last_verified_at else None,
        "is_active": r.is_active,
    }


def create_benefit_record(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> BenefitsDirectoryRecord:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_MANAGE)
    assert_addon(session, get_settings(), ctx.organisation_id)
    ensure_categories(session, ctx.organisation_id)
    row = BenefitsDirectoryRecord(
        organisation_id=ctx.organisation_id,
        category_slug=data["category_slug"],
        benefit_name=data["benefit_name"],
        description=data.get("description"),
        eligibility_information=data.get("eligibility_information"),
        application_guidance=data.get("application_guidance"),
        required_evidence=data.get("required_evidence") or [],
        official_source_id=data.get("official_source_id"),
        application_link=data.get("application_link"),
        geographic_coverage=data.get("geographic_coverage"),
        is_active=bool(data.get("is_active", False)),
    )
    session.add(row)
    session.flush()
    if data.get("conditions"):
        session.add(
            BenefitsEligibilityRule(
                organisation_id=ctx.organisation_id,
                benefit_record_id=row.id,
                rule_version=row.rule_version,
                conditions=data["conditions"],
                source_reference=data.get("source_reference"),
            )
        )
        session.flush()
    record_event(
        session,
        action=audit_events.BENEFITS_NAVIGATOR_RECORD_CREATED,
        resource_type="benefits_directory_record",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Benefit directory record created",
    )
    return row


def search_benefits(
    session: Session,
    ctx: OrganisationContext,
    *,
    category: str | None,
    location: str | None,
    housing: str | None,
    employment: str | None,
) -> list[dict[str, Any]]:
    access.require_read(ctx)
    assert_addon(session, get_settings(), ctx.organisation_id)
    q = select(BenefitsDirectoryRecord).where(
        BenefitsDirectoryRecord.organisation_id == ctx.organisation_id,
        BenefitsDirectoryRecord.is_active.is_(True),
    )
    rows = session.scalars(q).all()
    out: list[dict[str, Any]] = []
    for r in rows:
        if category and r.category_slug != category:
            continue
        if location and location not in (r.geographic_coverage or ""):
            continue
        if housing and r.category_slug not in {"housing_benefits", "council_tax_support", "emergency_financial"}:
            if housing != "any":
                continue
        if employment and r.category_slug not in {"employment_support", "universal_credit"}:
            if employment != "any":
                continue
        out.append(_benefit_dict(r))
    return out


def run_assessment(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> BenefitsAssessmentSession:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_ASSESS)
    assert_addon(session, get_settings(), ctx.organisation_id)
    tenant_id = data.get("tenant_user_id") or ctx.user_id
    access.require_tenant_data_access(session, ctx, tenant_id)
    benefit_id = data.get("benefit_record_id")
    answers = data.get("answers") or {}
    conditions: dict[str, Any] = {}
    rule_version = None
    if benefit_id:
        rule = session.scalar(
            select(BenefitsEligibilityRule).where(
                BenefitsEligibilityRule.organisation_id == ctx.organisation_id,
                BenefitsEligibilityRule.benefit_record_id == benefit_id,
                BenefitsEligibilityRule.active.is_(True),
            )
        )
        if rule:
            conditions = rule.conditions
            rule_version = rule.rule_version
    status_value, explanation = evaluate_rule(conditions, answers)
    row = BenefitsAssessmentSession(
        organisation_id=ctx.organisation_id,
        tenant_user_id=tenant_id,
        answers=answers,
        result_status=status_value,
        result_explanation=explanation,
        benefit_record_id=benefit_id,
        rule_version=rule_version,
        assessed_at=_now(),
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.BENEFITS_NAVIGATOR_ASSESSMENT_RUN,
        resource_type="benefits_assessment_session",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Benefits eligibility guidance assessment recorded",
    )
    return row


def ask_ai(session: Session, ctx: OrganisationContext, question: str) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_TENANT)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    if not settings_row.ai_assistant_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="AI benefits assistant not enabled for organisation")
    snippets = search_benefits(session, ctx, category=None, location=None, housing=None, employment=None)
    fallback_answer = (
        f"{AI_NOTICE} Review active benefits in your directory or contact support. "
        "No guarantee of eligibility."
    )
    answer = fallback_answer
    source_refs = [{"type": "directory", "count": len(snippets)}]
    settings = get_settings()
    try:
        if settings.ai_service_base_url and settings.ai_service_token:
            ai = ask_benefits_navigator(
                settings,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value if ctx.role else "tenant",
                question=question,
                benefit_snippets=snippets[:10],
            )
            answer = str(ai.get("answer") or ai.get("message") or fallback_answer)
            source_refs = ai.get("source_refs") or source_refs
    except HTTPException:
        pass
    msg = BenefitsAiNavigatorMessage(
        organisation_id=ctx.organisation_id,
        user_id=ctx.user_id,
        question=question,
        answer=answer,
        source_refs=source_refs,
    )
    session.add(msg)
    session.flush()
    record_event(
        session,
        action=audit_events.BENEFITS_NAVIGATOR_AI_ASK,
        resource_type="benefits_ai_navigator_message",
        resource_id=str(msg.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Benefits AI navigator question",
    )
    return {"answer": answer, "notice": AI_NOTICE, "source_refs": source_refs, "guarantees_eligibility": False}


def save_benefit(session: Session, ctx: OrganisationContext, benefit_id: UUID) -> BenefitsSavedGuidance:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_TENANT)
    assert_addon(session, get_settings(), ctx.organisation_id)
    existing = session.scalar(
        select(BenefitsSavedGuidance).where(
            BenefitsSavedGuidance.organisation_id == ctx.organisation_id,
            BenefitsSavedGuidance.user_id == ctx.user_id,
            BenefitsSavedGuidance.benefit_record_id == benefit_id,
        )
    )
    if existing:
        return existing
    row = BenefitsSavedGuidance(
        organisation_id=ctx.organisation_id,
        user_id=ctx.user_id,
        benefit_record_id=benefit_id,
    )
    session.add(row)
    session.flush()
    _notify_user(session, ctx.organisation_id, ctx.user_id, "Benefit guidance saved")
    return row


def tenant_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_TENANT)
    assert_addon(session, get_settings(), ctx.organisation_id)
    saved = session.scalars(
        select(BenefitsSavedGuidance).where(
            BenefitsSavedGuidance.organisation_id == ctx.organisation_id,
            BenefitsSavedGuidance.user_id == ctx.user_id,
        )
    ).all()
    assessments = session.scalars(
        select(BenefitsAssessmentSession)
        .where(
            BenefitsAssessmentSession.organisation_id == ctx.organisation_id,
            BenefitsAssessmentSession.tenant_user_id == ctx.user_id,
        )
        .order_by(BenefitsAssessmentSession.assessed_at.desc())
        .limit(5)
    ).all()
    recommended = search_benefits(session, ctx, category=None, location=None, housing=None, employment=None)[:5]
    checklist = session.scalar(
        select(BenefitsDocumentChecklist).where(
            BenefitsDocumentChecklist.organisation_id == ctx.organisation_id,
            BenefitsDocumentChecklist.user_id == ctx.user_id,
        )
    )
    return {
        "recommended": recommended,
        "saved_count": len(saved),
        "recent_assessments": [
            {"id": str(a.id), "status": a.result_status, "explanation": a.result_explanation} for a in assessments
        ],
        "checklist_items": (checklist.items if checklist else []),
        "notice": AI_NOTICE,
    }


def upsert_checklist(session: Session, ctx: OrganisationContext, items: list[dict[str, Any]], benefit_id: UUID | None) -> BenefitsDocumentChecklist:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_TENANT)
    assert_addon(session, get_settings(), ctx.organisation_id)
    row = session.scalar(
        select(BenefitsDocumentChecklist).where(
            BenefitsDocumentChecklist.organisation_id == ctx.organisation_id,
            BenefitsDocumentChecklist.user_id == ctx.user_id,
        )
    )
    if row is None:
        if not items:
            items = [{"key": k, "prepared": False} for k in DEFAULT_CHECKLIST_ITEMS]
        row = BenefitsDocumentChecklist(
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            benefit_record_id=benefit_id,
            items=items,
        )
        session.add(row)
    else:
        row.items = items
        row.benefit_record_id = benefit_id or row.benefit_record_id
    session.flush()
    return row


def grant_staff_consent(session: Session, ctx: OrganisationContext, support_user_id: UUID) -> BenefitsStaffConsentGrant:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_TENANT)
    row = BenefitsStaffConsentGrant(
        organisation_id=ctx.organisation_id,
        tenant_user_id=ctx.user_id,
        support_user_id=support_user_id,
    )
    session.add(row)
    session.flush()
    return row


def list_community_support(session: Session, ctx: OrganisationContext, location: str | None) -> list[dict[str, Any]]:
    access.require_read(ctx)
    q = select(CommunityService).where(
        CommunityService.organisation_id == ctx.organisation_id,
        CommunityService.is_published.is_(True),
        CommunityService.verification_status == "verified",
    )
    rows = session.scalars(q).all()
    out = []
    for r in rows:
        if location and location not in (r.address_line or ""):
            continue
        out.append(
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category,
                "contact": r.contact,
                "eligibility": r.eligibility,
            }
        )
    return out


def admin_reports(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_REPORTS)
    org = ctx.organisation_id
    active = (
        session.scalar(
            select(func.count()).select_from(BenefitsDirectoryRecord).where(
                BenefitsDirectoryRecord.organisation_id == org,
                BenefitsDirectoryRecord.is_active.is_(True),
            )
        )
        or 0
    )
    saved = session.scalar(select(func.count()).select_from(BenefitsSavedGuidance).where(BenefitsSavedGuidance.organisation_id == org)) or 0
    assessments = (
        session.scalar(select(func.count()).select_from(BenefitsAssessmentSession).where(BenefitsAssessmentSession.organisation_id == org))
        or 0
    )
    sources_pending = (
        session.scalar(
            select(func.count()).select_from(BenefitsOfficialSource).where(
                BenefitsOfficialSource.organisation_id == org,
                BenefitsOfficialSource.verification_status == "pending",
            )
        )
        or 0
    )
    return {
        "active_benefits": int(active),
        "saved_guidance_total": int(saved),
        "assessments_total": int(assessments),
        "sources_pending_verification": int(sources_pending),
    }


def _notify_user(session: Session, org_id: UUID, user_id: UUID, subject: str) -> None:
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(org_id),
            recipient_user_id=str(user_id),
            subject=subject,
            body="Open Benefits Navigator in HMore.",
            channel="in_app",
            target_type="benefits_navigator",
            target_id=subject[:40],
            idempotency_key=f"bn:{user_id}:{subject}:{date.today().isoformat()}",
            essential_operational=True,
        ),
    )
