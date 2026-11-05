"""Exactly six approved HMore core roles. No additional core roles."""

from __future__ import annotations

from dataclasses import dataclass

from app.db.models.enums import HMoreRole

APPROVED_ROLE_COUNT = 6


@dataclass(frozen=True)
class RoleDefinition:
    role: HMoreRole
    display_name: str
    responsibilities: tuple[str, ...]
    platform_scoped: bool = False


ROLE_DEFINITIONS: dict[HMoreRole, RoleDefinition] = {
    HMoreRole.SUPER_ADMIN: RoleDefinition(
        role=HMoreRole.SUPER_ADMIN,
        display_name="Super Admin",
        platform_scoped=True,
        responsibilities=(
            "Creates and manages organisations",
            "Manages platform-wide settings",
            "Platform-wide monitoring",
        ),
    ),
    HMoreRole.ORGANISATION_ADMIN: RoleDefinition(
        role=HMoreRole.ORGANISATION_ADMIN,
        display_name="Organisation Admin",
        responsibilities=(
            "Manages organisation users, settings and workflows",
            "Reviews applications and decisions",
            "Performs compliance checks",
            "Accesses reports and audit logs",
            "Manages permitted room occupancy and alerts",
        ),
    ),
    HMoreRole.LANDLORD: RoleDefinition(
        role=HMoreRole.LANDLORD,
        display_name="Landlord",
        responsibilities=(
            "Manages own properties, rooms and vacancies",
            "Manages tenancies",
            "Manages inspections",
            "Maintains rent records",
            "Reviews repair status on own properties",
        ),
    ),
    HMoreRole.TENANT: RoleDefinition(
        role=HMoreRole.TENANT,
        display_name="Tenant",
        responsibilities=(
            "Accesses own profile, plan and documents",
            "Reports repairs and complaints",
            "Finds local services",
            "Finds jobs and training",
        ),
    ),
    HMoreRole.SUPPORT_WORKER: RoleDefinition(
        role=HMoreRole.SUPPORT_WORKER,
        display_name="Support Worker",
        responsibilities=(
            "Manages assigned notes and support plans",
            "Records visits and tasks",
            "Handles employment support",
            "Records skills, CVs, jobs and training activities",
            "Creates incident reports and follow-ups",
        ),
    ),
    HMoreRole.MAINTENANCE_CONTRACTOR: RoleDefinition(
        role=HMoreRole.MAINTENANCE_CONTRACTOR,
        display_name="Maintenance & Contractors",
        responsibilities=(
            "Accesses assigned work orders",
            "Updates repair status",
            "Uploads photos and completion evidence",
            "Manages permitted scheduling and job approvals",
        ),
    ),
}


def assert_exactly_six_roles() -> None:
    if len(HMoreRole) != APPROVED_ROLE_COUNT:
        raise RuntimeError(
            f"Expected {APPROVED_ROLE_COUNT} approved roles, found {len(HMoreRole)}"
        )
    if set(ROLE_DEFINITIONS) != set(HMoreRole):
        raise RuntimeError("ROLE_DEFINITIONS must cover every HMoreRole exactly once")


def parse_role(value: str) -> HMoreRole:
    try:
        return HMoreRole(value)
    except ValueError as exc:
        raise ValueError(f"Unknown role: {value}") from exc


assert_exactly_six_roles()
