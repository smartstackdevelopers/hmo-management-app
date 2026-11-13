"""F7.12 final acceptance and handover package checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HANDOVER = REPO / "docs" / "handover"


def test_f712_handover_package() -> None:
    required = [
        "README.md",
        "EXECUTIVE_COMPLETION_REPORT.md",
        "FINAL_ACCEPTANCE_MATRIX.md",
        "SEVEN_PHASE_COMPLETION_SUMMARY.md",
        "OUTSTANDING_ISSUES_REGISTER.md",
        "PRODUCTION_ACCEPTANCE_CHECKLIST.md",
        "GO_LIVE_DECISION.md",
        "END_TO_END_ACCEPTANCE_TESTS.md",
    ]
    for name in required:
        assert (HANDOVER / name).is_file(), name


def test_f712_final_report_and_not_live() -> None:
    report = REPO / "docs" / "phase7" / "F7.12_FINAL_ACCEPTANCE_REPORT.md"
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "NOT YET LIVE" in text


def test_f712_go_live_decision_option_e() -> None:
    decision = (HANDOVER / "GO_LIVE_DECISION.md").read_text(encoding="utf-8")
    assert "E. NOT YET LIVE" in decision
    assert "LIVE AND VERIFIED" not in decision.split("## Selected status")[1][:200]

