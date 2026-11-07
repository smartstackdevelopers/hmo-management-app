from __future__ import annotations

import uuid
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def get_correlation_id() -> str:
    return correlation_id_var.get()


def set_correlation_id(value: str | None) -> str:
    cid = (value or "").strip() or new_correlation_id()
    correlation_id_var.set(cid)
    return cid
