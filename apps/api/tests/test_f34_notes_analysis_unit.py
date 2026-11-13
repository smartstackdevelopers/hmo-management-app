"""F3.4 unit tests — heuristic analysis, versioning, schema (no database)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.notes_analysis.heuristic import build_heuristic_analysis
from app.notes_analysis.versioning import note_payload_for_ai, source_note_version
from app.rbac.matrix import role_has_permission
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission


def test_heuristic_flags_follow_up_without_next_action() -> None:
    out = build_heuristic_analysis(
        {
            "summary": "Home visit",
            "notes": "Discussed employment. Meeting planned.",
            "activity_category": "support",
            "follow_up_required": True,
            "next_action": "",
            "log_date": "2026-11-01",
        }
    )
    analysis = out["analysis"]
    assert "AI-generated" in analysis["summary"]
    assert analysis["generation_method"] == "structured_heuristic"
    titles = [m["title"] for m in analysis["missing_details"]]
    assert any("Follow-up" in t for t in titles)
    assert any("Meeting" in t for t in titles)


def test_heuristic_empty_note() -> None:
    out = build_heuristic_analysis(
        {
            "summary": "",
            "notes": "",
            "activity_category": "support",
            "follow_up_required": False,
            "next_action": None,
            "log_date": "2026-11-01",
        }
    )
    assert any("empty" in m["title"].lower() for m in out["analysis"]["missing_details"])


def test_source_note_version_changes_with_content() -> None:
    base = SimpleNamespace(
        id=uuid4(),
        status="active",
        summary="A",
        notes="B",
        activity_category="support",
        interaction_type=None,
        follow_up_required=False,
        next_action=None,
        updated_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        log_date=date(2026, 11, 1),
    )
    v1 = source_note_version(base)  # type: ignore[arg-type]
    base.notes = "Changed"
    v2 = source_note_version(base)  # type: ignore[arg-type]
    assert v1 != v2
    payload = note_payload_for_ai(base)  # type: ignore[arg-type]
    assert payload["source_note_version"] == v2
    assert "notes" in payload


def test_f34_rbac_matrix() -> None:
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_NOTES_ANALYSIS_RUN)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AI_NOTES_ANALYSIS_REVIEW)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AI_NOTES_ANALYSIS_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.AI_NOTES_ANALYSIS_RUN)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_NOTES_ANALYSIS_REVIEW)

