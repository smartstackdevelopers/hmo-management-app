"""Request bodies for device sessions. Biometric samples are rejected."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceSessionRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    installation_id: uuid.UUID
    platform: Literal["ios", "android", "web"]
    device_name: str | None = Field(default=None, max_length=255)
    app_version: str | None = Field(default=None, max_length=64)

    @field_validator("device_name", "app_version")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class DeviceSessionRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revocation_reason: str | None = Field(default=None, max_length=500)

    @field_validator("revocation_reason")
    @classmethod
    def blank_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None
