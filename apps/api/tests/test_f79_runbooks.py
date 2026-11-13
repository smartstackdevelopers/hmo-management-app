"""F7.9 operational runbook documentation presence checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUNBOOKS = REPO / "docs" / "operations" / "runbooks"


def test_f79_required_runbooks() -> None:
    expected = [
        "README.md",
        "HMORE_OPERATIONS_RUNBOOK.md",
        "APPLICATION_OPERATIONS.md",
        "SECURITY_INCIDENT_RESPONSE_PLAN.md",
        "PERSONAL_DATA_BREACH_RESPONSE_PLAN.md",
        "DISASTER_RECOVERY_RUNBOOK.md",
        "DATABASE_OPERATIONS_GUIDE.md",
        "AWS_INFRASTRUCTURE_OPERATIONS_GUIDE.md",
        "DEPLOYMENT_AND_ROLLBACK_GUIDE.md",
        "MONITORING_AND_ALERTING_GUIDE.md",
        "USER_ACCESS_ADMINISTRATION_GUIDE.md",
        "OPERATIONAL_CHECKLISTS.md",
        "INCIDENT_SEVERITY_AND_ESCALATION.md",
    ]
    for name in expected:
        assert (RUNBOOKS / name).is_file(), name


def test_f79_final_report() -> None:
    assert (REPO / "docs" / "phase7" / "F7.9_RUNBOOKS_FINAL_REPORT.md").is_file()


def test_f79_breach_plan_mentions_dpo_review() -> None:
    text = (RUNBOOKS / "PERSONAL_DATA_BREACH_RESPONSE_PLAN.md").read_text(encoding="utf-8")
    assert "DPO" in text
    assert "does not make legal reporting decisions" in text.lower()

