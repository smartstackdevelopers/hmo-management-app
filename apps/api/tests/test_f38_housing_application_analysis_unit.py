"""F3.8 checklist mapping and narrative validation. No database and no LLM."""

from __future__ import annotations

import pytest

from app.ai_usage.features import feature_for_workflow
from app.db.models.enums import HMoreRole
from app.housing_application_analysis.checklist import (
    heuristic_gap_narrative,
    map_evidence_status,
    validate_ai_narrative,
)
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission


def test_evidence_status_mapping() -> None:
    assert map_evidence_status("accepted", file_count=1, is_required=True)[0] == "complete"
    assert map_evidence_status("missing", file_count=0, is_required=True)[0] == "missing"
    assert map_evidence_status("pending", file_count=0, is_required=True)[0] == "missing"
    assert map_evidence_status("pending", file_count=1, is_required=True)[0] == "needs_review"
    assert map_evidence_status("not_applicable", file_count=0, is_required=False)[0] == "not_applicable"


def test_narrative_rejects_housing_decisions() -> None:
    with pytest.raises(ValueError):
        validate_ai_narrative("The application is approved for housing.")
    with pytest.raises(ValueError):
        validate_ai_narrative("The tenant is eligible for housing allocation.")
    ok = validate_ai_narrative(
        "Missing identity evidence remains. Final decisions remain with authorised human staff."
    )
    assert "authorised human staff" in ok


def test_heuristic_narrative_has_no_decision_language() -> None:
    text = heuristic_gap_narrative(
        [
            {"title": "Proof of identity", "outcome": "missing"},
            {"title": "Housing requirements recorded", "outcome": "complete"},
        ],
        application_reference="APP-1",
    )
    lowered = text.lower()
    assert "approved" not in lowered
    assert "rejected" not in lowered
    assert "eligible" not in lowered
    assert "does not determine housing eligibility" in lowered


def test_feature_and_roles() -> None:
    assert feature_for_workflow("housing_application_analysis") == "ai.agent.housing_application"
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_HOUSING_APPLICATION_RUN)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_HOUSING_APPLICATION_REVIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AI_HOUSING_APPLICATION_REVIEW)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AI_HOUSING_APPLICATION_READ)

