from __future__ import annotations

import pytest

from app.core.errors import PromptError
from app.prompts.seed import FOUNDATION_PROMPT_ID, FOUNDATION_PROMPT_VERSION
from app.prompts.store import PromptStore, reset_prompt_store_for_tests
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_seed_prompt_active() -> None:
    store = reset_prompt_store_for_tests()
    active = store.resolve_active(FOUNDATION_PROMPT_ID)
    assert active.version == FOUNDATION_PROMPT_VERSION
    assert active.status.value == "published"


def test_published_prompt_immutable() -> None:
    store = reset_prompt_store_for_tests()
    with pytest.raises(PromptError):
        store.upsert_draft(
            prompt_id=FOUNDATION_PROMPT_ID,
            version=FOUNDATION_PROMPT_VERSION,
            workflow_or_feature="foundation_echo",
            template="changed",
        )


def test_missing_prompt_version() -> None:
    store = PromptStore()
    with pytest.raises(PromptError):
        store.get("does.not.exist")


def test_publish_promotes_and_deprecates_previous() -> None:
    store = PromptStore()
    store.upsert_draft(
        prompt_id="demo.prompt",
        version="1.0.0",
        workflow_or_feature="demo",
        template="v1",
    )
    store.publish("demo.prompt", "1.0.0")
    store.upsert_draft(
        prompt_id="demo.prompt",
        version="1.1.0",
        workflow_or_feature="demo",
        template="v2",
    )
    store.publish("demo.prompt", "1.1.0")
    assert store.resolve_active("demo.prompt").version == "1.1.0"
    assert store.get("demo.prompt", "1.0.0").status.value == "deprecated"


def test_prompts_list_api_hides_templates(client: TestClient) -> None:
    response = client.get("/api/v1/prompts", headers=auth_headers())
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert "template" not in items[0]
