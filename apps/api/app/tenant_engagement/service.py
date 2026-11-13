"""F8.8 tenant engagement service."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.enums import HMoreRole
from app.db.models.tenant_engagement import (
    EngagementActivityCatalog,
    EngagementActivityCompletion,
    EngagementBadge,
    EngagementBadgeAward,
    EngagementDevelopmentGoal,
    EngagementGoalCategory,
    EngagementGoalMilestone,
    EngagementLeaderboardOptIn,
    EngagementPointLedger,
    EngagementTimelineEvent,
    OrganisationTenantEngagementSettings,
)
from app.db.models.lms import LmsEnrollment
from app.tenant_engagement import access
from app.tenant_engagement.ai_client import suggest_development
from app.tenant_engagement.constants import (
    ADDON_DISCLAIMER,
    AI_NOTICE,
    DEFAULT_ACTIVITIES,
    DEFAULT_BADGES,
    DEFAULT_GOAL_CATEGORIES,
)
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationTenantEngagementSettings:
    row = session.scalars(
        select(OrganisationTenantEngagementSettings).where(
            OrganisationTenantEngagementSettings.organisation_id == org_id
        )
    ).first()
    if row is None:
        row = OrganisationTenantEngagementSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationTenantEngagementSettings:
    if not settings.tenant_engagement_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Tenant engagement add-on disabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Tenant engagement disabled for organisation")
    return row


def settings_dict(row: OrganisationTenantEngagementSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "points_enabled": row.points_enabled,
        "leaderboard_enabled": row.leaderboard_enabled,
        "ai_assistant_enabled": row.ai_assistant_enabled,
        "point_rules": row.point_rules,
        "reminder_config": row.reminder_config,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationTenantEngagementSettings:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_MANAGE)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    for key in ("enabled", "privacy_review_complete", "points_enabled", "leaderboard_enabled", "ai_assistant_enabled"):
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))
    if data.get("point_rules") is not None:
        row.point_rules = data["point_rules"]
    if data.get("reminder_config") is not None:
        row.reminder_config = data["reminder_config"]
    session.flush()
    record_event(
        session,
        action=audit_events.TENANT_ENGAGEMENT_SETTINGS_UPDATE,
        resource_type="tenant_engagement_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Tenant engagement settings updated",
    )
    return row


def _seed_catalog(session: Session, org_id: UUID) -> None:
    if not session.scalar(select(func.count()).select_from(EngagementGoalCategory).where(EngagementGoalCategory.organisation_id == org_id)):
        for idx, (slug, name) in enumerate(DEFAULT_GOAL_CATEGORIES):
            session.add(EngagementGoalCategory(organisation_id=org_id, slug=slug, name=name, sort_order=idx))
    if not session.scalar(select(func.count()).select_from(EngagementBadge).where(EngagementBadge.organisation_id == org_id)):
        for slug, name, cond in DEFAULT_BADGES:
            session.add(
                EngagementBadge(
                    organisation_id=org_id, slug=slug, name=name, condition_key=cond, description="Configurable badge"
                )
            )
    if not session.scalar(select(func.count()).select_from(EngagementActivityCatalog).where(EngagementActivityCatalog.organisation_id == org_id)):
        for slug, name in DEFAULT_ACTIVITIES:
            session.add(EngagementActivityCatalog(organisation_id=org_id, slug=slug, name=name, description=name))
    session.flush()


def _timeline(session: Session, org_id: UUID, tenant_user_id: UUID, event_type: str, summary: str, metadata: dict | None = None) -> None:
    session.add(
        EngagementTimelineEvent(
            organisation_id=org_id,
            tenant_user_id=tenant_user_id,
            event_type=event_type,
            summary=summary,
            event_metadata=metadata or {},
        )
    )


def create_goal(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> EngagementDevelopmentGoal:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_TENANT)
    assert_addon(session, get_settings(), ctx.organisation_id)
    _seed_catalog(session, ctx.organisation_id)
    tenant_id = data.get("tenant_user_id") or ctx.user_id
    access.assert_tenant_or_staff(ctx, tenant_id)
    row = EngagementDevelopmentGoal(
        organisation_id=ctx.organisation_id,
        tenant_user_id=tenant_id,
        title=data["title"],
        description=data.get("description"),
        category_slug=data["category_slug"],
        start_date=data.get("start_date"),
        target_date=data.get("target_date"),
        progress_status=data.get("progress_status", "in_progress"),
        created_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    _timeline(session, ctx.organisation_id, tenant_id, "goal_created", f"Goal created: {row.title}")
    return row


def add_milestone(session: Session, ctx: OrganisationContext, goal_id: UUID, data: dict[str, Any]) -> EngagementGoalMilestone:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_TENANT)
    goal = session.get(EngagementDevelopmentGoal, goal_id)
    if goal is None or goal.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Goal not found")
    access.assert_tenant_or_staff(ctx, goal.tenant_user_id)
    ms = EngagementGoalMilestone(
        organisation_id=ctx.organisation_id,
        goal_id=goal.id,
        title=data["title"],
        description=data.get("description"),
        target_date=data.get("target_date"),
    )
    session.add(ms)
    session.flush()
    return ms


def complete_milestone(session: Session, ctx: OrganisationContext, milestone_id: UUID, data: dict[str, Any]) -> EngagementGoalMilestone:
    ms = session.get(EngagementGoalMilestone, milestone_id)
    if ms is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    goal = session.get(EngagementDevelopmentGoal, ms.goal_id)
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Goal not found")
    access.assert_tenant_or_staff(ctx, goal.tenant_user_id)
    evidence = data.get("evidence_file_id")
    if ctx.user_id == goal.tenant_user_id and not evidence:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Evidence required for tenant completion")
    if ctx.user_id != goal.tenant_user_id:
        require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_STAFF)
    ms.status = "completed"
    ms.completed_at = _now()
    ms.evidence_file_id = evidence
    ms.confirmed_by_user_id = ctx.user_id if ctx.user_id != goal.tenant_user_id else data.get("confirmed_by_user_id")
    ms.review_notes = data.get("review_notes")
    session.flush()
    _timeline(session, ctx.organisation_id, goal.tenant_user_id, "milestone_completed", ms.title)
    settings_row = _settings(session, ctx.organisation_id)
    if settings_row.points_enabled:
        award_points(
            session,
            ctx,
            goal.tenant_user_id,
            points=int(settings_row.point_rules.get("milestone_complete", 10)),
            reason="milestone_completed",
            source_type="milestone",
            source_id=ms.id,
            idempotency_key=f"ms:{ms.id}",
        )
    _recompute_goal_progress(session, goal)
    _notify_user(session, ctx.organisation_id, goal.tenant_user_id, "Milestone completed")
    return ms


def _recompute_goal_progress(session: Session, goal: EngagementDevelopmentGoal) -> None:
    milestones = session.scalars(select(EngagementGoalMilestone).where(EngagementGoalMilestone.goal_id == goal.id)).all()
    if not milestones:
        return
    done = sum(1 for m in milestones if m.status == "completed")
    goal.completion_percent = int((done / len(milestones)) * 100)
    if goal.completion_percent >= 100:
        goal.progress_status = "completed"
    session.flush()


def award_points(
    session: Session,
    ctx: OrganisationContext,
    tenant_user_id: UUID,
    *,
    points: int,
    reason: str,
    source_type: str,
    source_id: UUID | None,
    idempotency_key: str,
) -> EngagementPointLedger | None:
    settings_row = _settings(session, ctx.organisation_id)
    if not settings_row.points_enabled:
        return None
    existing = session.scalar(
        select(EngagementPointLedger).where(
            EngagementPointLedger.organisation_id == ctx.organisation_id,
            EngagementPointLedger.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing
    row = EngagementPointLedger(
        organisation_id=ctx.organisation_id,
        tenant_user_id=tenant_user_id,
        points=points,
        reason=reason,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        created_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    return row


def award_badge(session: Session, ctx: OrganisationContext, badge_id: UUID, tenant_user_id: UUID, *, verified: bool) -> EngagementBadgeAward:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_BADGES)
    badge = session.get(EngagementBadge, badge_id)
    if badge is None or not badge.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Badge not found")
    if not verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Badge must be verified before award")
    key = f"badge:{badge_id}:{tenant_user_id}"
    existing = session.scalar(
        select(EngagementBadgeAward).where(
            EngagementBadgeAward.organisation_id == ctx.organisation_id,
            EngagementBadgeAward.idempotency_key == key,
        )
    )
    if existing:
        return existing
    row = EngagementBadgeAward(
        organisation_id=ctx.organisation_id,
        badge_id=badge.id,
        tenant_user_id=tenant_user_id,
        verified=True,
        awarded_by_user_id=ctx.user_id,
        idempotency_key=key,
    )
    session.add(row)
    session.flush()
    _timeline(session, ctx.organisation_id, tenant_user_id, "badge_awarded", badge.name)
    _notify_user(session, ctx.organisation_id, tenant_user_id, "Badge awarded")
    settings_row = _settings(session, ctx.organisation_id)
    if settings_row.points_enabled and badge.points_value:
        award_points(
            session,
            ctx,
            tenant_user_id,
            points=badge.points_value,
            reason="badge_awarded",
            source_type="badge",
            source_id=badge.id,
            idempotency_key=f"pts:{key}",
        )
    record_event(
        session,
        action=audit_events.TENANT_ENGAGEMENT_BADGE_AWARDED,
        resource_type="engagement_badge_award",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Badge awarded with verification",
    )
    return row


def complete_activity(session: Session, ctx: OrganisationContext, activity_id: UUID, tenant_user_id: UUID | None) -> EngagementActivityCompletion:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_TENANT)
    tenant_id = tenant_user_id or ctx.user_id
    access.assert_tenant_or_staff(ctx, tenant_id)
    activity = session.get(EngagementActivityCatalog, activity_id)
    if activity is None or not activity.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Activity not found")
    row = EngagementActivityCompletion(
        organisation_id=ctx.organisation_id,
        activity_id=activity.id,
        tenant_user_id=tenant_id,
        confirmed_by_user_id=ctx.user_id if ctx.user_id != tenant_id else None,
    )
    session.add(row)
    session.flush()
    _timeline(session, ctx.organisation_id, tenant_id, "activity_completed", activity.name)
    settings_row = _settings(session, ctx.organisation_id)
    if settings_row.points_enabled and activity.points_value:
        award_points(
            session,
            ctx,
            tenant_id,
            points=activity.points_value,
            reason="activity_completed",
            source_type="activity",
            source_id=activity.id,
            idempotency_key=f"act:{activity.id}:{tenant_id}:{row.id}",
        )
    return row


def tenant_dashboard(session: Session, ctx: OrganisationContext, tenant_user_id: UUID | None) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_TENANT)
    assert_addon(session, get_settings(), ctx.organisation_id)
    tenant_id = tenant_user_id or ctx.user_id
    access.assert_tenant_or_staff(ctx, tenant_id)
    goals = session.scalars(
        select(EngagementDevelopmentGoal).where(
            EngagementDevelopmentGoal.organisation_id == ctx.organisation_id,
            EngagementDevelopmentGoal.tenant_user_id == tenant_id,
        )
    ).all()
    badges = session.scalars(
        select(EngagementBadgeAward)
        .join(EngagementBadge, EngagementBadgeAward.badge_id == EngagementBadge.id)
        .where(
            EngagementBadgeAward.organisation_id == ctx.organisation_id,
            EngagementBadgeAward.tenant_user_id == tenant_id,
        )
    ).all()
    points = (
        session.scalar(
            select(func.coalesce(func.sum(EngagementPointLedger.points), 0)).where(
                EngagementPointLedger.organisation_id == ctx.organisation_id,
                EngagementPointLedger.tenant_user_id == tenant_id,
            )
        )
        or 0
    )
    lms_progress = (
        session.scalar(
            select(func.count()).select_from(LmsEnrollment).where(
                LmsEnrollment.organisation_id == ctx.organisation_id,
                LmsEnrollment.user_id == tenant_id,
            )
        )
        or 0
    )
    timeline = session.scalars(
        select(EngagementTimelineEvent)
        .where(
            EngagementTimelineEvent.organisation_id == ctx.organisation_id,
            EngagementTimelineEvent.tenant_user_id == tenant_id,
        )
        .order_by(EngagementTimelineEvent.created_at.desc())
        .limit(20)
    ).all()
    return {
        "goals": [
            {
                "id": str(g.id),
                "title": g.title,
                "category_slug": g.category_slug,
                "progress_status": g.progress_status,
                "completion_percent": g.completion_percent,
            }
            for g in goals
        ],
        "badges_count": len(badges),
        "points_total": int(points),
        "lms_enrollments": int(lms_progress),
        "timeline": [{"event_type": t.event_type, "summary": t.summary, "at": t.created_at.isoformat()} for t in timeline],
        "disclaimer": ADDON_DISCLAIMER,
    }


def set_leaderboard_opt_in(session: Session, ctx: OrganisationContext, opted_in: bool, display_name: str | None) -> EngagementLeaderboardOptIn:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_TENANT)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    if opted_in and not settings_row.leaderboard_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Leaderboard disabled for organisation")
    row = session.scalar(
        select(EngagementLeaderboardOptIn).where(
            EngagementLeaderboardOptIn.organisation_id == ctx.organisation_id,
            EngagementLeaderboardOptIn.tenant_user_id == ctx.user_id,
        )
    )
    if row is None:
        row = EngagementLeaderboardOptIn(
            organisation_id=ctx.organisation_id,
            tenant_user_id=ctx.user_id,
            opted_in=opted_in,
            display_name=display_name,
        )
        session.add(row)
    else:
        row.opted_in = opted_in
        row.display_name = display_name
    session.flush()
    return row


def leaderboard(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_read(ctx)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    if not settings_row.leaderboard_enabled:
        return []
    rows = session.scalars(
        select(EngagementLeaderboardOptIn).where(
            EngagementLeaderboardOptIn.organisation_id == ctx.organisation_id,
            EngagementLeaderboardOptIn.opted_in.is_(True),
        )
    ).all()
    result: list[dict[str, Any]] = []
    for opt in rows:
        pts = (
            session.scalar(
                select(func.coalesce(func.sum(EngagementPointLedger.points), 0)).where(
                    EngagementPointLedger.organisation_id == ctx.organisation_id,
                    EngagementPointLedger.tenant_user_id == opt.tenant_user_id,
                )
            )
            or 0
        )
        result.append({"display_name": opt.display_name or "Participant", "points": int(pts)})
    result.sort(key=lambda x: x["points"], reverse=True)
    return result[:20]


def ai_suggest(session: Session, ctx: OrganisationContext, prompt: str) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_TENANT)
    settings_row = assert_addon(session, get_settings(), ctx.organisation_id)
    if not settings_row.ai_assistant_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="AI assistant disabled")
    goals = session.scalars(
        select(EngagementDevelopmentGoal).where(
            EngagementDevelopmentGoal.organisation_id == ctx.organisation_id,
            EngagementDevelopmentGoal.tenant_user_id == ctx.user_id,
        )
    ).all()
    context = {"goals": [g.title for g in goals], "notice": AI_NOTICE}
    suggestion = f"{AI_NOTICE} Consider breaking your goal into small milestones and linking LMS lessons where assigned."
    try:
        if get_settings().ai_service_base_url:
            ai = suggest_development(
                get_settings(),
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value if ctx.role else "tenant",
                prompt=prompt,
                context=context,
            )
            suggestion = str(ai.get("answer") or ai.get("suggestion") or suggestion)
    except HTTPException:
        pass
    record_event(
        session,
        action=audit_events.TENANT_ENGAGEMENT_AI_SUGGEST,
        resource_type="tenant_engagement_ai",
        resource_id=str(ctx.user_id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="AI personal development suggestion",
    )
    return {"suggestion": suggestion, "notice": AI_NOTICE, "user_may_reject": True}


def admin_reports(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_REPORTS)
    org = ctx.organisation_id
    active_goals = (
        session.scalar(
            select(func.count()).select_from(EngagementDevelopmentGoal).where(
                EngagementDevelopmentGoal.organisation_id == org,
                EngagementDevelopmentGoal.progress_status.in_(("in_progress", "not_started")),
            )
        )
        or 0
    )
    completed_goals = (
        session.scalar(
            select(func.count()).select_from(EngagementDevelopmentGoal).where(
                EngagementDevelopmentGoal.organisation_id == org,
                EngagementDevelopmentGoal.progress_status == "completed",
            )
        )
        or 0
    )
    badges = session.scalar(select(func.count()).select_from(EngagementBadgeAward).where(EngagementBadgeAward.organisation_id == org)) or 0
    activities = (
        session.scalar(select(func.count()).select_from(EngagementActivityCompletion).where(EngagementActivityCompletion.organisation_id == org))
        or 0
    )
    return {
        "active_goals": int(active_goals),
        "completed_goals": int(completed_goals),
        "badges_awarded": int(badges),
        "activities_completed": int(activities),
    }


def _notify_user(session: Session, org_id: UUID, user_id: UUID, subject: str) -> None:
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(org_id),
            recipient_user_id=str(user_id),
            subject=subject,
            body="Open your engagement dashboard in HMore.",
            channel="in_app",
            target_type="tenant_engagement",
            target_id=subject[:40],
            idempotency_key=f"te:{user_id}:{subject}:{date.today().isoformat()}",
            essential_operational=False,
        ),
    )
