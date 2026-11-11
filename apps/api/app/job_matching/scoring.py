"""Transparent relevance scoring from tenant profile vs job listing.

Never uses protected characteristics. Never invents skills or requirements.
"""

from __future__ import annotations

from typing import Any

from app.job_matching.embeddings import cosine_similarity, tokenize


def _norm(value: str) -> str:
    return " ".join(tokenize(value))


def build_tenant_profile_text(profile: dict[str, Any]) -> str:
    skills = [str(s.get("name") or "") for s in profile.get("skills") or [] if isinstance(s, dict)]
    interests = [str(i) for i in profile.get("career_interests") or []]
    goals = [str(profile.get("employment_goals") or "")]
    quals = []
    for item in profile.get("qualifications") or []:
        if isinstance(item, dict):
            quals.append(" ".join(str(v) for v in item.values() if v))
        else:
            quals.append(str(item))
    cv_skills = [str(s.get("name") or "") for s in profile.get("cv_skills") or [] if isinstance(s, dict)]
    return " ".join(skills + cv_skills + interests + goals + quals + list(profile.get("preferred_categories") or []))


def score_job(*, profile: dict[str, Any], job: dict[str, Any], profile_embedding: list[float]) -> dict[str, Any]:
    tenant_skills = {
        _norm(str(s.get("name") or ""))
        for s in (profile.get("skills") or []) + (profile.get("cv_skills") or [])
        if isinstance(s, dict) and s.get("name")
    }
    tenant_skills.discard("")
    required = []
    for item in job.get("required_skills") or []:
        if isinstance(item, str) and item.strip():
            required.append(item.strip())
        elif isinstance(item, dict) and item.get("name"):
            required.append(str(item["name"]).strip())
    required_norm = {_norm(r) for r in required}
    required_norm.discard("")

    matching = sorted({r for r in required if _norm(r) in tenant_skills})
    missing = sorted({r for r in required if _norm(r) not in tenant_skills})

    skill_score = 0.0
    if required_norm:
        skill_score = len(matching) / max(len(required_norm), 1)
    else:
        # No explicit skills on listing — use title/description token overlap only.
        job_tokens = set(tokenize(f"{job.get('title') or ''} {job.get('description') or ''}"))
        skill_score = min(1.0, len(tenant_skills & job_tokens) / 5.0) if tenant_skills else 0.0

    interests = {_norm(str(i)) for i in profile.get("career_interests") or []}
    categories = {_norm(str(i)) for i in profile.get("preferred_categories") or []}
    title_tokens = set(tokenize(str(job.get("title") or "")))
    interest_hit = bool((interests | categories) & title_tokens) or any(
        i and i in _norm(str(job.get("description") or "")) for i in (interests | categories) if len(i) > 3
    )
    interest_score = 1.0 if interest_hit else 0.0

    pref_types = {_norm(str(t)) for t in profile.get("preferred_employment_types") or []}
    job_type = _norm(str(job.get("employment_type") or ""))
    type_score = 1.0 if (not pref_types or (job_type and job_type in pref_types)) else 0.2

    pref_locations = {_norm(str(loc)) for loc in profile.get("preferred_locations") or []}
    job_loc = _norm(str(job.get("location") or ""))
    location_score = 1.0
    if pref_locations and job_loc:
        location_score = 1.0 if any(p in job_loc or job_loc in p for p in pref_locations) else 0.3
    elif pref_locations and not job_loc:
        location_score = 0.5

    emb = job.get("embedding") or []
    semantic = cosine_similarity(profile_embedding, emb) if emb and profile_embedding else 0.0
    semantic = max(0.0, min(1.0, (semantic + 1.0) / 2.0))  # map [-1,1] -> [0,1]

    # Weighted blend — transparent and preference-driven only.
    score = (
        0.40 * skill_score
        + 0.20 * interest_score
        + 0.15 * type_score
        + 0.10 * location_score
        + 0.15 * semantic
    )
    score = round(max(0.0, min(1.0, score)) * 100.0, 1)

    reasons: list[str] = []
    if matching:
        reasons.append(f"Matching skills: {', '.join(matching[:8])}")
    if missing:
        reasons.append(f"Unconfirmed or missing skills on your profile: {', '.join(missing[:8])}")
    if interest_hit:
        reasons.append("Title/description aligns with your career interests or preferred categories")
    if job.get("employment_type") and pref_types and job_type in pref_types:
        reasons.append(f"Employment type matches preference ({job.get('employment_type')})")
    if location_score >= 0.9 and pref_locations:
        reasons.append("Location matches your preferred locations")
    if not reasons:
        reasons.append("Limited overlap with your saved skills — review the listing carefully")

    return {
        "score": score,
        "matching_skills": matching,
        "missing_skills": missing,
        "reasons": reasons,
        "components": {
            "skills": round(skill_score, 3),
            "interests": interest_score,
            "employment_type": round(type_score, 3),
            "location": round(location_score, 3),
            "semantic": round(semantic, 3),
        },
    }
