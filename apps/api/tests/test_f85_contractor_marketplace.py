"""F8.5 contractor marketplace add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.contractor_marketplace.constants import ADDON_DISCLAIMER, DEFAULT_CATEGORIES
from app.rbac.matrix import permissions_for_role
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission


def test_default_categories_count() -> None:
    assert len(DEFAULT_CATEGORIES) == 10


def test_disclaimer_no_false_verification() -> None:
    assert "verification" in ADDON_DISCLAIMER.lower() or "certif" in ADDON_DISCLAIMER.lower()


def test_contractor_role_has_workspace_permissions() -> None:
    perms = permissions_for_role(HMoreRole.MAINTENANCE_CONTRACTOR)
    assert Permission.CONTRACTOR_MARKETPLACE_WORKSPACE in perms
    assert Permission.CONTRACTOR_MARKETPLACE_QUOTE in perms


def test_f85_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f85/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.5_CONTRACTOR_MARKETPLACE_FINAL_REPORT.md").is_file()


def test_alembic_head_f85() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261118_5400_f86"]
