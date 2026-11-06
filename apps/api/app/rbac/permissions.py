"""Central permission registry for HMore (F1.4). Deny-by-default outside this set."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Permission(StrEnum):
    # Platform (Super Admin)
    ORGANISATIONS_CREATE = "organisations.create"
    ORGANISATIONS_READ = "organisations.read"
    ORGANISATIONS_MANAGE = "organisations.manage"
    PLATFORM_SETTINGS_MANAGE = "platform.settings.manage"
    PLATFORM_MONITORING_READ = "platform.monitoring.read"

    # Organisation administration
    ORGANISATION_USERS_READ = "organisation.users.read"
    ORGANISATION_USERS_MANAGE = "organisation.users.manage"
    ORGANISATION_SETTINGS_MANAGE = "organisation.settings.manage"
    ORGANISATION_WORKFLOWS_MANAGE = "organisation.workflows.manage"
    APPLICATIONS_REVIEW = "applications.review"
    APPLICATIONS_MANAGE = "applications.manage"
    APPLICATIONS_CREATE_OWN = "applications.create.own"
    APPLICATIONS_READ_OWN = "applications.read.own"
    APPLICATIONS_CREATE_ASSIGNED = "applications.create.assigned"
    APPLICATIONS_READ_ASSIGNED = "applications.read.assigned"
    WAITING_LIST_MANAGE = "waiting_list.manage"
    WAITING_LIST_READ = "waiting_list.read"
    # F2.6 evidence checklists and packs
    EVIDENCE_MANAGE = "evidence.manage"
    EVIDENCE_MANAGE_ASSIGNED = "evidence.manage.assigned"
    EVIDENCE_READ_ASSIGNED = "evidence.read.assigned"
    EVIDENCE_READ_OWN = "evidence.read.own"
    EVIDENCE_REVIEW = "evidence.review"
    EVIDENCE_PACK_GENERATE = "evidence.pack.generate"
    COMPLIANCE_CHECK = "compliance.check"
    REPORTS_READ = "reports.read"
    AUDIT_LOGS_READ = "audit_logs.read"
    OCCUPANCY_READ = "occupancy.read"
    OCCUPANCY_ALERTS_MANAGE = "occupancy.alerts.manage"

    # Tenant person records (distinct from Tenant login role)
    TENANTS_READ = "tenants.read"
    TENANTS_MANAGE = "tenants.manage"

    # Private organisation file metadata (F1.8) — not public sharing
    FILES_READ = "files.read"
    FILES_MANAGE = "files.manage"

    # Housing / landlord
    PROPERTIES_READ = "properties.read"
    PROPERTIES_MANAGE = "properties.manage"
    ROOMS_READ = "rooms.read"
    ROOMS_MANAGE = "rooms.manage"
    VACANCIES_MANAGE = "vacancies.manage"
    TENANCIES_MANAGE = "tenancies.manage"
    INSPECTIONS_MANAGE = "inspections.manage"
    RENT_RECORDS_MANAGE = "rent_records.manage"
    REPAIRS_STATUS_READ = "repairs.status.read"

    # Tenant self-service
    PROFILE_READ_OWN = "profile.read.own"
    PROFILE_UPDATE_OWN = "profile.update.own"
    PLANS_READ_OWN = "plans.read.own"
    DOCUMENTS_READ_OWN = "documents.read.own"
    REPAIRS_CREATE_OWN = "repairs.create.own"
    COMPLAINTS_CREATE_OWN = "complaints.create.own"
    COMPLAINTS_READ_OWN = "complaints.read.own"
    COMPLAINTS_CREATE_ASSIGNED = "complaints.create.assigned"
    COMPLAINTS_READ_ASSIGNED = "complaints.read.assigned"
    COMPLAINTS_MANAGE = "complaints.manage"
    COMPLAINTS_ASSIGN = "complaints.assign"
    COMPLAINTS_PRIORITY_MANAGE = "complaints.priority.manage"
    COMPLAINTS_NOTES_INTERNAL = "complaints.notes.internal"
    COMPLAINTS_NOTES_ADD = "complaints.notes.add"
    COMPLAINTS_DEADLINES_MANAGE = "complaints.deadlines.manage"
    COMPLAINTS_ESCALATE = "complaints.escalate"
    COMPLAINTS_CLOSE = "complaints.close"
    COMPLAINTS_READ_PROPERTY = "complaints.read.property"
    SERVICES_DISCOVER = "services.discover"
    JOBS_DISCOVER = "jobs.discover"
    TRAINING_DISCOVER = "training.discover"
    # F2.3 staff training records (distinct from tenant TRAINING_DISCOVER)
    TRAINING_RECORDS_MANAGE = "training.records.manage"
    TRAINING_RECORDS_READ_OWN = "training.records.read.own"
    SAFEGUARDING_REMINDERS_MANAGE = "safeguarding.reminders.manage"
    SAFEGUARDING_REMINDERS_MANAGE_ASSIGNED = "safeguarding.reminders.manage.assigned"

    # Support worker (assigned-scope — enforced with resource checks / F1.5+)
    SUPPORT_NOTES_READ_ASSIGNED = "support_notes.read.assigned"
    SUPPORT_NOTES_CREATE_ASSIGNED = "support_notes.create.assigned"
    SUPPORT_PLANS_MANAGE_ASSIGNED = "support_plans.manage.assigned"
    VISITS_MANAGE_ASSIGNED = "visits.manage.assigned"
    TASKS_MANAGE_ASSIGNED = "tasks.manage.assigned"
    EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED = "employment_support.manage.assigned"
    INCIDENTS_CREATE_ASSIGNED = "incidents.create.assigned"
    INCIDENTS_READ_ASSIGNED = "incidents.read.assigned"
    INCIDENTS_MANAGE = "incidents.manage"
    WORKLOAD_READ = "workload.read"
    WORKLOAD_READ_OWN = "workload.read.own"

    # Maintenance & contractors (assigned-scope)
    WORK_ORDERS_READ_ASSIGNED = "work_orders.read.assigned"
    WORK_ORDERS_UPDATE_ASSIGNED = "work_orders.update.assigned"
    WORK_ORDERS_EVIDENCE_UPLOAD_ASSIGNED = "work_orders.evidence.upload.assigned"
    WORK_ORDERS_SCHEDULE_ASSIGNED = "work_orders.schedule.assigned"
    WORK_ORDERS_APPROVE_ASSIGNED = "work_orders.approve.assigned"

    # Role administration
    ROLE_ASSIGNMENTS_MANAGE = "role_assignments.manage"


@dataclass(frozen=True)
class PermissionMeta:
    permission: Permission
    purpose: str
    sensitive: bool = False


PERMISSION_CATALOG: dict[Permission, PermissionMeta] = {
    Permission.ORGANISATIONS_CREATE: PermissionMeta(
        Permission.ORGANISATIONS_CREATE, "Create organisations on the platform", True
    ),
    Permission.ORGANISATIONS_READ: PermissionMeta(
        Permission.ORGANISATIONS_READ, "Read organisation directory (platform or own org)"
    ),
    Permission.ORGANISATIONS_MANAGE: PermissionMeta(
        Permission.ORGANISATIONS_MANAGE, "Update or deactivate organisations", True
    ),
    Permission.PLATFORM_SETTINGS_MANAGE: PermissionMeta(
        Permission.PLATFORM_SETTINGS_MANAGE, "Change platform-wide settings", True
    ),
    Permission.PLATFORM_MONITORING_READ: PermissionMeta(
        Permission.PLATFORM_MONITORING_READ, "View platform monitoring and health"
    ),
    Permission.ORGANISATION_USERS_READ: PermissionMeta(
        Permission.ORGANISATION_USERS_READ, "List users in the organisation"
    ),
    Permission.ORGANISATION_USERS_MANAGE: PermissionMeta(
        Permission.ORGANISATION_USERS_MANAGE, "Invite/update organisation users", True
    ),
    Permission.ORGANISATION_SETTINGS_MANAGE: PermissionMeta(
        Permission.ORGANISATION_SETTINGS_MANAGE, "Change organisation settings", True
    ),
    Permission.ORGANISATION_WORKFLOWS_MANAGE: PermissionMeta(
        Permission.ORGANISATION_WORKFLOWS_MANAGE, "Configure organisation workflows"
    ),
    Permission.APPLICATIONS_REVIEW: PermissionMeta(
        Permission.APPLICATIONS_REVIEW, "Review housing applications and decisions"
    ),
    Permission.APPLICATIONS_MANAGE: PermissionMeta(
        Permission.APPLICATIONS_MANAGE, "Manage organisation housing applications", True
    ),
    Permission.APPLICATIONS_CREATE_OWN: PermissionMeta(
        Permission.APPLICATIONS_CREATE_OWN, "Create own housing applications"
    ),
    Permission.APPLICATIONS_READ_OWN: PermissionMeta(
        Permission.APPLICATIONS_READ_OWN, "Read own housing applications"
    ),
    Permission.APPLICATIONS_CREATE_ASSIGNED: PermissionMeta(
        Permission.APPLICATIONS_CREATE_ASSIGNED,
        "Create housing applications for assigned tenants",
    ),
    Permission.APPLICATIONS_READ_ASSIGNED: PermissionMeta(
        Permission.APPLICATIONS_READ_ASSIGNED,
        "Read housing applications for assigned tenants",
    ),
    Permission.WAITING_LIST_MANAGE: PermissionMeta(
        Permission.WAITING_LIST_MANAGE, "Manage organisation housing waiting list", True
    ),
    Permission.WAITING_LIST_READ: PermissionMeta(
        Permission.WAITING_LIST_READ, "Read organisation housing waiting list"
    ),
    Permission.EVIDENCE_MANAGE: PermissionMeta(
        Permission.EVIDENCE_MANAGE,
        "Manage organisation housing evidence checklists and associations",
        True,
    ),
    Permission.EVIDENCE_MANAGE_ASSIGNED: PermissionMeta(
        Permission.EVIDENCE_MANAGE_ASSIGNED,
        "Manage evidence for assigned housing applications",
        True,
    ),
    Permission.EVIDENCE_READ_ASSIGNED: PermissionMeta(
        Permission.EVIDENCE_READ_ASSIGNED,
        "Read evidence for assigned housing applications",
    ),
    Permission.EVIDENCE_READ_OWN: PermissionMeta(
        Permission.EVIDENCE_READ_OWN, "Read evidence for own housing applications"
    ),
    Permission.EVIDENCE_REVIEW: PermissionMeta(
        Permission.EVIDENCE_REVIEW, "Review and accept/reject housing evidence", True
    ),
    Permission.EVIDENCE_PACK_GENERATE: PermissionMeta(
        Permission.EVIDENCE_PACK_GENERATE,
        "Generate and download housing evidence packs",
        True,
    ),
    Permission.COMPLIANCE_CHECK: PermissionMeta(
        Permission.COMPLIANCE_CHECK, "Run compliance checks", True
    ),
    Permission.REPORTS_READ: PermissionMeta(Permission.REPORTS_READ, "Access organisation reports"),
    Permission.AUDIT_LOGS_READ: PermissionMeta(
        Permission.AUDIT_LOGS_READ, "Read audit logs", True
    ),
    Permission.OCCUPANCY_READ: PermissionMeta(
        Permission.OCCUPANCY_READ, "View permitted room occupancy counts", True
    ),
    Permission.OCCUPANCY_ALERTS_MANAGE: PermissionMeta(
        Permission.OCCUPANCY_ALERTS_MANAGE, "Manage occupancy alerts", True
    ),
    Permission.TENANTS_READ: PermissionMeta(
        Permission.TENANTS_READ, "Read organisation tenant person records", True
    ),
    Permission.TENANTS_MANAGE: PermissionMeta(
        Permission.TENANTS_MANAGE, "Create/update/archive tenant person records", True
    ),
    Permission.FILES_READ: PermissionMeta(
        Permission.FILES_READ, "Read private organisation file metadata and download", True
    ),
    Permission.FILES_MANAGE: PermissionMeta(
        Permission.FILES_MANAGE, "Upload and delete private organisation files", True
    ),
    Permission.PROPERTIES_READ: PermissionMeta(Permission.PROPERTIES_READ, "Read properties"),
    Permission.PROPERTIES_MANAGE: PermissionMeta(
        Permission.PROPERTIES_MANAGE, "Create/update properties (ownership rules apply)"
    ),
    Permission.ROOMS_READ: PermissionMeta(Permission.ROOMS_READ, "Read rooms"),
    Permission.ROOMS_MANAGE: PermissionMeta(Permission.ROOMS_MANAGE, "Create/update rooms"),
    Permission.VACANCIES_MANAGE: PermissionMeta(Permission.VACANCIES_MANAGE, "Manage vacancies"),
    Permission.TENANCIES_MANAGE: PermissionMeta(Permission.TENANCIES_MANAGE, "Manage tenancies"),
    Permission.INSPECTIONS_MANAGE: PermissionMeta(
        Permission.INSPECTIONS_MANAGE, "Manage inspections"
    ),
    Permission.RENT_RECORDS_MANAGE: PermissionMeta(
        Permission.RENT_RECORDS_MANAGE, "Maintain rent records", True
    ),
    Permission.REPAIRS_STATUS_READ: PermissionMeta(
        Permission.REPAIRS_STATUS_READ, "Review repair status on own properties"
    ),
    Permission.PROFILE_READ_OWN: PermissionMeta(
        Permission.PROFILE_READ_OWN, "Read own profile"
    ),
    Permission.PROFILE_UPDATE_OWN: PermissionMeta(
        Permission.PROFILE_UPDATE_OWN, "Update own profile"
    ),
    Permission.PLANS_READ_OWN: PermissionMeta(Permission.PLANS_READ_OWN, "Read own support plan"),
    Permission.DOCUMENTS_READ_OWN: PermissionMeta(
        Permission.DOCUMENTS_READ_OWN, "Read own documents"
    ),
    Permission.REPAIRS_CREATE_OWN: PermissionMeta(
        Permission.REPAIRS_CREATE_OWN, "Report own repairs"
    ),
    Permission.COMPLAINTS_CREATE_OWN: PermissionMeta(
        Permission.COMPLAINTS_CREATE_OWN, "Raise own complaints"
    ),
    Permission.COMPLAINTS_READ_OWN: PermissionMeta(
        Permission.COMPLAINTS_READ_OWN, "Read own complaints"
    ),
    Permission.COMPLAINTS_CREATE_ASSIGNED: PermissionMeta(
        Permission.COMPLAINTS_CREATE_ASSIGNED,
        "Create complaints for assigned tenants",
    ),
    Permission.COMPLAINTS_READ_ASSIGNED: PermissionMeta(
        Permission.COMPLAINTS_READ_ASSIGNED,
        "Read assigned or caseload complaints",
    ),
    Permission.COMPLAINTS_MANAGE: PermissionMeta(
        Permission.COMPLAINTS_MANAGE, "Manage organisation complaints workflow", True
    ),
    Permission.COMPLAINTS_ASSIGN: PermissionMeta(
        Permission.COMPLAINTS_ASSIGN, "Assign or reassign complaints"
    ),
    Permission.COMPLAINTS_PRIORITY_MANAGE: PermissionMeta(
        Permission.COMPLAINTS_PRIORITY_MANAGE, "Change complaint priority"
    ),
    Permission.COMPLAINTS_NOTES_INTERNAL: PermissionMeta(
        Permission.COMPLAINTS_NOTES_INTERNAL,
        "View internal complaint investigation notes",
        True,
    ),
    Permission.COMPLAINTS_NOTES_ADD: PermissionMeta(
        Permission.COMPLAINTS_NOTES_ADD, "Add complaint investigation or follow-up notes"
    ),
    Permission.COMPLAINTS_DEADLINES_MANAGE: PermissionMeta(
        Permission.COMPLAINTS_DEADLINES_MANAGE,
        "Update operational complaint deadlines",
        True,
    ),
    Permission.COMPLAINTS_ESCALATE: PermissionMeta(
        Permission.COMPLAINTS_ESCALATE, "Escalate complaints", True
    ),
    Permission.COMPLAINTS_CLOSE: PermissionMeta(
        Permission.COMPLAINTS_CLOSE, "Close or reopen complaints", True
    ),
    Permission.COMPLAINTS_READ_PROPERTY: PermissionMeta(
        Permission.COMPLAINTS_READ_PROPERTY,
        "Read complaints linked to permitted properties",
    ),
    Permission.SERVICES_DISCOVER: PermissionMeta(
        Permission.SERVICES_DISCOVER, "Find local services"
    ),
    Permission.JOBS_DISCOVER: PermissionMeta(Permission.JOBS_DISCOVER, "Find jobs"),
    Permission.TRAINING_DISCOVER: PermissionMeta(
        Permission.TRAINING_DISCOVER, "Find training"
    ),
    Permission.TRAINING_RECORDS_MANAGE: PermissionMeta(
        Permission.TRAINING_RECORDS_MANAGE,
        "Manage organisation staff training records",
        True,
    ),
    Permission.TRAINING_RECORDS_READ_OWN: PermissionMeta(
        Permission.TRAINING_RECORDS_READ_OWN, "Read own staff training records"
    ),
    Permission.SAFEGUARDING_REMINDERS_MANAGE: PermissionMeta(
        Permission.SAFEGUARDING_REMINDERS_MANAGE,
        "Manage organisation safeguarding reminders",
        True,
    ),
    Permission.SAFEGUARDING_REMINDERS_MANAGE_ASSIGNED: PermissionMeta(
        Permission.SAFEGUARDING_REMINDERS_MANAGE_ASSIGNED,
        "Manage assigned safeguarding reminders",
        True,
    ),
    Permission.SUPPORT_NOTES_READ_ASSIGNED: PermissionMeta(
        Permission.SUPPORT_NOTES_READ_ASSIGNED, "Read notes for assigned tenants"
    ),
    Permission.SUPPORT_NOTES_CREATE_ASSIGNED: PermissionMeta(
        Permission.SUPPORT_NOTES_CREATE_ASSIGNED, "Create notes for assigned tenants"
    ),
    Permission.SUPPORT_PLANS_MANAGE_ASSIGNED: PermissionMeta(
        Permission.SUPPORT_PLANS_MANAGE_ASSIGNED, "Manage assigned support plans"
    ),
    Permission.VISITS_MANAGE_ASSIGNED: PermissionMeta(
        Permission.VISITS_MANAGE_ASSIGNED, "Manage assigned visits"
    ),
    Permission.TASKS_MANAGE_ASSIGNED: PermissionMeta(
        Permission.TASKS_MANAGE_ASSIGNED, "Manage assigned tasks"
    ),
    Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED: PermissionMeta(
        Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED,
        "Manage employment support for assigned tenants",
    ),
    Permission.INCIDENTS_CREATE_ASSIGNED: PermissionMeta(
        Permission.INCIDENTS_CREATE_ASSIGNED, "Create incident reports for assigned work"
    ),
    Permission.INCIDENTS_READ_ASSIGNED: PermissionMeta(
        Permission.INCIDENTS_READ_ASSIGNED, "Read assigned or reported incidents"
    ),
    Permission.INCIDENTS_MANAGE: PermissionMeta(
        Permission.INCIDENTS_MANAGE, "Manage organisation incident reports", True
    ),
    Permission.WORKLOAD_READ: PermissionMeta(
        Permission.WORKLOAD_READ, "View organisation staff workload summaries"
    ),
    Permission.WORKLOAD_READ_OWN: PermissionMeta(
        Permission.WORKLOAD_READ_OWN, "View own workload summary"
    ),
    Permission.WORK_ORDERS_READ_ASSIGNED: PermissionMeta(
        Permission.WORK_ORDERS_READ_ASSIGNED, "Read assigned work orders"
    ),
    Permission.WORK_ORDERS_UPDATE_ASSIGNED: PermissionMeta(
        Permission.WORK_ORDERS_UPDATE_ASSIGNED, "Update assigned work orders"
    ),
    Permission.WORK_ORDERS_EVIDENCE_UPLOAD_ASSIGNED: PermissionMeta(
        Permission.WORK_ORDERS_EVIDENCE_UPLOAD_ASSIGNED,
        "Upload completion evidence for assigned jobs",
    ),
    Permission.WORK_ORDERS_SCHEDULE_ASSIGNED: PermissionMeta(
        Permission.WORK_ORDERS_SCHEDULE_ASSIGNED, "Schedule assigned jobs"
    ),
    Permission.WORK_ORDERS_APPROVE_ASSIGNED: PermissionMeta(
        Permission.WORK_ORDERS_APPROVE_ASSIGNED, "Approve assigned jobs where permitted"
    ),
    Permission.ROLE_ASSIGNMENTS_MANAGE: PermissionMeta(
        Permission.ROLE_ASSIGNMENTS_MANAGE,
        "Assign organisation roles within policy",
        True,
    ),
}


def parse_permission(value: str) -> Permission:
    try:
        return Permission(value)
    except ValueError as exc:
        raise ValueError(f"Unknown permission: {value}") from exc


def all_permission_ids() -> frozenset[str]:
    return frozenset(p.value for p in Permission)
