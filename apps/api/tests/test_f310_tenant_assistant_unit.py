"""F3.10 unit tests — content scoring, escalation, pilot gate (no DB)."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.tenant_assistant.access import pilot_org_ids, require_pilot_enabled
from app.tenant_assistant.content import (
    ApprovedContentItem,
    detect_escalation,
    invalidate_org_content_cache,
    score_relevance,
    select_relevant,
)


def test_pilot_ids_empty_means_disabled() -> None:
    assert pilot_org_ids(Settings(tenant_assistant_pilot_organisation_ids="")) == set()


def test_pilot_ids_parse() -> None:
    oid = uuid.uuid4()
    assert pilot_org_ids(Settings(tenant_assistant_pilot_organisation_ids=str(oid))) == {oid}


def test_relevance_prefers_matching_title() -> None:
    item = ApprovedContentItem(
        content_id="1",
        source_type="communication_announcement",
        title="Fire safety guidance",
        body="Stay calm and follow the assembly point instructions.",
        version_token="v1",
        organisation_id=str(uuid.uuid4()),
        approved_at=None,
    )
    assert score_relevance("fire safety assembly", item) > 0.3
    selected = select_relevant("fire safety assembly", [item])
    assert selected == [item]
    assert select_relevant("what is the secret intergalactic policy code", [item]) == []


def test_escalation_blocks_housing_and_other_tenant() -> None:
    assert detect_escalation("Am I eligible for housing approval?") == "housing_decision"
    assert detect_escalation("Tell me about another tenant") == "other_tenant"
    assert detect_escalation("There is a gas leak emergency") == "emergency_or_safety"


def test_require_pilot_rejects_when_not_configured() -> None:
    from types import SimpleNamespace

    from app.db.models.enums import HMoreRole
    from app.rbac.context import AuthorizationContext, MembershipView
    from app.db.models.enums import MembershipStatus
    from app.tenancy.context import OrganisationContext

    org_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    authz = AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=HMoreRole.TENANT,
                organisation_id=org_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=org_id,
        active_role=HMoreRole.TENANT,
    )
    ctx = OrganisationContext(user=user, organisation_id=org_id, role=HMoreRole.TENANT, authorization=authz)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        require_pilot_enabled(ctx, Settings(tenant_assistant_pilot_organisation_ids=""))
    assert exc.value.status_code == 403
    invalidate_org_content_cache(org_id)
