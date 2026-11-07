from __future__ import annotations

import pytest

from app.core.errors import WorkflowError
from app.tools.registry import build_default_tool_registry


def test_allowlisted_tool_only() -> None:
    registry = build_default_tool_registry()
    assert registry.invoke("echo_safe", message="ok") == "ok"
    with pytest.raises(WorkflowError):
        registry.invoke("rm_rf")
