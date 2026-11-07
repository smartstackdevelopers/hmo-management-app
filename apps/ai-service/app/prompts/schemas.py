from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PromptStatus(str, Enum):
    draft = "draft"
    published = "published"
    deprecated = "deprecated"


class PromptVersion(BaseModel):
    prompt_id: str
    version: str
    status: PromptStatus
    workflow_or_feature: str
    template: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    published_at: datetime | None = None

    model_config = {"frozen": True}


class PromptSummary(BaseModel):
    prompt_id: str
    version: str
    status: PromptStatus
    workflow_or_feature: str
    created_at: datetime
    published_at: datetime | None = None
