"""F3.7 draft composition. No database and no model call."""

from __future__ import annotations

import pytest

from app.ai_usage.features import feature_for_workflow
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.db.models.enums import HMoreRole
from app.support_plan_drafts.compose import compose_support_plan_draft, validate_draft_content


def _packet(**profile):
    base = {
        "id": "tenant-1",
        "preferred_name": "Ali",
        "status": "active",
        "needs_goals": "Help with weekly budgeting",
    }
    base.update(profile)
    return {
        "profile": base,
        "sources": [{"type": "tenant", "id": "tenant-1", "updated_at": "2026-11-07T00:00:00"}],
        "goals": [],
        "daily_notes": [],
        "support_plans": [],
        "approved_case_summaries": [],
    }


def test_draft_restates_recorded_need_without_assignment() -> None:
    result = compose_support_plan_draft(_packet())
    content = result["content"]
    assert content["suggested_goals"][0]["source_refs"][0]["id"] == "tenant-1"
    assert "assign" in content["responsibility_note"].lower()
    assert content["suggested_goals"][0]["milestones"][0]["title"]
    assert "target_date" not in content["suggested_goals"][0]


def test_missing_needs_are_reported() -> None:
    result = compose_support_plan_draft(_packet(needs_goals=None))
    assert result["content"]["suggested_goals"] == []
    assert any("not invented" in gap.lower() or "was not invented" in gap.lower() for gap in result["content"]["gaps"])


def test_unknown_source_and_decision_language_rejected() -> None:
    packet = _packet()
    bad_source = compose_support_plan_draft(packet)["content"]
    bad_source["suggested_goals"][0]["source_refs"] = [{"type": "tenant", "id": "other"}]
    with pytest.raises(ValueError):
        validate_draft_content(bad_source, packet)
    decided = compose_support_plan_draft(packet)["content"]
    decided["situation"] = "The tenant is eligible for housing."
    with pytest.raises(ValueError):
        validate_draft_content(decided, packet)


def test_feature_and_roles() -> None:
    assert feature_for_workflow("support_plan_draft") == "ai.agent.support_planning"
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_SUPPORT_PLAN_DRAFT_RUN)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_SUPPORT_PLAN_DRAFT_REVIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AI_SUPPORT_PLAN_DRAFT_REVIEW)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AI_SUPPORT_PLAN_DRAFT_READ)

