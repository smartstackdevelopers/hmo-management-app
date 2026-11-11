"""Shared F5.3 employment preparation constants."""

from __future__ import annotations

SKILL_CATEGORIES = (
    "communication",
    "customer_service",
    "administration",
    "it_digital",
    "construction_maintenance",
    "cleaning_housekeeping",
    "hospitality",
    "retail",
    "healthcare_support",
    "teamwork",
    "problem_solving",
    "time_management",
    "leadership",
    "languages",
    "other",
)

SKILL_LEVELS = ("beginner", "developing", "intermediate", "advanced")

CV_TEMPLATES = (
    "simple_professional",
    "modern_professional",
    "entry_level",
    "skills_based",
    "experienced_worker",
)

DEFAULT_CV_SECTIONS = (
    "personal_profile",
    "contact",
    "employment",
    "education",
    "qualifications",
    "skills",
    "certificates",
    "volunteer",
    "projects",
    "languages",
    "references",
)

APPLICATION_STATUSES = (
    "interested",
    "preparing",
    "applied",
    "acknowledged",
    "interview_scheduled",
    "interview_completed",
    "offer_received",
    "rejected",
    "withdrawn",
)

COMMON_INTERVIEW_QUESTIONS = (
    "Tell me about yourself.",
    "Why do you want this role?",
    "What relevant skills do you bring?",
    "Describe a time you worked in a team.",
    "What are your strengths?",
    "What would you like to learn in this role?",
    "Do you have any questions for us?",
)

INTERVIEW_CHECKLIST_DEFAULT = (
    {"id": "read_job_description", "label": "Re-read the job description", "done": False},
    {"id": "prepare_examples", "label": "Prepare examples of your skills", "done": False},
    {"id": "plan_travel", "label": "Plan travel or online join details", "done": False},
    {"id": "prepare_questions", "label": "Prepare questions to ask the employer", "done": False},
    {"id": "bring_documents", "label": "Bring or have CV and ID ready", "done": False},
)
