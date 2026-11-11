"""Approved job source adapters. Never scrape against terms; never invent jobs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.job_matching.constants import SOURCE_ADZUNA, SOURCE_REED
from app.job_matching.embeddings import content_hash, embed_text

logger = logging.getLogger("hmore.job_matching.sources")


@dataclass
class NormalizedJob:
    external_id: str
    source_name: str
    source_url: str | None
    title: str
    employer_name: str
    description: str | None
    location: str | None
    employment_type: str | None
    salary_text: str | None
    required_skills: list[str]
    required_qualifications: list[str]
    experience_requirements: str | None
    published_at: datetime | None
    expires_at: datetime | None

    def search_document(self) -> str:
        parts = [
            self.title,
            self.employer_name,
            self.location or "",
            self.employment_type or "",
            self.description or "",
            " ".join(self.required_skills),
            " ".join(self.required_qualifications),
        ]
        return " ".join(p for p in parts if p)

    def to_persist_fields(self) -> dict[str, Any]:
        doc = self.search_document()
        digest = content_hash([self.external_id, self.title, self.employer_name, doc, self.source_url or ""])
        return {
            "external_id": self.external_id,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "title": self.title[:255],
            "employer_name": self.employer_name[:255],
            "description": self.description,
            "location": (self.location or None),
            "employment_type": self.employment_type,
            "salary_text": self.salary_text,
            "required_skills_json": list(self.required_skills),
            "required_qualifications_json": list(self.required_qualifications),
            "experience_requirements": self.experience_requirements,
            "published_at": self.published_at,
            "expires_at": self.expires_at,
            "last_checked_at": datetime.now(timezone.utc),
            "is_active": True,
            "search_document": doc,
            "embedding_json": embed_text(doc),
            "content_hash": digest,
        }


def source_status(settings: Settings) -> list[dict[str, Any]]:
    adzuna_ok = bool((settings.job_source_adzuna_app_id or "").strip() and (settings.job_source_adzuna_app_key or "").strip())
    reed_ok = bool((settings.job_source_reed_api_key or "").strip())
    return [
        {
            "source": SOURCE_ADZUNA,
            "available": adzuna_ok,
            "detail": "Configured" if adzuna_ok else "Missing JOB_SOURCE_ADZUNA_APP_ID / JOB_SOURCE_ADZUNA_APP_KEY",
        },
        {
            "source": SOURCE_REED,
            "available": reed_ok,
            "detail": "Configured" if reed_ok else "Missing JOB_SOURCE_REED_API_KEY",
        },
        {
            "source": "hmore_catalogue",
            "available": True,
            "detail": "Organisation OpportunityListing jobs/training (published)",
        },
        {
            "source": "structured_import",
            "available": True,
            "detail": "API structured import for authorised staff",
        },
    ]


def _map_employment_type(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.lower()
    mapping = [
        ("full", "full_time"),
        ("part", "part_time"),
        ("temp", "temporary"),
        ("permanent", "permanent"),
        ("apprent", "apprenticeship"),
        ("intern", "internship"),
        ("volunteer", "volunteer"),
        ("contract", "temporary"),
    ]
    for needle, value in mapping:
        if needle in text:
            return value
    return None


def search_adzuna(
    settings: Settings,
    *,
    what: str | None,
    where: str | None,
    page: int = 1,
    results_per_page: int = 20,
) -> list[NormalizedJob]:
    app_id = (settings.job_source_adzuna_app_id or "").strip()
    app_key = (settings.job_source_adzuna_app_key or "").strip()
    if not app_id or not app_key:
        return []
    page = max(1, page)
    url = f"https://api.adzuna.com/v1/api/jobs/gb/search/{page}"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(50, max(1, results_per_page)),
        "content-type": "application/json",
    }
    if what:
        params["what"] = what
    if where:
        params["where"] = where
    try:
        with httpx.Client(timeout=settings.job_source_timeout_seconds) as client:
            response = client.get(url, params=params)
    except httpx.HTTPError as exc:
        logger.warning("adzuna unreachable: %s", type(exc).__name__)
        return []
    if response.status_code >= 400:
        logger.warning("adzuna HTTP %s", response.status_code)
        return []
    payload = response.json() if response.content else {}
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []
    out: list[NormalizedJob] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        company = item.get("company") if isinstance(item.get("company"), dict) else {}
        employer = str(company.get("display_name") or item.get("company") or "Unknown employer").strip()
        if not title or not employer:
            continue
        location_obj = item.get("location") if isinstance(item.get("location"), dict) else {}
        location = str(location_obj.get("display_name") or item.get("location") or "").strip() or None
        salary = None
        if item.get("salary_min") or item.get("salary_max"):
            salary = f"{item.get('salary_min') or ''}–{item.get('salary_max') or ''}".strip("–")
        category = item.get("category") if isinstance(item.get("category"), dict) else {}
        cat_label = str(category.get("label") or "").strip()
        skills = [cat_label] if cat_label else []
        created = None
        if item.get("created"):
            try:
                created = datetime.fromisoformat(str(item["created"]).replace("Z", "+00:00"))
            except ValueError:
                created = None
        out.append(
            NormalizedJob(
                external_id=str(item.get("id") or item.get("adref") or title),
                source_name=SOURCE_ADZUNA,
                source_url=str(item.get("redirect_url") or "") or None,
                title=title,
                employer_name=employer[:255],
                description=str(item.get("description") or "") or None,
                location=location,
                employment_type=_map_employment_type(str(item.get("contract_time") or item.get("contract_type") or "")),
                salary_text=salary,
                required_skills=skills,
                required_qualifications=[],
                experience_requirements=None,
                published_at=created,
                expires_at=None,
            )
        )
    return out


def search_reed(
    settings: Settings,
    *,
    keywords: str | None,
    location: str | None,
    results_to_take: int = 20,
) -> list[NormalizedJob]:
    api_key = (settings.job_source_reed_api_key or "").strip()
    if not api_key:
        return []
    params: dict[str, Any] = {"resultsToTake": min(100, max(1, results_to_take))}
    if keywords:
        params["keywords"] = keywords
    if location:
        params["locationName"] = location
    try:
        with httpx.Client(timeout=settings.job_source_timeout_seconds) as client:
            response = client.get(
                "https://www.reed.co.uk/api/1.0/search",
                params=params,
                auth=(api_key, ""),
            )
    except httpx.HTTPError as exc:
        logger.warning("reed unreachable: %s", type(exc).__name__)
        return []
    if response.status_code >= 400:
        logger.warning("reed HTTP %s", response.status_code)
        return []
    payload = response.json() if response.content else {}
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []
    out: list[NormalizedJob] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("jobTitle") or "").strip()
        employer = str(item.get("employerName") or "").strip() or "Unknown employer"
        if not title:
            continue
        job_id = str(item.get("jobId") or title)
        url = f"https://www.reed.co.uk/jobs/{job_id}" if item.get("jobId") else str(item.get("jobUrl") or "") or None
        salary = None
        if item.get("minimumSalary") or item.get("maximumSalary"):
            salary = f"{item.get('minimumSalary') or ''}–{item.get('maximumSalary') or ''}".strip("–")
        out.append(
            NormalizedJob(
                external_id=job_id,
                source_name=SOURCE_REED,
                source_url=url,
                title=title,
                employer_name=employer[:255],
                description=str(item.get("jobDescription") or "") or None,
                location=str(item.get("locationName") or "") or None,
                employment_type=_map_employment_type(str(item.get("jobType") or "")),
                salary_text=salary,
                required_skills=[],
                required_qualifications=[],
                experience_requirements=None,
                published_at=None,
                expires_at=None,
            )
        )
    return out
