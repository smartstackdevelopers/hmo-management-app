from __future__ import annotations

from app.prompts.store import PromptStore

FOUNDATION_PROMPT_ID = "hmore.foundation.echo"
FOUNDATION_PROMPT_VERSION = "1.0.0"


def seed_prompts(store: PromptStore) -> None:
    store.upsert_draft(
        prompt_id=FOUNDATION_PROMPT_ID,
        version=FOUNDATION_PROMPT_VERSION,
        workflow_or_feature="foundation_echo",
        template=(
            "You are the HMore foundation echo workflow. "
            "Organisation={{organisation_id}} Role={{role}}. "
            "Echo the safe operational message only: {{message}}"
        ),
        metadata={"phase": "F3.1", "agent": None},
    )
    store.publish(FOUNDATION_PROMPT_ID, FOUNDATION_PROMPT_VERSION)
