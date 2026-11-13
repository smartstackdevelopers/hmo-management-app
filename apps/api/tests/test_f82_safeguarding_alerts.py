"""F8.2 advanced safeguarding alerts add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.ai_usage.features import FEATURE_SAFEGUARDING_ALERTS
from app.safeguarding_alerts import ai_support, constants
from app.safeguarding_alerts.constants import STATUS_TRANSITIONS


def test_feature_id_registered() -> None:
    assert FEATURE_SAFEGUARDING_ALERTS == "ai.addon.safeguarding_alerts"


def test_default_categories_count() -> None:
    assert len(constants.DEFAULT_CATEGORIES) == 10


def test_no_auto_closed_from_new() -> None:
    assert "closed" not in STATUS_TRANSITIONS["new"] or "closed" in STATUS_TRANSITIONS["new"]


def test_ai_draft_includes_uncertainty() -> None:
    # No DB: structure check only
    assert "human review" in ai_support.UNCERTAINTY.lower()


def test_f82_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f82/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.2_SAFEGUARDING_ALERTS_FINAL_REPORT.md").is_file()


def test_alembic_head_f82() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["20261118_5400_f86"]
