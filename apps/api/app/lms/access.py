"""F8.4 LMS access."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.db.models.lms import LmsCourse, LmsEnrollment
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_learn(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.LMS_TENANT_LEARN)
        return
    require_permission(ctx.authorization, Permission.LMS_LEARN)


def require_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.LMS_MANAGE)


def assert_course_visible(ctx: OrganisationContext, course: LmsCourse, settings_tenant_enabled: bool) -> None:
    if course.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.status != "published":
        require_manage(ctx)
    if ctx.role == HMoreRole.TENANT:
        if course.staff_only or not course.tenant_visible or not settings_tenant_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course not available to tenants")


def assert_enrollment_owner(ctx: OrganisationContext, enrollment: LmsEnrollment) -> None:
    if enrollment.user_id != ctx.user_id and ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        require_permission(ctx.authorization, Permission.LMS_MANAGE)
        if enrollment.user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your enrollment")
