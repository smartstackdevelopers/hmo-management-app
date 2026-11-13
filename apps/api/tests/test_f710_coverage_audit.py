"""F7.10 final coverage audit documentation checks."""

from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AUDIT = REPO / "docs" / "audit"


def test_f710_audit_package_files() -> None:
    required = [
        "README.md",
        "REQUIREMENTS_TRACEABILITY_MATRIX.md",
        "REQUIREMENTS_TRACEABILITY_MATRIX.csv",
        "MISSING_FEATURES_REGISTER.md",
        "REMEDIATION_PLAN.md",
        "SECURITY_PRIVACY_STATUS.md",
        "OPTIONAL_SCOPE_REGISTER.md",
        "FINAL_TESTING_EVIDENCE_REGISTER.md",
        "PHASE_COMPLETION_SUMMARY.md",
        "END_TO_END_WORKFLOW_VERIFICATION.md",
        "SIX_ROLE_ACCESS_VERIFICATION.md",
    ]
    for name in required:
        assert (AUDIT / name).is_file(), name


def test_f710_final_coverage_report() -> None:
    assert (REPO / "docs" / "phase7" / "F7.10_FINAL_COVERAGE_REPORT.md").is_file()


def test_f710_traceability_matrix_minimum_rows() -> None:
    csv_path = AUDIT / "REQUIREMENTS_TRACEABILITY_MATRIX.csv"
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 150
    statuses = {r["status"] for r in rows}
    assert "PASS" in statuses
    assert "PARTIAL" in statuses
    # Honest audit must not claim 100% PASS on all mandatory rows
    pass_count = sum(1 for r in rows if r["status"] == "PASS")
    assert pass_count < len(rows)

