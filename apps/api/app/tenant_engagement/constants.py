"""F8.8 tenant engagement constants."""

from __future__ import annotations

DEFAULT_GOAL_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("education", "Education"),
    ("employment", "Employment"),
    ("independent_living", "Independent Living"),
    ("health_wellbeing", "Health and Wellbeing"),
    ("financial_skills", "Financial Skills"),
    ("social_participation", "Social Participation"),
    ("housing_independence", "Housing Independence"),
    ("digital_skills", "Digital Skills"),
    ("personal_development", "Personal Development"),
    ("community_engagement", "Community Engagement"),
)

DEFAULT_BADGES: tuple[tuple[str, str, str], ...] = (
    ("first_goal_completed", "First Goal Completed", "goal_completed"),
    ("learning_starter", "Learning Starter", "lms_lesson"),
    ("training_completed", "Training Completed", "lms_course"),
    ("employment_prep", "Employment Preparation", "employment_activity"),
    ("digital_skills", "Digital Skills Progress", "digital_activity"),
    ("community_participation", "Community Participation", "community_activity"),
    ("independent_living", "Independent Living Progress", "independent_living"),
    ("personal_milestone", "Personal Milestone Achieved", "milestone_completed"),
    ("consistent_engagement", "Consistent Engagement", "streak"),
    ("support_plan_milestone", "Support Plan Milestone Completed", "support_plan_link"),
)

DEFAULT_ACTIVITIES: tuple[tuple[str, str], ...] = (
    ("complete_learning_lesson", "Complete a learning lesson"),
    ("employment_workshop", "Attend an employment workshop"),
    ("prepare_cv", "Prepare a CV"),
    ("budgeting_activity", "Complete a budgeting activity"),
    ("attend_appointment", "Attend an agreed appointment"),
    ("independent_living_task", "Complete an independent living task"),
    ("community_activity", "Participate in an approved community activity"),
    ("digital_skills_exercise", "Complete a digital skills exercise"),
)

ADDON_DISCLAIMER = (
    "Engagement points and badges recognise voluntary progress. They do not affect housing eligibility, "
    "essential services or safeguarding status."
)

AI_NOTICE = (
    "Suggestions only — not medical, housing or employment decisions. Users may reject any suggestion."
)
