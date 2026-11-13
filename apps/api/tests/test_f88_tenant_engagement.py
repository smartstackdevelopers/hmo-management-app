"""F8.8 tenant engagement add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.tenant_engagement.constants import ADDON_DISCLAIMER, DEFAULT_GOAL_CATEGORIES
from app.rbac.matrix import permissions_for_role
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission


def test_goal_categories_count() -> None:
    assert len(DEFAULT_GOAL_CATEGORIES) == 10


def test_disclaimer_no_housing_impact() -> None:
    assert "housing" in ADDON_DISCLAIMER.lower()


def test_tenant_has_engagement_permissions() -> None:
    perms = permissions_for_role(HMoreRole.TENANT)
    assert Permission.TENANT_ENGAGEMENT_TENANT in perms


def test_contractor_no_engagement() -> None:
    perms = permissions_for_role(HMoreRole.MAINTENANCE_CONTRACTOR)
    assert Permission.TENANT_ENGAGEMENT_TENANT not in perms


def test_support_staff_assist() -> None:
    perms = permissions_for_role(HMoreRole.SUPPORT_WORKER)
    assert Permission.TENANT_ENGAGEMENT_STAFF in perms


def test_f88_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f88/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.8_TENANT_ENGAGEMENT_FINAL_REPORT.md").is_file()


def test_alembic_head_f88() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261120_5600_f88"]
