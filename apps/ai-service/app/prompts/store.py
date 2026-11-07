from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Iterable

from app.core.errors import PromptError, ValidationServiceError
from app.prompts.schemas import PromptStatus, PromptVersion


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PromptStore:
    """In-memory prompt registry for F3.1.

    Persistence note: F3.1 keeps prompts in-process so the AI service stays
    independently deployable without a new schema. Multi-replica production
    should move this store behind shared storage in a later Phase 3 feature
    without changing the public prompt resolution API.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._versions: dict[tuple[str, str], PromptVersion] = {}
        self._active: dict[str, str] = {}  # prompt_id -> published version

    def upsert_draft(
        self,
        *,
        prompt_id: str,
        version: str,
        workflow_or_feature: str,
        template: str,
        metadata: dict | None = None,
    ) -> PromptVersion:
        key = (prompt_id, version)
        with self._lock:
            existing = self._versions.get(key)
            if existing and existing.status != PromptStatus.draft:
                raise PromptError(
                    f"Prompt {prompt_id}@{version} is {existing.status.value} and immutable",
                    status_code=409,
                )
            record = PromptVersion(
                prompt_id=prompt_id,
                version=version,
                status=PromptStatus.draft,
                workflow_or_feature=workflow_or_feature,
                template=template,
                metadata=metadata or {},
                created_at=existing.created_at if existing else _utcnow(),
                published_at=None,
            )
            self._versions[key] = record
            return record

    def publish(self, prompt_id: str, version: str) -> PromptVersion:
        key = (prompt_id, version)
        with self._lock:
            record = self._versions.get(key)
            if not record:
                raise PromptError(f"Prompt {prompt_id}@{version} not found")
            if record.status == PromptStatus.published:
                return record
            if record.status != PromptStatus.draft:
                raise PromptError(
                    f"Only draft prompts can be published (got {record.status.value})",
                    status_code=409,
                )
            published = record.model_copy(
                update={"status": PromptStatus.published, "published_at": _utcnow()},
            )
            # Freeze: replace with frozen published copy; further upserts blocked.
            self._versions[key] = published
            previous = self._active.get(prompt_id)
            if previous and previous != version:
                prev_key = (prompt_id, previous)
                prev = self._versions.get(prev_key)
                if prev and prev.status == PromptStatus.published:
                    self._versions[prev_key] = prev.model_copy(
                        update={"status": PromptStatus.deprecated},
                    )
            self._active[prompt_id] = version
            return published

    def get(self, prompt_id: str, version: str | None = None) -> PromptVersion:
        with self._lock:
            if version is None:
                active = self._active.get(prompt_id)
                if not active:
                    raise PromptError(f"No active published version for prompt '{prompt_id}'")
                version = active
            record = self._versions.get((prompt_id, version))
            if not record:
                raise PromptError(f"Prompt {prompt_id}@{version} not found")
            return record

    def resolve_active(self, prompt_id: str) -> PromptVersion:
        record = self.get(prompt_id, None)
        if record.status != PromptStatus.published:
            raise PromptError(
                f"Active prompt {prompt_id}@{record.version} is not published",
                status_code=409,
            )
        return record

    def list_versions(self, prompt_id: str | None = None) -> list[PromptVersion]:
        with self._lock:
            values: Iterable[PromptVersion] = self._versions.values()
            items = [v for v in values if prompt_id is None or v.prompt_id == prompt_id]
            return sorted(items, key=lambda v: (v.prompt_id, v.version))

    def render(self, prompt_id: str, *, version: str | None = None, variables: dict[str, str] | None = None) -> tuple[PromptVersion, str]:
        record = self.get(prompt_id, version)
        if record.status == PromptStatus.draft and version is None:
            raise PromptError("Draft prompts cannot be resolved as active", status_code=409)
        text = record.template
        for key, value in (variables or {}).items():
            if "{{" in key or "}}" in key:
                raise ValidationServiceError("Invalid prompt variable name")
            text = text.replace("{{" + key + "}}", value)
        return record, text


_STORE: PromptStore | None = None
_STORE_LOCK = threading.Lock()


def get_prompt_store() -> PromptStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            from app.prompts.seed import seed_prompts

            _STORE = PromptStore()
            seed_prompts(_STORE)
        return _STORE


def reset_prompt_store_for_tests() -> PromptStore:
    global _STORE
    with _STORE_LOCK:
        from app.prompts.seed import seed_prompts

        _STORE = PromptStore()
        seed_prompts(_STORE)
        return _STORE
