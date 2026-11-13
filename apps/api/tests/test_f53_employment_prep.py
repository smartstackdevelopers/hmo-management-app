"""F5.3 employment preparation: skills, CV, applications, isolation."""

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
from app.employment import service as employment
from app.employment.constants import CV_TEMPLATES, SKILL_CATEGORIES
from app.employment.pdf import build_cv_pdf
from app.employment.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    AssessmentUpdate,
    CareerGoalWrite,
    CvAssistRequest,
    CvCreate,
    CvUpdate,
    SkillItem,
)
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.storage.memory import InMemoryStorage
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


def test_alembic_head_is_f53() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261118_5400_f86"]
    rev = script.get_revision("20261110_3600_f53")
    assert rev is not None
    assert rev.down_revision == "20261110_3500_f52"


def test_tenant_has_employment_prep_permission() -> None:
    assert role_has_permission(HMoreRole.TENANT, Permission.EMPLOYMENT_PREP_MANAGE_OWN)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.EMPLOYMENT_PREP_READ_ASSIGNED)


def test_skill_categories_and_templates() -> None:
    cats = employment.list_skill_categories()
    assert "communication" in cats["categories"]
    assert set(SKILL_CATEGORIES).issubset(set(cats["categories"]))
    assert "simple_professional" in CV_TEMPLATES


def test_cv_pdf_does_not_invent_content() -> None:
    pdf = build_cv_pdf(
        title="Demo CV",
        template_id="entry_level",
        content={"personal_profile": "Hardworking team member", "skills": [{"name": "Teamwork"}]},
        section_order=["personal_profile", "skills"],
    )
    assert pdf.startswith(b"%PDF")
    assert b"Hardworking team member" in pdf
    assert b"Teamwork" in pdf
    assert b"Invented Job" not in pdf


def test_ai_assist_falls_back_without_gateway() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    fake_tenant = SimpleNamespace(id=uuid.uuid4())
    with patch("app.employment.service.resolve_own_tenant", return_value=fake_tenant):
        with patch(
            "app.employment.ai_client.rewrite_cv_text",
            side_effect=HTTPException(status_code=503, detail="unavailable"),
        ):
            out = employment.assist_cv_wording(
                MagicMock(),
                ctx,
                CvAssistRequest(field="personal_profile", original_text="  hello team  "),
            )
    assert out.requires_approval is True
    assert out.original_text == "hello team"
    assert out.suggested_text.startswith("Hello team")
    assert "invent" in out.disclaimer.lower()
    assert out.provider == "local_cleanup"


@pytest.mark.postgres
def test_employment_prep_flow_and_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, Tenant, User

    org = Organisation(name="Emp Org", slug=f"f53-{unique_suffix}")
    other = Organisation(name="Other", slug=f"f53-o-{unique_suffix}")
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
    db_session.add_all([org, other, user, other_user])
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
    storage = InMemoryStorage()
    settings = Settings(
        storage_provider="memory",
        storage_allowed_content_types="application/pdf",
        storage_max_upload_bytes=2_000_000,
    )

    assessment = employment.get_or_create_assessment(db_session, ctx)
    assert assessment.status == "in_progress"
    updated = employment.update_assessment(
        db_session,
        ctx,
        AssessmentUpdate(
            skills=[
                SkillItem(
                    name="Customer service",
                    category="customer_service",
                    level="intermediate",
                    is_custom=False,
                ),
                SkillItem(name="Urdu", category="languages", level="advanced", is_custom=False),
            ],
            career_interests=["retail", "admin"],
            employment_goals="Find stable part-time work",
            education=[{"institution": "Local college", "qualification": "Level 2", "year": "2020"}],
            experiences=[
                {
                    "kind": "volunteer",
                    "title": "Community helper",
                    "organisation": "Food bank",
                    "description": "Supported visitors",
                }
            ],
        ),
    )
    assert updated.completion_percent > 0
    assert updated.summary["skill_count"] == 2

    cv = employment.create_cv(
        db_session,
        ctx,
        CvCreate(title=f"Retail CV {unique_suffix}", template_id="skills_based", seed_from_assessment=True),
    )
    assert cv.content["skills"]
    assert any(item.get("name") == "Customer service" for item in cv.content["skills"])
    edited = employment.update_cv(
        db_session,
        ctx,
        cv.id,
        CvUpdate(
            content={
                "personal_profile": "Reliable team member with retail interest",
                "skills": cv.content["skills"],
            }
        ),
    )
    assert edited.version == 2
    assert edited.completion["percent"] >= 40
    assert edited.content.get("volunteer")  # seed retained via merge

    pdf_cv = employment.generate_cv_pdf(
        db_session, ctx, cv.id, settings=settings, backend=storage
    )
    assert pdf_cv.pdf_file_id is not None
    response = employment.download_cv_pdf(
        db_session, ctx, cv.id, settings=settings, backend=storage
    )
    assert response.media_type == "application/pdf"
    assert b"%PDF" in response.body

    dup = employment.duplicate_cv(db_session, ctx, cv.id)
    assert dup.id != cv.id
    assert "copy" in dup.title.lower()

    app = employment.create_application(
        db_session,
        ctx,
        ApplicationCreate(
            employer_name="Local Shop",
            job_title="Sales assistant",
            job_location="Birmingham",
            linked_cv_id=cv.id,
            status="preparing",
        ),
    )
    moved = employment.update_application(
        db_session, ctx, app.id, ApplicationUpdate(status="applied")
    )
    assert moved.status == "applied"
    dash = employment.application_dashboard(db_session, ctx)
    assert dash.total >= 1
    assert dash.submitted >= 1

    goal = employment.create_career_goal(
        db_session,
        ctx,
        CareerGoalWrite(title="Build retail experience", status="pending"),
    )
    roadmap = employment.get_roadmap(db_session, ctx)
    assert goal.title in [item.title for item in roadmap.goals]

    with pytest.raises(HTTPException) as denied:
        employment.get_cv(db_session, other_ctx, cv.id)
    assert denied.value.status_code in {403, 404}

