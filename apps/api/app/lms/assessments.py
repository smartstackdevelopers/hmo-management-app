"""F8.4 assessment auto-scoring — manual items stay pending."""

from __future__ import annotations

from typing import Any

from app.db.models.lms import LmsQuestion


def score_answer(question: LmsQuestion, answer: Any) -> tuple[bool | None, bool]:
    """Return (correct, auto_scored)."""
    if question.requires_manual_marking or question.question_type == "short_answer":
        return None, False
    correct = question.correct_answer
    if correct is None:
        return None, False
    if question.question_type in {"multiple_choice", "true_false", "knowledge_check"}:
        return answer == correct, True
    if question.question_type == "multiple_answer":
        if not isinstance(answer, list) or not isinstance(correct, list):
            return False, True
        return sorted(answer) == sorted(correct), True
    return None, False


def compute_score_percent(results: list[tuple[bool | None, bool]]) -> int | None:
    scorable = [c for c, auto in results if auto and c is not None]
    if not scorable:
        return None
    correct = sum(1 for c in scorable if c)
    return int(round(100 * correct / len(scorable)))
