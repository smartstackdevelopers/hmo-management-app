"""Role-to-permission matrix. Unlisted permissions are denied."""

from __future__ import annotations

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission

ROLE_PERMISSIONS: dict[HMoreRole, frozenset[Permission]] = {
    HMoreRole.SUPER_ADMIN: frozenset(
        {
            Permission.ORGANISATIONS_CREATE,
            Permission.ORGANISATIONS_READ,
            Permission.ORGANISATIONS_MANAGE,
            Permission.PLATFORM_SETTINGS_MANAGE,
            Permission.PLATFORM_MONITORING_READ,
            Permission.ROLE_ASSIGNMENTS_MANAGE,
            Permission.AUDIT_LOGS_READ,
            Permission.REPORTS_READ,
        }
    ),
    HMoreRole.ORGANISATION_ADMIN: frozenset(
        {
            Permission.ORGANISATIONS_READ,
            Permission.ORGANISATION_USERS_READ,
            Permission.ORGANISATION_USERS_MANAGE,
            Permission.ORGANISATION_SETTINGS_MANAGE,
            Permission.ORGANISATION_WORKFLOWS_MANAGE,
            Permission.APPLICATIONS_REVIEW,
            Permission.COMPLIANCE_CHECK,
            Permission.REPORTS_READ,
            Permission.AUDIT_LOGS_READ,
            Permission.OCCUPANCY_READ,
            Permission.OCCUPANCY_ALERTS_MANAGE,
            Permission.TENANTS_READ,
            Permission.TENANTS_MANAGE,
            Permission.PROPERTIES_READ,
            Permission.PROPERTIES_MANAGE,
            Permission.ROOMS_READ,
            Permission.ROOMS_MANAGE,
            Permission.ROLE_ASSIGNMENTS_MANAGE,
            Permission.WORK_ORDERS_APPROVE_ASSIGNED,
        }
    ),
    HMoreRole.LANDLORD: frozenset(
        {
            Permission.PROPERTIES_READ,
            Permission.PROPERTIES_MANAGE,
            Permission.ROOMS_READ,
            Permission.ROOMS_MANAGE,
            Permission.VACANCIES_MANAGE,
            Permission.TENANCIES_MANAGE,
            Permission.INSPECTIONS_MANAGE,
            Permission.RENT_RECORDS_MANAGE,
            Permission.REPAIRS_STATUS_READ,
            Permission.PROFILE_READ_OWN,
            Permission.PROFILE_UPDATE_OWN,
        }
    ),
    HMoreRole.TENANT: frozenset(
        {
            Permission.PROFILE_READ_OWN,
            Permission.PROFILE_UPDATE_OWN,
            Permission.TENANTS_READ,  # own linked tenant person record only
            Permission.PLANS_READ_OWN,
            Permission.DOCUMENTS_READ_OWN,
            Permission.REPAIRS_CREATE_OWN,
            Permission.COMPLAINTS_CREATE_OWN,
            Permission.SERVICES_DISCOVER,
            Permission.JOBS_DISCOVER,
            Permission.TRAINING_DISCOVER,
        }
    ),
    HMoreRole.SUPPORT_WORKER: frozenset(
        {
            Permission.SUPPORT_NOTES_READ_ASSIGNED,
            Permission.SUPPORT_NOTES_CREATE_ASSIGNED,
            Permission.SUPPORT_PLANS_MANAGE_ASSIGNED,
            Permission.VISITS_MANAGE_ASSIGNED,
            Permission.TASKS_MANAGE_ASSIGNED,
            Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED,
            Permission.INCIDENTS_CREATE_ASSIGNED,
            Permission.OCCUPANCY_READ,
            Permission.PROFILE_READ_OWN,
            Permission.TENANTS_READ,  # assigned-scope refinement remains F1.5+/later
            Permission.TENANCIES_MANAGE,  # assigned caseload only — resource check required
            Permission.PROPERTIES_READ,
            Permission.ROOMS_READ,
        }
    ),
    HMoreRole.MAINTENANCE_CONTRACTOR: frozenset(
        {
            Permission.WORK_ORDERS_READ_ASSIGNED,
            Permission.WORK_ORDERS_UPDATE_ASSIGNED,
            Permission.WORK_ORDERS_EVIDENCE_UPLOAD_ASSIGNED,
            Permission.WORK_ORDERS_SCHEDULE_ASSIGNED,
            Permission.WORK_ORDERS_APPROVE_ASSIGNED,
            Permission.PROFILE_READ_OWN,
            Permission.PROPERTIES_READ,
            Permission.ROOMS_READ,
        }
    ),
}


def permissions_for_role(role: HMoreRole) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def role_has_permission(role: HMoreRole, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
