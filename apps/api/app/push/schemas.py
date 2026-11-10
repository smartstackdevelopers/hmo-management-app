"""Request bodies for the push device API."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_EXPO_TOKEN = re.compile(r"^(ExponentPushToken|ExpoPushToken)\[[A-Za-z0-9_-]{8,200}\]$")


class PushDeviceRegister(BaseModel):
    expo_push_token: str = Field(..., min_length=20, max_length=255)
    platform: Literal["ios", "android", "web"]
    device_name: str | None = Field(default=None, max_length=255)
    app_version: str | None = Field(default=None, max_length=64)

    @field_validator("expo_push_token")
    @classmethod
    def expo_token_shape(cls, value: str) -> str:
        token = value.strip()
        if not _EXPO_TOKEN.match(token):
            raise ValueError("expo_push_token must look like ExponentPushToken[...]")
        return token

    @field_validator("device_name", "app_version")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None
