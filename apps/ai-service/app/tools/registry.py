from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.errors import WorkflowError


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    description: str
    handler: Callable[..., Any]


class ToolRegistry:
    """Allow-listed tools only — model output cannot register or invoke arbitrary tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        if tool.name in self._tools:
            raise WorkflowError(f"Tool '{tool.name}' is already registered", status_code=409)
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool:
        tool = self._tools.get(name)
        if not tool:
            raise WorkflowError(f"Tool '{name}' is not an approved tool")
        return tool

    def invoke(self, name: str, **kwargs: Any) -> Any:
        return self.get(name).handler(**kwargs)

    def names(self) -> list[str]:
        return sorted(self._tools)


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def echo_safe(*, message: str) -> str:
        # Strip control chars; no code execution.
        cleaned = "".join(ch for ch in message if ch.isprintable() or ch in "\n\t")
        return cleaned[:4000]

    registry.register(
        RegisteredTool(
            name="echo_safe",
            description="Return a sanitised echo of a message (no side effects).",
            handler=echo_safe,
        )
    )
    return registry
