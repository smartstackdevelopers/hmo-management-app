"""Wellbeing constants and non-clinical disclaimer copy."""

from __future__ import annotations

DISCLAIMER = (
    "HMore provides general wellbeing information and support resources. "
    "It is not a medical service. Daily check-ins are not medical assessments and mood records are not diagnoses. "
    "Exercise and mindfulness activities are general information only and are not a replacement for professional care. "
    "If you are in immediate danger or think you may harm yourself, contact local emergency services (999 in the UK) "
    "or a suitable crisis support service such as Samaritans on 116 123. "
    "Seek help from a qualified professional if you have concerns about your health."
)

MOODS = ("very_good", "good", "okay", "low", "very_low")

ROUTINE_CATEGORIES = (
    "morning",
    "personal_care",
    "exercise",
    "meals",
    "work_study",
    "family",
    "relaxation",
    "evening",
    "other",
)

EXERCISE_CATEGORIES = (
    "walking",
    "gentle_movement",
    "stretching",
    "beginner",
    "home",
    "balance",
    "general_fitness",
    "other",
)

MINDFULNESS_CATEGORIES = (
    "breathing",
    "relaxation",
    "mindful_awareness",
    "guided_reflection",
    "short_break",
    "daily_calm",
)

DIRECTORY_CATEGORIES = (
    "community_wellbeing",
    "mental_wellbeing_support",
    "social_support",
    "community_activities",
    "local_advice",
    "general_support",
)

# Official national signposting only — not local invented providers.
NATIONAL_SUPPORT_LINKS = (
    {
        "id": "emergency_uk",
        "title": "Emergency services (UK)",
        "description": "If you or someone else is in immediate danger.",
        "contact": "999",
        "url": None,
        "category": "crisis",
    },
    {
        "id": "samaritans",
        "title": "Samaritans",
        "description": "24/7 listening support in the UK and Ireland.",
        "contact": "116 123",
        "url": "https://www.samaritans.org",
        "category": "crisis",
    },
    {
        "id": "nhs_111",
        "title": "NHS 111",
        "description": "Urgent medical help or advice when it is not a 999 emergency (England).",
        "contact": "111",
        "url": "https://111.nhs.uk",
        "category": "health_advice",
    },
)

DEFAULT_RESOURCES = (
    {
        "kind": "exercise",
        "category": "walking",
        "title": "Gentle outdoor or indoor walk",
        "description": "A short walk at a comfortable pace.",
        "instructions": "Wear suitable shoes. Walk for a few minutes at a pace that feels comfortable. Stop if you feel pain or dizziness.",
        "duration_minutes": 10,
        "activity_level": "gentle",
        "equipment": "Comfortable shoes",
        "safety_notes": "Seek professional advice before starting new activity if you have health concerns.",
        "source_name": "HMore general wellbeing guidance",
        "verification_status": "verified",
    },
    {
        "kind": "exercise",
        "category": "stretching",
        "title": "Seated shoulder stretch",
        "description": "Gentle stretch while sitting.",
        "instructions": "Sit upright. Slowly roll your shoulders backward a few times. Stop if uncomfortable.",
        "duration_minutes": 3,
        "activity_level": "gentle",
        "equipment": "Chair",
        "safety_notes": "Do not force a stretch. Stop if you feel pain.",
        "source_name": "HMore general wellbeing guidance",
        "verification_status": "verified",
    },
    {
        "kind": "mindfulness",
        "category": "breathing",
        "title": "Slow breathing pause",
        "description": "A short breathing pause. Stop anytime.",
        "instructions": "Sit comfortably. Breathe in slowly through your nose, then out gently. Repeat a few times. Stop if you feel uneasy.",
        "duration_minutes": 2,
        "activity_level": None,
        "equipment": None,
        "safety_notes": "This is not treatment for any medical condition. Stop if uncomfortable.",
        "source_name": "HMore general wellbeing guidance",
        "verification_status": "verified",
    },
    {
        "kind": "mindfulness",
        "category": "short_break",
        "title": "One-minute quiet break",
        "description": "A brief pause without screens.",
        "instructions": "Put your device down if safe to do so. Notice three things you can see. Stop whenever you want.",
        "duration_minutes": 1,
        "activity_level": None,
        "equipment": None,
        "safety_notes": "Optional activity only. Not a clinical intervention.",
        "source_name": "HMore general wellbeing guidance",
        "verification_status": "verified",
    },
)

NAVIGATOR_CATEGORIES = (
    {
        "id": "feeling_low",
        "title": "Feeling low or stressed",
        "description": "Community and listening support options. Not a diagnosis tool.",
        "maps_to_directory": ["mental_wellbeing_support", "community_wellbeing", "general_support"],
        "national_link_ids": ["samaritans", "nhs_111"],
    },
    {
        "id": "lonely",
        "title": "Wanting company or community",
        "description": "Social and community activity options.",
        "maps_to_directory": ["social_support", "community_activities", "community_wellbeing"],
        "national_link_ids": [],
    },
    {
        "id": "practical_advice",
        "title": "Practical local advice",
        "description": "Local advice and general support services.",
        "maps_to_directory": ["local_advice", "general_support"],
        "national_link_ids": ["nhs_111"],
    },
    {
        "id": "crisis",
        "title": "Immediate danger or crisis",
        "description": "Contact emergency or crisis services directly. HMore does not monitor emergencies.",
        "maps_to_directory": [],
        "national_link_ids": ["emergency_uk", "samaritans"],
    },
)
