"""F3.5 unit tests — grounded compose, schema, RBAC (no database, no LLM provider)."""

from __future__ import annotations

from fastapi import HTTPException

from app.ai_usage.features import FEATURE_CASE_SUMMARY, feature_for_workflow
from app.case_summaries.compose import compose_case_summary, source_fingerprint
from app.case_summaries.service import _accept_result
from app.db.models.enums import HMoreRole
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission


def _packet():
    return {
        "profile": {
            "id": "tenant-1",
            "preferred_name": "Amina",
            "tenancy_reference": "T-1",
            "status": "active",
            "needs_goals": "Wants warehouse work",
        },
        "daily_notes": [
            {
                "id": "note-1",
                "log_date": "2026-11-01",
                "when": "2026-11-01",
                "summary": "Visit completed",
                "notes": "Discussed CV",
                "status": "active",
            }
        ],
        "meetings": [],
        "appointments": [
            {
                "id": "appt-1",
                "kind": "appointment",
                "title": "Housing review",
                "when": "2026-12-01T10:00:00+00:00",
                "status": "scheduled",
            }
        ],
        "follow_ups": [
            {"id": "fu-1", "action": "Send CV template", "due_at": "2026-11-15", "status": "open"}
        ],
        "support_plans": [
            {"id": "plan-1", "kind": "support_plan", "title": "Employment plan", "status": "active", "objectives": "CV"}
        ],
        "goals": [],
        "incidents": [
            {"id": "inc-1", "kind": "incident", "title": "Noise report", "when": "2026-10-01", "status": "closed", "severity": "low"}
        ],
        "complaints": [],
        "maintenance": [
            {"id": "mnt-1", "kind": "maintenance", "title": "Boiler", "when": "2026-10-02", "status": "submitted", "priority": "low"}
        ],
        "documents": [],
        "sources": [
            {"type": "tenant", "id": "tenant-1"},
            {"type": "daily_log", "id": "note-1"},
            {"type": "appointment", "id": "appt-1"},
            {"type": "follow_up", "id": "fu-1"},
            {"type": "support_plan", "id": "plan-1"},
            {"type": "incident", "id": "inc-1"},
            {"type": "maintenance", "id": "mnt-1"},
        ],
    }


def test_compose_uses_only_supplied_facts() -> None:
    out = compose_case_summary(_packet())
    assert "Amina" in out["sections"]["overview"]
    assert "Visit completed" in out["sections"]["recent_support"]
    assert "Discussed CV" in out["sections"]["recent_support"]
    assert "Employment plan" in out["sections"]["needs_and_goals"]
    assert "Send CV template" in out["sections"]["outstanding_actions"]
    assert "Housing review" in out["sections"]["upcoming"]
    assert out["recorded_concerns"][0]["source_id"] == "inc-1"
    assert out["recorded_concerns"][0]["explicitly_recorded"] is True
    assert all(item["source_type"] != "maintenance" for item in out["recorded_concerns"])
    assert "diagnosis" in out["uncertainty_notes"].lower()
    assert out["generation_method"] == "structured_heuristic"
    assert out["ai_generated"] is True


def test_missing_sources_are_labelled_unavailable() -> None:
    packet = _packet()
    packet["daily_notes"] = []
    packet["meetings"] = []
    packet["appointments"] = []
    packet["support_plans"] = []
    packet["goals"] = []
    packet["profile"]["needs_goals"] = None
    out = compose_case_summary(packet)
    assert any("daily notes" in item.lower() for item in out["missing_information"])
    assert "Unavailable" in out["sections"]["recent_support"]
    assert out["recorded_concerns"]


def test_fingerprint_changes_when_sources_change() -> None:
    packet = _packet()
    first = source_fingerprint(packet)
    packet["sources"][1]["updated_at"] = "2026-11-02T00:00:00+00:00"
    second = source_fingerprint(packet)
    assert first != second


def test_invalid_ai_output_rejected() -> None:
    packet = _packet()
    try:
        _accept_result({"sections": {"overview": ""}, "recorded_concerns": [], "generation_method": "llm"}, packet)
        raise AssertionError("expected validation error")
    except HTTPException as exc:
        assert exc.status_code == 422
    try:
        _accept_result(
            {
                "sections": {key: "x" for key in ["overview", "background", "events", "recent_support", "needs_and_goals", "outstanding_actions", "upcoming"]},
                "recorded_concerns": [{"text": "invented", "source_type": "incident", "source_id": "not-in-packet", "explicitly_recorded": True}],
                "generation_method": "llm",
            },
            packet,
        )
        raise AssertionError("expected untraceable concern to fail")
    except HTTPException as exc:
        assert exc.status_code == 422


def test_feature_and_rbac() -> None:
    assert feature_for_workflow("case_summary") == FEATURE_CASE_SUMMARY
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_CASE_SUMMARY_RUN)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_CASE_SUMMARY_READ)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_CASE_SUMMARY_REVIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AI_CASE_SUMMARY_REVIEW)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.AI_CASE_SUMMARY_REVIEW)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AI_CASE_SUMMARY_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.AI_CASE_SUMMARY_RUN)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.AI_CASE_SUMMARY_RUN)
