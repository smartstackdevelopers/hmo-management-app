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
    MAINTENANCE_MANAGE = "maintenance.manage"
    MAINTENANCE_CREATE_OWN = "maintenance.create.own"
    MAINTENANCE_READ_OWN = "maintenance.read.own"
    MAINTENANCE_CREATE_ASSIGNED = "maintenance.create.assigned"
    MAINTENANCE_READ_ASSIGNED = "maintenance.read.assigned"
    MAINTENANCE_READ_PROPERTY = "maintenance.read.property"
    MAINTENANCE_PRIORITY_MANAGE = "maintenance.priority.manage"
    MAINTENANCE_ASSIGN = "maintenance.assign"
    MAINTENANCE_SCHEDULE = "maintenance.schedule"
    MAINTENANCE_APPROVE = "maintenance.approve"
    MAINTENANCE_NOTES_ADD = "maintenance.notes.add"
    MAINTENANCE_PHOTO_UPLOAD = "maintenance.photo.upload"
    MAINTENANCE_PHOTO_READ = "maintenance.photo.read"
    MAINTENANCE_COMPLETE = "maintenance.complete"
    MAINTENANCE_CLOSE_REOPEN = "maintenance.close"
    MAINTENANCE_EMERGENCY_MANAGE = "maintenance.emergency.manage"
    # F2.9 tenant timeline, meetings, appointments, follow-ups
    TIMELINE_READ = "timeline.read"
    TIMELINE_READ_OWN = "timeline.read.own"
    TIMELINE_READ_LANDLORD = "timeline.read.landlord"
    TIMELINE_MEETING_CREATE = "timeline.meeting.create"
    TIMELINE_MEETING_READ = "timeline.meeting.read"
    TIMELINE_MEETING_NOTES_INTERNAL = "timeline.meeting.notes.internal"
    TIMELINE_APPOINTMENT_MANAGE = "timeline.appointment.manage"
    TIMELINE_FOLLOWUP_MANAGE = "timeline.followup.manage"
    TIMELINE_FOLLOWUP_READ_ASSIGNED = "timeline.followup.read.assigned"
    TIMELINE_NEEDS_MANAGE = "timeline.needs.manage"
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
    # F2.10 structured support plans (goals, milestones, reviews, exports)
    SUPPORT_PLAN_READ = "support_plans.read"
    SUPPORT_PLAN_READ_OWN = "support_plans.read.own"
    SUPPORT_PLAN_MANAGE = "support_plans.manage"
    SUPPORT_PLAN_NOTES_INTERNAL = "support_plans.notes.internal"
    SUPPORT_PLAN_EXPORT = "support_plans.export"
    SUPPORT_PLAN_REVIEW_FINALISE = "support_plans.review.finalise"
    # F2.11 managed documents (central DMS — not F2.6 evidence files)
    DOCUMENTS_READ_META = "documents.read.meta"
    DOCUMENTS_READ_CONTENT = "documents.read.content"
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_VERSION = "documents.version"
    DOCUMENTS_ARCHIVE = "documents.archive"
    DOCUMENTS_MANAGE_EXPIRY = "documents.manage.expiry"
    DOCUMENTS_MANAGE_RETENTION = "documents.manage.retention"
    DOCUMENTS_VIEW_RESTRICTED = "documents.view.restricted"
    DOCUMENTS_ACCESS_REQUEST = "documents.access.request"
    DOCUMENTS_ACCESS_APPROVE = "documents.access.approve"
    DOCUMENTS_SIGN_REQUEST = "documents.sign.request"
    DOCUMENTS_SIGN_COMPLETE = "documents.sign.complete"
    DOCUMENTS_MANAGE_CATEGORIES = "documents.manage.categories"
    DOCUMENTS_MANAGE_SETTINGS = "documents.manage.settings"
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
    Permission.MAINTENANCE_MANAGE: PermissionMeta(
        Permission.MAINTENANCE_MANAGE, "Manage organisation maintenance requests", True
    ),
    Permission.MAINTENANCE_CREATE_OWN: PermissionMeta(
        Permission.MAINTENANCE_CREATE_OWN, "Submit maintenance requests for own tenancy"
    ),
    Permission.MAINTENANCE_READ_OWN: PermissionMeta(
        Permission.MAINTENANCE_READ_OWN, "Read own maintenance requests"
    ),
    Permission.MAINTENANCE_CREATE_ASSIGNED: PermissionMeta(
        Permission.MAINTENANCE_CREATE_ASSIGNED,
        "Create maintenance requests for assigned tenants",
    ),
    Permission.MAINTENANCE_READ_ASSIGNED: PermissionMeta(
        Permission.MAINTENANCE_READ_ASSIGNED,
        "Read maintenance requests for assigned tenants",
    ),
    Permission.MAINTENANCE_READ_PROPERTY: PermissionMeta(
        Permission.MAINTENANCE_READ_PROPERTY,
        "Read maintenance requests for authorised properties",
    ),
    Permission.MAINTENANCE_PRIORITY_MANAGE: PermissionMeta(
        Permission.MAINTENANCE_PRIORITY_MANAGE, "Change maintenance priority", True
    ),
    Permission.MAINTENANCE_ASSIGN: PermissionMeta(
        Permission.MAINTENANCE_ASSIGN, "Assign maintenance to staff or contractor"
    ),
    Permission.MAINTENANCE_SCHEDULE: PermissionMeta(
        Permission.MAINTENANCE_SCHEDULE, "Schedule maintenance visits"
    ),
    Permission.MAINTENANCE_APPROVE: PermissionMeta(
        Permission.MAINTENANCE_APPROVE, "Approve or reject maintenance work requests", True
    ),
    Permission.MAINTENANCE_NOTES_ADD: PermissionMeta(
        Permission.MAINTENANCE_NOTES_ADD, "Add internal or tenant-visible maintenance notes"
    ),
    Permission.MAINTENANCE_PHOTO_UPLOAD: PermissionMeta(
        Permission.MAINTENANCE_PHOTO_UPLOAD, "Upload maintenance photographs", True
    ),
    Permission.MAINTENANCE_PHOTO_READ: PermissionMeta(
        Permission.MAINTENANCE_PHOTO_READ, "View maintenance photographs", True
    ),
    Permission.MAINTENANCE_COMPLETE: PermissionMeta(
        Permission.MAINTENANCE_COMPLETE, "Record maintenance completion", True
    ),
    Permission.MAINTENANCE_CLOSE_REOPEN: PermissionMeta(
        Permission.MAINTENANCE_CLOSE_REOPEN, "Close or reopen maintenance requests", True
    ),
    Permission.MAINTENANCE_EMERGENCY_MANAGE: PermissionMeta(
        Permission.MAINTENANCE_EMERGENCY_MANAGE,
        "Manage emergency gas/fire instruction content (org-approved text only)",
        True,
    ),
    Permission.TIMELINE_READ: PermissionMeta(
        Permission.TIMELINE_READ, "Read tenant timelines (aggregated, scope-enforced)", True
    ),
    Permission.TIMELINE_READ_OWN: PermissionMeta(
        Permission.TIMELINE_READ_OWN, "Read own tenant timeline summary"
    ),
    Permission.TIMELINE_READ_LANDLORD: PermissionMeta(
        Permission.TIMELINE_READ_LANDLORD,
        "Read property-scoped tenant timeline (limited activity types)",
    ),
    Permission.TIMELINE_MEETING_CREATE: PermissionMeta(
        Permission.TIMELINE_MEETING_CREATE, "Schedule tenant meetings", True
    ),
    Permission.TIMELINE_MEETING_READ: PermissionMeta(
        Permission.TIMELINE_MEETING_READ, "View tenant meetings"
    ),
    Permission.TIMELINE_MEETING_NOTES_INTERNAL: PermissionMeta(
        Permission.TIMELINE_MEETING_NOTES_INTERNAL, "View confidential meeting notes", True
    ),
    Permission.TIMELINE_APPOINTMENT_MANAGE: PermissionMeta(
        Permission.TIMELINE_APPOINTMENT_MANAGE, "Manage tenant appointments", True
    ),
    Permission.TIMELINE_FOLLOWUP_MANAGE: PermissionMeta(
        Permission.TIMELINE_FOLLOWUP_MANAGE, "Manage tenant follow-ups", True
    ),
    Permission.TIMELINE_FOLLOWUP_READ_ASSIGNED: PermissionMeta(
        Permission.TIMELINE_FOLLOWUP_READ_ASSIGNED, "Read follow-ups assigned to you"
    ),
    Permission.TIMELINE_NEEDS_MANAGE: PermissionMeta(
        Permission.TIMELINE_NEEDS_MANAGE, "Record tenant needs and goals (non-clinical)", True
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
    Permission.SUPPORT_PLAN_READ: PermissionMeta(
        Permission.SUPPORT_PLAN_READ,
        "Read structured support plans, goals, and reviews within scope",
        True,
    ),
    Permission.SUPPORT_PLAN_READ_OWN: PermissionMeta(
        Permission.SUPPORT_PLAN_READ_OWN,
        "Read own tenant-linked structured support plans (permitted fields only)",
    ),
    Permission.SUPPORT_PLAN_MANAGE: PermissionMeta(
        Permission.SUPPORT_PLAN_MANAGE,
        "Create and update structured support plans for authorised tenants",
        True,
    ),
    Permission.SUPPORT_PLAN_NOTES_INTERNAL: PermissionMeta(
        Permission.SUPPORT_PLAN_NOTES_INTERNAL,
        "View internal notes on support plans, goals, milestones, and reviews",
        True,
    ),
    Permission.SUPPORT_PLAN_EXPORT: PermissionMeta(
        Permission.SUPPORT_PLAN_EXPORT,
        "Generate and download structured support-plan progress exports",
        True,
    ),
    Permission.SUPPORT_PLAN_REVIEW_FINALISE: PermissionMeta(
        Permission.SUPPORT_PLAN_REVIEW_FINALISE,
        "Finalise weekly or monthly support plan reviews",
        True,
    ),
    Permission.DOCUMENTS_READ_META: PermissionMeta(
        Permission.DOCUMENTS_READ_META,
        "View managed document metadata within authorised scope",
        True,
    ),
    Permission.DOCUMENTS_READ_CONTENT: PermissionMeta(
        Permission.DOCUMENTS_READ_CONTENT,
        "Download managed document file content within authorised scope",
        True,
    ),
    Permission.DOCUMENTS_UPLOAD: PermissionMeta(
        Permission.DOCUMENTS_UPLOAD, "Upload new managed documents or versions", True
    ),
    Permission.DOCUMENTS_VERSION: PermissionMeta(
        Permission.DOCUMENTS_VERSION, "Upload new versions of managed documents", True
    ),
    Permission.DOCUMENTS_ARCHIVE: PermissionMeta(
        Permission.DOCUMENTS_ARCHIVE, "Archive managed documents", True
    ),
    Permission.DOCUMENTS_MANAGE_EXPIRY: PermissionMeta(
        Permission.DOCUMENTS_MANAGE_EXPIRY, "Set or change document expiry dates", True
    ),
    Permission.DOCUMENTS_MANAGE_RETENTION: PermissionMeta(
        Permission.DOCUMENTS_MANAGE_RETENTION, "Manage retention metadata and reviews", True
    ),
    Permission.DOCUMENTS_VIEW_RESTRICTED: PermissionMeta(
        Permission.DOCUMENTS_VIEW_RESTRICTED,
        "View confidential or restricted managed documents",
        True,
    ),
    Permission.DOCUMENTS_ACCESS_REQUEST: PermissionMeta(
        Permission.DOCUMENTS_ACCESS_REQUEST, "Submit access requests for managed documents"
    ),
    Permission.DOCUMENTS_ACCESS_APPROVE: PermissionMeta(
        Permission.DOCUMENTS_ACCESS_APPROVE, "Approve or reject document access requests", True
    ),
    Permission.DOCUMENTS_SIGN_REQUEST: PermissionMeta(
        Permission.DOCUMENTS_SIGN_REQUEST, "Create internal signature requests", True
    ),
    Permission.DOCUMENTS_SIGN_COMPLETE: PermissionMeta(
        Permission.DOCUMENTS_SIGN_COMPLETE,
        "Complete or decline in-platform signature (not qualified e-signature)",
        True,
    ),
    Permission.DOCUMENTS_MANAGE_CATEGORIES: PermissionMeta(
        Permission.DOCUMENTS_MANAGE_CATEGORIES, "Manage organisation document categories", True
    ),
    Permission.DOCUMENTS_MANAGE_SETTINGS: PermissionMeta(
        Permission.DOCUMENTS_MANAGE_SETTINGS,
        "Manage organisation document reminder and retention defaults",
        True,
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
