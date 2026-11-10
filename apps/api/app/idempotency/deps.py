"""Optional Idempotency-Key header. Absent or blank means the route runs once."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

from app.idempotency.service import clean_idempotency_key


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    return clean_idempotency_key(idempotency_key)


IdempotencyKey = Annotated[str | None, Depends(get_idempotency_key)]
