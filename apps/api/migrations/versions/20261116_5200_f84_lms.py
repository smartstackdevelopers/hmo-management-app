"""F8.4 optional training LMS add-on tables.

Revision ID: 20261116_5200_f84
Revises: 20261115_5100_f83
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261116_5200_f84"
down_revision: Union[str, None] = "20261115_5100_f83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _policy(table: str) -> str:
    return f"""
    CREATE POLICY hmore_org_isolation ON {table}
      FOR ALL
      USING (
        current_setting('app.rls_bypass', true) = 'on'
        OR organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
      )
      WITH CHECK (
        current_setting('app.rls_bypass', true) = 'on'
        OR organisation_id::text = NULLIF(current_setting('app.organisation_id', true), '')
      );
    """


def _enable_rls(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(_policy(table)))


def upgrade() -> None:
    op.create_table(
        "organisation_lms_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("privacy_review_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("default_certificate_validity_days", sa.Integer(), nullable=True),
        sa.Column("tenant_courses_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reminder_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", name="uq_lms_settings_org"),
    )
    op.create_table(
        "lms_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "slug", name="uq_lms_category_slug"),
    )
    op.create_table(
        "lms_courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instructor", sa.String(255), nullable=True),
        sa.Column("learning_objectives", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("certificate_eligible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("pass_mark_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("certificate_validity_days", sa.Integer(), nullable=True),
        sa.Column("staff_only", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tenant_visible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["lms_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["image_file_id"], ["file_metadata.id"], ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_lms_courses_status"),
    )
    op.create_table(
        "lms_course_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["lms_courses.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "lms_lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("external_url", sa.String(512), nullable=True),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["module_id"], ["lms_course_modules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["file_metadata.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "content_type IN ('video', 'pdf', 'text', 'presentation', 'external_link', 'interactive', 'download')",
            name="ck_lms_lesson_content_type",
        ),
    )
    op.create_table(
        "lms_course_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_value", sa.String(128), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["lms_courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "target_type IN ('user', 'role', 'organisation', 'category')",
            name="ck_lms_assignment_target",
        ),
    )
    op.create_table(
        "lms_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="assigned"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["lms_courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "course_id", "user_id", name="uq_lms_enrollment_user_course"),
        sa.CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed')",
            name="ck_lms_enrollment_status",
        ),
    )
    op.create_table(
        "lms_lesson_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["lms_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lms_lessons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("enrollment_id", "lesson_id", name="uq_lms_lesson_completion"),
    )
    op.create_table(
        "lms_quizzes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("is_final_assessment", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pass_mark_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("attempt_limit", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["lms_courses.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "lms_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_type", sa.String(32), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("correct_answer", postgresql.JSONB(), nullable=True),
        sa.Column("requires_manual_marking", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quiz_id"], ["lms_quizzes.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "question_type IN ('multiple_choice', 'true_false', 'multiple_answer', 'short_answer', 'knowledge_check')",
            name="ck_lms_question_type",
        ),
    )
    op.create_table(
        "lms_assessment_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score_percent", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quiz_id"], ["lms_quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["lms_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('submitted', 'pending_manual', 'marked', 'void')",
            name="ck_lms_attempt_status",
        ),
    )
    op.create_table(
        "lms_assessment_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer", postgresql.JSONB(), nullable=False),
        sa.Column("auto_scored", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attempt_id"], ["lms_assessment_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["lms_questions.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "lms_certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("certificate_number", sa.String(32), nullable=False),
        sa.Column("verification_reference", sa.String(64), nullable=False),
        sa.Column("learner_name", sa.String(255), nullable=False),
        sa.Column("course_title", sa.String(255), nullable=False),
        sa.Column("provider_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="issued"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["lms_enrollments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organisation_id", "certificate_number", name="uq_lms_certificate_number"),
        sa.UniqueConstraint("organisation_id", "verification_reference", name="uq_lms_certificate_verify"),
        sa.CheckConstraint(
            "status IN ('issued', 'valid', 'expired', 'revoked')",
            name="ck_lms_certificate_status",
        ),
    )
    tables = (
        "organisation_lms_settings",
        "lms_categories",
        "lms_courses",
        "lms_course_modules",
        "lms_lessons",
        "lms_course_assignments",
        "lms_enrollments",
        "lms_lesson_completions",
        "lms_quizzes",
        "lms_questions",
        "lms_assessment_attempts",
        "lms_assessment_answers",
        "lms_certificates",
    )
    for table in tables:
        _enable_rls(table)


def downgrade() -> None:
    op.drop_table("lms_certificates")
    op.drop_table("lms_assessment_answers")
    op.drop_table("lms_assessment_attempts")
    op.drop_table("lms_questions")
    op.drop_table("lms_quizzes")
    op.drop_table("lms_lesson_completions")
    op.drop_table("lms_enrollments")
    op.drop_table("lms_course_assignments")
    op.drop_table("lms_lessons")
    op.drop_table("lms_course_modules")
    op.drop_table("lms_courses")
    op.drop_table("lms_categories")
    op.drop_table("organisation_lms_settings")
