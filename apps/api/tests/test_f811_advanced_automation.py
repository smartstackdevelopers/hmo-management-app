"""F8.11 advanced automation add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.advanced_automation.constants import ADDON_DISCLAIMER, WORKFLOW_TEMPLATES, WORKFLOW_TRIGGERS
from app.advanced_automation.validation import validate_conditions, validate_steps
from app.db.models.enums import HMoreRole
from app.rbac.matrix import permissions_for_role, role_has_permission
from app.rbac.permissions import Permission
import pytest
from fastapi import HTTPException


def test_triggers_count() -> None:
    assert len(WORKFLOW_TRIGGERS) == 18


def test_templates_count() -> None:
    assert len(WORKFLOW_TEMPLATES) == 12


def test_validate_steps_requires_start_end() -> None:
    with pytest.raises(HTTPException):
        validate_steps([{"key": "a", "type": "notification"}])


def test_validate_steps_ok() -> None:
    validate_steps(
        [
            {"key": "start", "type": "start"},
            {"key": "end", "type": "end"},
        ]
    )


def test_conditions_and_or() -> None:
    validate_conditions({"operator": "or", "rules": []})


def test_org_admin_manage() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.ADVANCED_AUTOMATION_MANAGE)


def test_tenant_no_workflow_manage() -> None:
    perms = permissions_for_role(HMoreRole.TENANT)
    assert Permission.ADVANCED_AUTOMATION_MANAGE not in perms


def test_support_worker_can_approve() -> None:
    perms = permissions_for_role(HMoreRole.SUPPORT_WORKER)
    assert Permission.ADVANCED_AUTOMATION_APPROVE in perms


def test_f811_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f811/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.11_ADVANCED_AUTOMATION_FINAL_REPORT.md").is_file()


def test_disclaimer() -> None:
    assert "F6.3" in ADDON_DISCLAIMER or "automation" in ADDON_DISCLAIMER.lower()


def test_alembic_head_f811() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261122_5800_f811"]
