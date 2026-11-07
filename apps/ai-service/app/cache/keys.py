from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_cache_key(
    *,
    organisation_id: UUID,
    workflow_id: str,
    prompt_id: str,
    prompt_version: str,
    provider: str,
    model_id: str,
    input_fingerprint: dict[str, Any],
) -> str:
    """Organisation-scoped key. Never embeds raw PII — hash the canonical payload."""
    material = canonical_json(
        {
            "org": str(organisation_id),
            "workflow": workflow_id,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "provider": provider,
            "model_id": model_id,
            "input": input_fingerprint,
        }
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"hmore:ai:v1:org:{organisation_id}:wf:{workflow_id}:h:{digest}"


def lock_key_for(cache_key: str) -> str:
    return f"{cache_key}:lock"
