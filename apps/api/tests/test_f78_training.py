"""F7.8 training documentation presence checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TRAINING = REPO / "docs" / "training"


def test_f78_six_role_guides() -> None:
    roles = TRAINING / "roles"
    expected = [
        "01-super-admin.md",
        "02-organisation-admin.md",
        "03-landlord.md",
        "04-tenant.md",
        "05-support-worker.md",
        "06-maintenance-contractor.md",
    ]
    for name in expected:
        assert (roles / name).is_file(), name


def test_f78_knowledge_base_core() -> None:
    for rel in (
        "README.md",
        "GETTING_STARTED.md",
        "ai/AI_AGENTS_STAFF_GUIDE.md",
        "security/SECURITY_PRIVACY_AWARENESS.md",
        "TRAINING_SCHEDULE_TEMPLATE.md",
        "LAUNCH_SUPPORT_PLAN.md",
    ):
        assert (TRAINING / rel).is_file(), rel


def test_f78_quick_reference_count() -> None:
    qr = TRAINING / "quick-reference"
    files = list(qr.glob("*.md"))
    assert len(files) >= 10
