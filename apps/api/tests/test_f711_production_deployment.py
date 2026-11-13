"""F7.11 production deployment documentation — gate blocked, no live deploy."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROD = REPO / "docs" / "phase7" / "production"


def test_f711_production_package() -> None:
    for name in (
        "README.md",
        "PRODUCTION_READINESS_CHECKLIST.md",
        "DEPLOYMENT_APPROVAL_GATE.md",
        "GO_LIVE_ACCEPTANCE_CHECKLIST.md",
        "SMOKE_TEST_SCRIPT.md",
        "ROLLBACK_VERIFICATION.md",
    ):
        assert (PROD / name).is_file(), name


def test_f711_final_report_blocks_deploy() -> None:
    text = (REPO / "docs" / "phase7" / "F7.11_PRODUCTION_DEPLOYMENT_FINAL_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "no production deployment" in text.lower() or "NOT DEPLOYED" in text
    assert "BLOCKED" in text


def test_f711_approval_gate_not_passed() -> None:
    gate = (PROD / "DEPLOYMENT_APPROVAL_GATE.md").read_text(encoding="utf-8")
    assert "PENDING APPROVAL" in gate
    assert "BLOCKED" in gate
