"""F8.7 benefits navigator add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.benefits_navigator.constants import ADDON_DISCLAIMER, DEFAULT_CATEGORIES
from app.benefits_navigator.eligibility import evaluate_rule
from app.rbac.matrix import permissions_for_role
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission


def test_default_categories_count() -> None:
    assert len(DEFAULT_CATEGORIES) == 10


def test_eligibility_more_information_required() -> None:
    status, explanation = evaluate_rule({"required_fields": ["employment_status"]}, {})
    assert status == "more_information_required"
    assert "guidance only" in explanation.lower()


def test_eligibility_potentially_eligible() -> None:
    status, _ = evaluate_rule({"required_fields": []}, {"employment_status": "employed"})
    assert status == "potentially_eligible"


def test_disclaimer_no_guarantee() -> None:
    assert "guarantee" in ADDON_DISCLAIMER.lower()


def test_tenant_permissions() -> None:
    perms = permissions_for_role(HMoreRole.TENANT)
    assert Permission.BENEFITS_NAVIGATOR_TENANT in perms
    assert Permission.BENEFITS_NAVIGATOR_ASSESS in perms


def test_contractor_has_no_benefits_access() -> None:
    perms = permissions_for_role(HMoreRole.MAINTENANCE_CONTRACTOR)
    assert Permission.BENEFITS_NAVIGATOR_TENANT not in perms


def test_f87_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f87/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.7_BENEFITS_NAVIGATOR_FINAL_REPORT.md").is_file()


def test_alembic_head_f87() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261119_5500_f87"]
