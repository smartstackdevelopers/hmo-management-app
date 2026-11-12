"""F5.4 job matching: search-first scoring, sources, isolation helpers."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.core.config import Settings
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.job_matching.constants import SCORE_DISCLAIMER, SOURCE_STRUCTURED_IMPORT
from app.job_matching.embeddings import cosine_similarity, content_hash, embed_text
from app.job_matching.scoring import score_job
from app.job_matching.sources import NormalizedJob, source_status
from app.job_matching import service as job_matching
from app.job_matching.schemas import (
    AddToTrackerRequest,
    MatchExplainRequest,
    PreferencesUpdate,
    StructuredJobImport,
    StructuredJobImportBatch,
)
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id, user) -> OrganisationContext:
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=role,
        authorization=AuthorizationContext(
            user=user,
            memberships=[
                MembershipView(
                    membership_id=uuid.uuid4(),
                    role=role,
                    organisation_id=organisation_id,
                    status=MembershipStatus.ACTIVE,
                )
            ],
            active_organisation_id=organisation_id,
            active_role=role,
        ),
    )


def test_alembic_head_is_f54() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261112_4600_f72"]
    rev = script.get_revision("20261110_3700_f54")
    assert rev is not None
    assert rev.down_revision == "20261110_3600_f53"
    f55 = script.get_revision("20261110_3800_f55")
    assert f55 is not None
    assert f55.down_revision == "20261110_3700_f54"
    f61 = script.get_revision("20261111_3900_f61")
    assert f61 is not None
    assert f61.down_revision == "20261110_3800_f55"


def test_tenant_still_has_employment_prep_for_matching() -> None:
    assert role_has_permission(HMoreRole.TENANT, Permission.EMPLOYMENT_PREP_MANAGE_OWN)


def test_embeddings_are_deterministic_and_normalized() -> None:
    a = embed_text("customer service retail teamwork")
    b = embed_text("customer service retail teamwork")
    c = embed_text("unrelated nuclear physics")
    assert a == b
    assert abs(sum(v * v for v in a) - 1.0) < 1e-6
    assert cosine_similarity(a, b) > cosine_similarity(a, c)
    assert content_hash(["a", "b"]) == content_hash(["a", "b"])


def test_score_job_identifies_matching_and_missing_skills() -> None:
    profile = {
        "skills": [{"name": "Customer service"}, {"name": "Teamwork"}],
        "cv_skills": [],
        "career_interests": ["retail"],
        "preferred_categories": ["retail"],
        "preferred_locations": ["birmingham"],
        "preferred_employment_types": ["part_time"],
        "qualifications": [],
        "employment_goals": "Find retail work",
    }
    job = {
        "title": "Retail sales assistant",
        "description": "Help customers in a Birmingham shop",
        "location": "Birmingham",
        "employment_type": "part_time",
        "required_skills": ["Customer service", "Cash handling"],
        "embedding": embed_text("retail sales assistant customer service birmingham"),
    }
    result = score_job(profile=profile, job=job, profile_embedding=embed_text("customer service retail"))
    assert result["score"] > 40
    assert "Customer service" in result["matching_skills"]
    assert "Cash handling" in result["missing_skills"]
    assert any("Matching skills" in reason for reason in result["reasons"])


def test_score_does_not_use_protected_characteristic_fields() -> None:
    """Ensure scoring function signature only accepts employment-relevant profile keys."""
    profile = {
        "skills": [{"name": "Admin"}],
        "cv_skills": [],
        "career_interests": [],
        "preferred_categories": [],
        "preferred_locations": [],
        "preferred_employment_types": [],
        "qualifications": [],
        "employment_goals": None,
        "race": "should-be-ignored",
        "religion": "should-be-ignored",
        "disability": "should-be-ignored",
        "gender": "should-be-ignored",
    }
    job = {
        "title": "Administrator",
        "description": "Office admin",
        "location": None,
        "employment_type": None,
        "required_skills": ["Admin"],
        "embedding": embed_text("administrator office admin"),
    }
    result = score_job(profile=profile, job=job, profile_embedding=embed_text("admin"))
    blob = " ".join(result["reasons"]).lower()
    assert "race" not in blob
    assert "religion" not in blob
    assert "disability" not in blob
    assert "gender" not in blob


def test_source_status_reports_missing_credentials() -> None:
    settings = Settings(
        job_source_adzuna_app_id="",
        job_source_adzuna_app_key="",
        job_source_reed_api_key="",
    )
    status = source_status(settings)
    by_name = {item["source"]: item for item in status}
    assert by_name["adzuna"]["available"] is False
    assert by_name["reed"]["available"] is False
    assert by_name["hmore_catalogue"]["available"] is True


def test_normalized_job_builds_search_document_without_invention() -> None:
    job = NormalizedJob(
        external_id="1",
        source_name=SOURCE_STRUCTURED_IMPORT,
        source_url="https://example.com/jobs/1",
        title="Care assistant",
        employer_name="Local Care",
        description="Support residents",
        location="Leeds",
        employment_type="part_time",
        salary_text=None,
        required_skills=["Communication"],
        required_qualifications=[],
        experience_requirements=None,
        published_at=None,
        expires_at=None,
    )
    fields = job.to_persist_fields()
    assert "Care assistant" in fields["search_document"]
    assert fields["source_url"] == "https://example.com/jobs/1"
    assert "Invented" not in fields["search_document"]
    assert len(fields["embedding_json"]) > 0


def test_explain_falls_back_without_ai() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    fake_job = SimpleNamespace(
        id=uuid.uuid4(),
        title="Retail assistant",
        employer_name="Shop",
        location="Leeds",
        source_name="structured_import",
        score=70.0,
        reasons=["Matching skills: Teamwork"],
        missing_skills=["Till operation"],
        matching_skills=["Teamwork"],
        required_skills=["Teamwork"],
        salary_text=None,
        employment_type="part_time",
        description="Help customers",
        source_url="https://example.com/j",
        disclaimer=SCORE_DISCLAIMER,
    )
    with patch("app.job_matching.service.get_job", return_value=fake_job):
        with patch(
            "app.job_matching.service.get_matching_profile",
            return_value=SimpleNamespace(
                skills=[{"name": "Teamwork"}],
                career_interests=["retail"],
                employment_goals="Part-time work",
                cv_title="CV",
            ),
        ):
            with patch(
                "app.job_matching.ai_client.explain_job_match",
                side_effect=HTTPException(status_code=503, detail="unavailable"),
            ):
                out = job_matching.explain_match(
                    MagicMock(), ctx, MatchExplainRequest(job_id=fake_job.id)
                )
    assert out.requires_review is True
    assert "Retail assistant" in out.explanation
    assert "guarantee" in out.disclaimer.lower() or "advisory" in out.disclaimer.lower()
    assert out.provider == "deterministic_fallback"


def test_add_to_tracker_rejects_applied_without_confirmation() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    session = MagicMock()
    tenant = SimpleNamespace(id=uuid.uuid4())
    job = SimpleNamespace(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        employer_name="Shop",
        title="Assistant",
        location="Leeds",
        source_name="adzuna",
        source_url="https://example.com",
    )
    with patch("app.job_matching.service.resolve_own_tenant", return_value=tenant):
        session.get.return_value = job
        with pytest.raises(HTTPException) as exc:
            job_matching.add_job_to_tracker(
                session,
                ctx,
                AddToTrackerRequest(job_id=job.id, status="applied"),
            )
    assert exc.value.status_code == 422


@pytest.mark.postgres
def test_job_matching_flow_and_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, Tenant, User

    org = Organisation(name="Match Org", slug=f"f54-{unique_suffix}")
    other = Organisation(name="Other", slug=f"f54-o-{unique_suffix}")
    user = User(
        email=f"tenant-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_user = User(
        email=f"other-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, user, other_user, admin])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        user_id=user.id,
        preferred_name="Amina",
        status=RecordStatus.ACTIVE,
    )
    other_tenant = Tenant(
        organisation_id=other.id,
        user_id=other_user.id,
        preferred_name="Other",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([tenant, other_tenant])
    db_session.flush()
    ctx = _ctx(HMoreRole.TENANT, org.id, user)
    other_ctx = _ctx(HMoreRole.TENANT, other.id, other_user)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin)

    from app.employment import service as employment
    from app.employment.schemas import AssessmentUpdate, SkillItem

    employment.get_or_create_assessment(db_session, ctx)
    employment.update_assessment(
        db_session,
        ctx,
        AssessmentUpdate(
            skills=[SkillItem(name="Customer service", category="customer_service", level="intermediate")],
            career_interests=["retail"],
            employment_goals="Part-time retail",
        ),
    )
    job_matching.update_preferences(
        db_session,
        ctx,
        PreferencesUpdate(preferred_categories=["retail"], preferred_locations=["Birmingham"], preferred_employment_types=["part_time"]),
    )
    imported = job_matching.import_structured_jobs(
        db_session,
        admin_ctx,
        StructuredJobImportBatch(
            jobs=[
                StructuredJobImport(
                    external_id=f"job-{unique_suffix}",
                    title="Retail assistant",
                    employer_name="Local Shop",
                    description="Customer service in Birmingham",
                    location="Birmingham",
                    employment_type="part_time",
                    required_skills=["Customer service", "Till operation"],
                    source_url=f"https://example.com/jobs/{unique_suffix}",
                )
            ]
        ),
    )
    assert imported["imported"] == 1

    results = job_matching.search_jobs(
        db_session,
        ctx,
        q="retail",
        employer=None,
        location="Birmingham",
        employment_type="part_time",
        skills=None,
        sort="relevance",
        page=1,
        page_size=10,
        refresh_live=False,
    )
    assert results.total >= 1
    assert results.ai_used is False
    top = results.items[0]
    assert top.employer_name == "Local Shop"
    assert top.source_url
    assert top.score is not None
    assert "Till operation" in (top.missing_skills or [])

    saved = job_matching.save_job(db_session, ctx, top.id)
    assert saved["status"] in {"saved", "already_saved"}
    tracked = job_matching.add_job_to_tracker(
        db_session, ctx, AddToTrackerRequest(job_id=top.id, status="interested")
    )
    assert tracked["status"] in {"created", "already_tracked"}

    with pytest.raises(HTTPException):
        job_matching.get_job(db_session, other_ctx, top.id)
