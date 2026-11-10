"""F3.15 unit tests — registry and fail-closed defaults (no DB)."""

from __future__ import annotations

from app.ai_feature_flags.cache import TTL_SECONDS, cache_clear_all, cache_get, cache_invalidate, cache_set
from app.ai_feature_flags.registry import (
    CONTROLLABLE_FEATURE_IDS,
    REGISTRY,
    canonical_feature_id,
    is_registered,
)
from uuid import uuid4


def test_registry_covers_phase3_agents_not_f315_itself() -> None:
    ids = {f.feature_id for f in REGISTRY}
    assert "ai.agent.notes_analysis" in ids
    assert "ai.agent.tenant_assistant" in ids
    assert "ai.activity.transparency" in ids
    assert "ai.workflow.daily_log_rewrite" in ids
    assert "ai.feature_flags" not in ids
    assert len(CONTROLLABLE_FEATURE_IDS) == 12


def test_aliases_resolve() -> None:
    assert canonical_feature_id("ai.agent.case_summary") == "ai.workflow.case_summaries"
    assert is_registered("ai.agent.document_check")
    assert not is_registered("ai.agent.made_up")


def test_cache_is_org_scoped_and_ttl_documented() -> None:
    cache_clear_all()
    org_a = uuid4()
    org_b = uuid4()
    cache_set(org_a, "ai.agent.notes_analysis", enabled=True, pilot_enabled=False)
    cache_set(org_b, "ai.agent.notes_analysis", enabled=False, pilot_enabled=False)
    assert cache_get(org_a, "ai.agent.notes_analysis") == (True, False)
    assert cache_get(org_b, "ai.agent.notes_analysis") == (False, False)
    cache_invalidate(org_a, "ai.agent.notes_analysis")
    assert cache_get(org_a, "ai.agent.notes_analysis") is None
    assert cache_get(org_b, "ai.agent.notes_analysis") == (False, False)
    assert TTL_SECONDS == 15
    cache_clear_all()


def test_tenant_assistant_is_pilot_eligible() -> None:
    ta = next(f for f in REGISTRY if f.feature_id == "ai.agent.tenant_assistant")
    assert ta.pilot_eligible is True
    assert ta.preserve_enabled_for_existing_orgs is False
