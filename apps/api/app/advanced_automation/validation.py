"""Validate workflow definitions before publish."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.advanced_automation.constants import STEP_TYPES


def validate_steps(steps: list[dict[str, Any]]) -> None:
    if not steps:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Workflow must include steps")
    types = {s.get("type") for s in steps if isinstance(s, dict)}
    if "start" not in types or "end" not in types:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Workflow must include start and end steps")
    for step in steps:
        if not isinstance(step, dict):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid step definition")
        st = step.get("type")
        if st not in STEP_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown step type: {st}")
        if not step.get("key"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Each step requires a key")
        if st == "approval" and not step.get("required_role") and not step.get("approver_user_id"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Approval steps require required_role or approver")


def validate_conditions(conditions: dict[str, Any]) -> None:
    if not conditions:
        return
    op = conditions.get("operator", "and")
    if op not in ("and", "or"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Condition operator must be and or or")
    rules = conditions.get("rules") or []
    if not isinstance(rules, list):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Condition rules must be a list")
