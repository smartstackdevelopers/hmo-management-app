"""F3.14 AI activity transparency, confidence, sources, and wrong-answer feedback."""

from app.ai_transparency.service import (
    attach_transparency,
    ensure_activity_from_usage,
    get_activity,
    list_activities,
    list_feedback,
    record_local_activity,
    review_feedback,
    submit_feedback,
    feedback_stats,
)

__all__ = [
    "attach_transparency",
    "ensure_activity_from_usage",
    "get_activity",
    "list_activities",
    "list_feedback",
    "record_local_activity",
    "review_feedback",
    "submit_feedback",
    "feedback_stats",
]
