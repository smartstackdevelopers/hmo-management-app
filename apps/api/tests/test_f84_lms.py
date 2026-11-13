"""F8.4 LMS add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.lms import assessments
from app.lms.constants import DEFAULT_CATEGORIES, ADDON_DISCLAIMER
from app.db.models.lms import LmsQuestion


def test_default_categories_count() -> None:
    assert len(DEFAULT_CATEGORIES) == 10


def test_assessment_multiple_choice() -> None:
    q = LmsQuestion(
        question_type="multiple_choice",
        prompt="x",
        correct_answer="a",
        requires_manual_marking=False,
    )
    ok, auto = assessments.score_answer(q, "a")
    assert ok is True and auto is True


def test_short_answer_not_auto_passed() -> None:
    q = LmsQuestion(question_type="short_answer", prompt="x", requires_manual_marking=True)
    ok, auto = assessments.score_answer(q, "free text")
    assert ok is None and auto is False


def test_disclaimer_no_false_accreditation() -> None:
    assert "not external accreditation" in ADDON_DISCLAIMER.lower()


def test_f84_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f84/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.4_LMS_FINAL_REPORT.md").is_file()


def test_alembic_head_f84() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261116_5200_f84"]
