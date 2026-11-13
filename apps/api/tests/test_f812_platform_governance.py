"""F8.12 platform governance add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.db.models.enums import HMoreRole
from app.platform_governance.constants import ADDON_DISCLAIMER, COMPLIANCE_CATEGORIES
from app.rbac.matrix import permissions_for_role, role_has_permission
from app.rbac.permissions import Permission


def test_compliance_categories() -> None:
    assert len(COMPLIANCE_CATEGORIES) >= 5


def test_disclaimer_no_legal_guarantee() -> None:
    assert "compliance" in ADDON_DISCLAIMER.lower()


def test_super_admin_governance_manage() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.PLATFORM_GOVERNANCE_MANAGE)


def test_org_admin_governance() -> None:
    perms = permissions_for_role(HMoreRole.ORGANISATION_ADMIN)
    assert Permission.PLATFORM_GOVERNANCE_READ in perms
    assert Permission.PLATFORM_GOVERNANCE_COMPLIANCE in perms


def test_tenant_no_governance() -> None:
    perms = permissions_for_role(HMoreRole.TENANT)
    assert Permission.PLATFORM_GOVERNANCE_MANAGE not in perms


def test_f812_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f812/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.12_PLATFORM_GOVERNANCE_FINAL_REPORT.md").is_file()
    assert (repo / "docs/phase8/PHASE8_COMPLETION_REPORT.md").is_file()


def test_alembic_head_f812() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261123_5900_f812"]
