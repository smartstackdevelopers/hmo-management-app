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
    # F2.14 granular reporting (reports.read retained for backward compatibility)
    REPORTS_DASHBOARD_VIEW = "reports.dashboard.view"
    REPORTS_HOUSING_VIEW = "reports.housing.view"
    REPORTS_COMPLAINTS_VIEW = "reports.complaints.view"
    REPORTS_CASELOAD_VIEW = "reports.caseload.view"
    REPORTS_OCCUPANCY_VIEW = "reports.occupancy.view"
    REPORTS_PLANS_VIEW = "reports.plans.view"
    REPORTS_SCHEDULE_MANAGE = "reports.schedule.manage"
    REPORTS_ALERTS_VIEW = "reports.alerts.view"
    AUTOMATION_RULES_READ = "automation.rules.read"
    AUTOMATION_RULES_MANAGE = "automation.rules.manage"
    AUTOMATION_RUNS_READ = "automation.runs.read"
    AUTOMATION_ESCALATIONS_MANAGE = "automation.escalations.manage"
    INTEGRATIONS_READ = "integrations.read"
    INTEGRATIONS_MANAGE = "integrations.manage"
    # F7.2 privacy / GDPR management (technical records — not legal sign-off)
    PRIVACY_READ = "privacy.read"
    PRIVACY_MANAGE = "privacy.manage"
    # F7.3 backup administration (platform)
    BACKUP_READ = "backup.read"
    BACKUP_MANAGE = "backup.manage"
    BACKUP_RESTORE_DRILL = "backup.restore_drill"
    # F7.4 performance benchmarks
    PERFORMANCE_READ = "performance.read"
    PERFORMANCE_BENCHMARK_RUN = "performance.benchmark.run"
    REPORTS_EXPORT_CSV = "reports.export.csv"
    REPORTS_EXPORT_PDF = "reports.export.pdf"
    REPORTS_EXPORT_EXCEL = "reports.export.excel"
    AUDIT_LOGS_READ = "audit_logs.read"
    OCCUPANCY_READ = "occupancy.read"
    OCCUPANCY_ALERTS_MANAGE = "occupancy.alerts.manage"
    OCCUPANCY_SETTINGS_MANAGE = "occupancy.settings.manage"
    OCCUPANCY_COUNTS_CORRECT = "occupancy.counts.correct"
    FINANCE_RECORDS_READ = "finance.records.read"
    FINANCE_RECORDS_MANAGE = "finance.records.manage"
    FINANCE_BUDGETS_READ = "finance.budgets.read"
    FINANCE_BUDGETS_MANAGE = "finance.budgets.manage"
    FINANCE_REPORTS_VIEW = "finance.reports.view"
    FINANCE_EXPORTS = "finance.exports"
    COUNCIL_PORTAL_MANAGE = "council_portal.manage"

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
    # F5.3 tenant employment preparation (skills, CV, applications, roadmap)
    EMPLOYMENT_PREP_MANAGE_OWN = "employment.prep.manage.own"
    EMPLOYMENT_PREP_READ_ASSIGNED = "employment.prep.read.assigned"
    # F5.5 tenant wellbeing (private check-ins/routines; staff manage resources only)
    WELLBEING_MANAGE_OWN = "wellbeing.manage.own"
    WELLBEING_RESOURCES_MANAGE = "wellbeing.resources.manage"
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

    # F2.12 communication platform
    COMMUNICATION_MESSAGES_SEND = "communication.messages.send"
    COMMUNICATION_MESSAGES_READ = "communication.messages.read"
    COMMUNICATION_DELIVERIES_READ = "communication.deliveries.read"
    COMMUNICATION_CHANNEL_EMAIL_SEND = "communication.channel.email.send"
    COMMUNICATION_CHANNEL_SMS_SEND = "communication.channel.sms.send"
    COMMUNICATION_REMINDERS_MANAGE = "communication.reminders.manage"
    COMMUNICATION_ANNOUNCEMENTS_PUBLISH = "communication.announcements.publish"
    COMMUNICATION_ANNOUNCEMENTS_READ = "communication.announcements.read"
    COMMUNICATION_TEMPLATES_MANAGE = "communication.templates.manage"
    COMMUNICATION_TRANSLATIONS_MANAGE = "communication.translations.manage"

    # F2.13 organisation workflows
    APPROVALS_INBOX_READ = "approvals.inbox.read"
    APPROVALS_DECIDE = "approvals.decide"
    APPROVALS_ASSIGN = "approvals.assign"
    ORGANISATION_FORMS_MANAGE = "organisation.forms.manage"
    ORGANISATION_FORMS_PUBLISH = "organisation.forms.publish"
    ORGANISATION_FORMS_SUBMIT = "organisation.forms.submit"
    ORGANISATION_FORMS_SUBMISSIONS_READ = "organisation.forms.submissions.read"
    ORGANISATION_FORMS_SUBMISSIONS_REVIEW = "organisation.forms.submissions.review"
    SECURE_SHARING_GRANT = "secure_sharing.grant"
    SECURE_SHARING_REVOKE = "secure_sharing.revoke"
    SECURE_SHARING_READ = "secure_sharing.read"

    # F3.3 AI usage caps and cost dashboard
    AI_BUDGET_READ = "ai.budget.read"
    AI_BUDGET_MANAGE = "ai.budget.manage"
    AI_USAGE_READ = "ai.usage.read"
    AI_COST_DASHBOARD_VIEW = "ai.cost.dashboard.view"
    AI_PRICING_MANAGE = "ai.pricing.manage"
    AI_PLATFORM_COST_VIEW = "ai.platform.cost.view"

    # F3.14 AI activity transparency and wrong-answer feedback
    AI_ACTIVITY_READ = "ai.activity.read"
    AI_ACTIVITY_FEEDBACK_SUBMIT = "ai.activity.feedback.submit"
    AI_ACTIVITY_FEEDBACK_REVIEW = "ai.activity.feedback.review"

    # F3.15 organisation AI feature flags (never self-gated)
    AI_FEATURE_FLAGS_READ = "ai.feature_flags.read"
    AI_FEATURE_FLAGS_MANAGE = "ai.feature_flags.manage"

    # F3.4 Notes Analysis Agent
    AI_NOTES_ANALYSIS_RUN = "ai.notes.analysis.run"
    AI_NOTES_ANALYSIS_READ = "ai.notes.analysis.read"
    AI_NOTES_ANALYSIS_REVIEW = "ai.notes.analysis.review"
    AI_NOTES_ANALYSIS_INBOX_READ = "ai.notes.analysis.inbox.read"

    # F3.5 case summaries
    AI_CASE_SUMMARY_RUN = "ai.case_summary.run"
    AI_CASE_SUMMARY_READ = "ai.case_summary.read"
    AI_CASE_SUMMARY_REVIEW = "ai.case_summary.review"

    # F3.6 document checker
    AI_DOCUMENT_CHECK_RUN = "ai.document_check.run"
    AI_DOCUMENT_CHECK_READ = "ai.document_check.read"
    AI_DOCUMENT_CHECK_REVIEW = "ai.document_check.review"

    # F3.7 support planning drafts
    AI_SUPPORT_PLAN_DRAFT_RUN = "ai.support_plan_draft.run"
    AI_SUPPORT_PLAN_DRAFT_READ = "ai.support_plan_draft.read"
    AI_SUPPORT_PLAN_DRAFT_REVIEW = "ai.support_plan_draft.review"

    # F3.8 housing application analysis
    AI_HOUSING_APPLICATION_RUN = "ai.housing_application.run"
    AI_HOUSING_APPLICATION_READ = "ai.housing_application.read"
    AI_HOUSING_APPLICATION_REVIEW = "ai.housing_application.review"

    # F3.9 compliance agent
    AI_COMPLIANCE_RUN = "ai.compliance.run"
    AI_COMPLIANCE_READ = "ai.compliance.read"
    AI_COMPLIANCE_REVIEW = "ai.compliance.review"

    # F3.10 tenant assistant pilot
    AI_TENANT_ASSISTANT_ASK = "ai.tenant_assistant.ask"
    AI_TENANT_ASSISTANT_READ = "ai.tenant_assistant.read"

    # F3.11 duplicate detection (search-based; no AI per record)
    DUPLICATE_DETECTION_RUN = "duplicate_detection.run"
    DUPLICATE_DETECTION_READ = "duplicate_detection.read"
    DUPLICATE_DETECTION_REVIEW = "duplicate_detection.review"

    # F3.12 natural-language operational search
    OPERATIONAL_SEARCH_RUN = "operational_search.run"

    # F3.13 report drafts
    REPORT_DRAFTS_GENERATE = "report_drafts.generate"
    REPORT_DRAFTS_READ = "report_drafts.read"
    REPORT_DRAFTS_REVIEW = "report_drafts.review"


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
    Permission.REPORTS_DASHBOARD_VIEW: PermissionMeta(
        Permission.REPORTS_DASHBOARD_VIEW, "View operational reporting dashboard", True
    ),
    Permission.REPORTS_HOUSING_VIEW: PermissionMeta(
        Permission.REPORTS_HOUSING_VIEW, "View housing application reports", True
    ),
    Permission.REPORTS_COMPLAINTS_VIEW: PermissionMeta(
        Permission.REPORTS_COMPLAINTS_VIEW, "View complaints reports", True
    ),
    Permission.REPORTS_CASELOAD_VIEW: PermissionMeta(
        Permission.REPORTS_CASELOAD_VIEW, "View support worker caseload reports", True
    ),
    Permission.REPORTS_OCCUPANCY_VIEW: PermissionMeta(
        Permission.REPORTS_OCCUPANCY_VIEW, "View occupancy analytics reports", True
    ),
    Permission.REPORTS_PLANS_VIEW: PermissionMeta(
        Permission.REPORTS_PLANS_VIEW, "View support plan completion reports", True
    ),
    Permission.REPORTS_SCHEDULE_MANAGE: PermissionMeta(
        Permission.REPORTS_SCHEDULE_MANAGE, "Manage scheduled report delivery", True
    ),
    Permission.REPORTS_ALERTS_VIEW: PermissionMeta(
        Permission.REPORTS_ALERTS_VIEW, "View early-warning operational alerts", True
    ),
    Permission.AUTOMATION_RULES_READ: PermissionMeta(
        Permission.AUTOMATION_RULES_READ, "View organisation automation rules", True
    ),
    Permission.AUTOMATION_RULES_MANAGE: PermissionMeta(
        Permission.AUTOMATION_RULES_MANAGE, "Create and manage automation rules", True
    ),
    Permission.AUTOMATION_RUNS_READ: PermissionMeta(
        Permission.AUTOMATION_RUNS_READ, "View automation execution history", True
    ),
    Permission.AUTOMATION_ESCALATIONS_MANAGE: PermissionMeta(
        Permission.AUTOMATION_ESCALATIONS_MANAGE, "Acknowledge and resolve automation escalations", True
    ),
    Permission.INTEGRATIONS_READ: PermissionMeta(
        Permission.INTEGRATIONS_READ, "View organisation integration hub configurations", True
    ),
    Permission.INTEGRATIONS_MANAGE: PermissionMeta(
        Permission.INTEGRATIONS_MANAGE, "Manage integration configurations and sync jobs", True
    ),
    Permission.PRIVACY_READ: PermissionMeta(
        Permission.PRIVACY_READ, "View privacy inventory, DPIA register and data subject requests", True
    ),
    Permission.PRIVACY_MANAGE: PermissionMeta(
        Permission.PRIVACY_MANAGE, "Manage privacy registers, retention policies and DSR workflows", True
    ),
    Permission.BACKUP_READ: PermissionMeta(
        Permission.BACKUP_READ, "View backup status, history and monitoring dashboard", True
    ),
    Permission.BACKUP_MANAGE: PermissionMeta(
        Permission.BACKUP_MANAGE, "Run and configure platform backups", True
    ),
    Permission.BACKUP_RESTORE_DRILL: PermissionMeta(
        Permission.BACKUP_RESTORE_DRILL, "Execute isolated restore drills", True
    ),
    Permission.PERFORMANCE_READ: PermissionMeta(
        Permission.PERFORMANCE_READ, "View performance benchmark results", True
    ),
    Permission.PERFORMANCE_BENCHMARK_RUN: PermissionMeta(
        Permission.PERFORMANCE_BENCHMARK_RUN, "Run controlled API journey benchmarks", True
    ),
    Permission.REPORTS_EXPORT_CSV: PermissionMeta(
        Permission.REPORTS_EXPORT_CSV, "Export reports as CSV", True
    ),
    Permission.REPORTS_EXPORT_PDF: PermissionMeta(
        Permission.REPORTS_EXPORT_PDF, "Export reports as PDF", True
    ),
    Permission.REPORTS_EXPORT_EXCEL: PermissionMeta(
        Permission.REPORTS_EXPORT_EXCEL, "Export reports as Excel", True
    ),
    Permission.AUDIT_LOGS_READ: PermissionMeta(
        Permission.AUDIT_LOGS_READ, "Read audit logs", True
    ),
    Permission.OCCUPANCY_READ: PermissionMeta(
        Permission.OCCUPANCY_READ, "View permitted room occupancy counts", True
    ),
    Permission.OCCUPANCY_ALERTS_MANAGE: PermissionMeta(
        Permission.OCCUPANCY_ALERTS_MANAGE, "Manage occupancy alerts", True
    ),
    Permission.OCCUPANCY_SETTINGS_MANAGE: PermissionMeta(
        Permission.OCCUPANCY_SETTINGS_MANAGE,
        "Manage room occupancy privacy gate, devices and thresholds",
        True,
    ),
    Permission.OCCUPANCY_COUNTS_CORRECT: PermissionMeta(
        Permission.OCCUPANCY_COUNTS_CORRECT, "Correct estimated room occupancy counts", True
    ),
    Permission.FINANCE_RECORDS_READ: PermissionMeta(
        Permission.FINANCE_RECORDS_READ, "View organisation finance ledger records", True
    ),
    Permission.FINANCE_RECORDS_MANAGE: PermissionMeta(
        Permission.FINANCE_RECORDS_MANAGE, "Create and update finance ledger records", True
    ),
    Permission.FINANCE_BUDGETS_READ: PermissionMeta(
        Permission.FINANCE_BUDGETS_READ, "View finance budgets and variance", True
    ),
    Permission.FINANCE_BUDGETS_MANAGE: PermissionMeta(
        Permission.FINANCE_BUDGETS_MANAGE, "Manage finance budgets", True
    ),
    Permission.FINANCE_REPORTS_VIEW: PermissionMeta(
        Permission.FINANCE_REPORTS_VIEW, "View finance dashboard summaries", True
    ),
    Permission.FINANCE_EXPORTS: PermissionMeta(
        Permission.FINANCE_EXPORTS, "Export finance records (CSV/PDF/Excel)", True
    ),
    Permission.COUNCIL_PORTAL_MANAGE: PermissionMeta(
        Permission.COUNCIL_PORTAL_MANAGE,
        "Manage Council Portal add-on officers and application shares (not a core role)",
        True,
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
    Permission.EMPLOYMENT_PREP_MANAGE_OWN: PermissionMeta(
        Permission.EMPLOYMENT_PREP_MANAGE_OWN,
        "Manage own skills assessment, CVs and job applications",
    ),
    Permission.EMPLOYMENT_PREP_READ_ASSIGNED: PermissionMeta(
        Permission.EMPLOYMENT_PREP_READ_ASSIGNED,
        "Read employment preparation summaries for assigned tenants",
        True,
    ),
    Permission.WELLBEING_MANAGE_OWN: PermissionMeta(
        Permission.WELLBEING_MANAGE_OWN,
        "Manage own wellbeing check-ins, routines and saved resources",
    ),
    Permission.WELLBEING_RESOURCES_MANAGE: PermissionMeta(
        Permission.WELLBEING_RESOURCES_MANAGE,
        "Manage organisation wellbeing resource and directory listings",
        True,
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
    Permission.COMMUNICATION_MESSAGES_SEND: PermissionMeta(
        Permission.COMMUNICATION_MESSAGES_SEND, "Send in-app messages within permitted recipient scope"
    ),
    Permission.COMMUNICATION_MESSAGES_READ: PermissionMeta(
        Permission.COMMUNICATION_MESSAGES_READ, "Read permitted in-app messages and threads"
    ),
    Permission.COMMUNICATION_DELIVERIES_READ: PermissionMeta(
        Permission.COMMUNICATION_DELIVERIES_READ,
        "View communication delivery status and attempts (operational)",
        True,
    ),
    Permission.COMMUNICATION_CHANNEL_EMAIL_SEND: PermissionMeta(
        Permission.COMMUNICATION_CHANNEL_EMAIL_SEND,
        "Dispatch operational email via the communication service",
        True,
    ),
    Permission.COMMUNICATION_CHANNEL_SMS_SEND: PermissionMeta(
        Permission.COMMUNICATION_CHANNEL_SMS_SEND,
        "Dispatch operational SMS via the communication service",
        True,
    ),
    Permission.COMMUNICATION_REMINDERS_MANAGE: PermissionMeta(
        Permission.COMMUNICATION_REMINDERS_MANAGE,
        "Create or cancel scheduled communication reminders where permitted",
        True,
    ),
    Permission.COMMUNICATION_ANNOUNCEMENTS_PUBLISH: PermissionMeta(
        Permission.COMMUNICATION_ANNOUNCEMENTS_PUBLISH,
        "Publish emergency or org announcements",
        True,
    ),
    Permission.COMMUNICATION_ANNOUNCEMENTS_READ: PermissionMeta(
        Permission.COMMUNICATION_ANNOUNCEMENTS_READ, "Read announcements targeted to the user"
    ),
    Permission.COMMUNICATION_TEMPLATES_MANAGE: PermissionMeta(
        Permission.COMMUNICATION_TEMPLATES_MANAGE,
        "Manage organisation communication templates",
        True,
    ),
    Permission.COMMUNICATION_TRANSLATIONS_MANAGE: PermissionMeta(
        Permission.COMMUNICATION_TRANSLATIONS_MANAGE,
        "Request or review translations of communication content",
        True,
    ),
    Permission.APPROVALS_INBOX_READ: PermissionMeta(
        Permission.APPROVALS_INBOX_READ, "View organisation approvals inbox", True
    ),
    Permission.APPROVALS_DECIDE: PermissionMeta(
        Permission.APPROVALS_DECIDE, "Approve or reject aggregated approval requests", True
    ),
    Permission.APPROVALS_ASSIGN: PermissionMeta(
        Permission.APPROVALS_ASSIGN, "Assign reviewers to approval requests", True
    ),
    Permission.ORGANISATION_FORMS_MANAGE: PermissionMeta(
        Permission.ORGANISATION_FORMS_MANAGE, "Create and edit organisation custom forms", True
    ),
    Permission.ORGANISATION_FORMS_PUBLISH: PermissionMeta(
        Permission.ORGANISATION_FORMS_PUBLISH, "Publish organisation custom forms", True
    ),
    Permission.ORGANISATION_FORMS_SUBMIT: PermissionMeta(
        Permission.ORGANISATION_FORMS_SUBMIT, "Complete and submit published custom forms"
    ),
    Permission.ORGANISATION_FORMS_SUBMISSIONS_READ: PermissionMeta(
        Permission.ORGANISATION_FORMS_SUBMISSIONS_READ, "Read permitted custom form submissions"
    ),
    Permission.ORGANISATION_FORMS_SUBMISSIONS_REVIEW: PermissionMeta(
        Permission.ORGANISATION_FORMS_SUBMISSIONS_REVIEW,
        "Review and decide on custom form submissions",
        True,
    ),
    Permission.SECURE_SHARING_GRANT: PermissionMeta(
        Permission.SECURE_SHARING_GRANT, "Create secure sharing grants", True
    ),
    Permission.SECURE_SHARING_REVOKE: PermissionMeta(
        Permission.SECURE_SHARING_REVOKE, "Revoke secure sharing grants", True
    ),
    Permission.SECURE_SHARING_READ: PermissionMeta(
        Permission.SECURE_SHARING_READ, "View and access secure sharing grants", True
    ),
    Permission.AI_BUDGET_READ: PermissionMeta(
        Permission.AI_BUDGET_READ, "View organisation AI budget configuration", True
    ),
    Permission.AI_BUDGET_MANAGE: PermissionMeta(
        Permission.AI_BUDGET_MANAGE, "Create or update organisation AI budgets", True
    ),
    Permission.AI_USAGE_READ: PermissionMeta(
        Permission.AI_USAGE_READ, "View organisation AI usage and cost records", True
    ),
    Permission.AI_COST_DASHBOARD_VIEW: PermissionMeta(
        Permission.AI_COST_DASHBOARD_VIEW, "View organisation AI cost dashboard", True
    ),
    Permission.AI_PRICING_MANAGE: PermissionMeta(
        Permission.AI_PRICING_MANAGE, "Manage verified AI provider/model pricing", True
    ),
    Permission.AI_PLATFORM_COST_VIEW: PermissionMeta(
        Permission.AI_PLATFORM_COST_VIEW, "View platform-wide AI cost dashboard", True
    ),
    Permission.AI_NOTES_ANALYSIS_RUN: PermissionMeta(
        Permission.AI_NOTES_ANALYSIS_RUN, "Run AI notes analysis on authorised daily notes", True
    ),
    Permission.AI_NOTES_ANALYSIS_READ: PermissionMeta(
        Permission.AI_NOTES_ANALYSIS_READ, "View AI notes analysis results", True
    ),
    Permission.AI_NOTES_ANALYSIS_REVIEW: PermissionMeta(
        Permission.AI_NOTES_ANALYSIS_REVIEW, "Approve or reject AI notes analysis suggestions", True
    ),
    Permission.AI_NOTES_ANALYSIS_INBOX_READ: PermissionMeta(
        Permission.AI_NOTES_ANALYSIS_INBOX_READ, "View notes analysis human approval inbox", True
    ),
    Permission.AI_CASE_SUMMARY_RUN: PermissionMeta(
        Permission.AI_CASE_SUMMARY_RUN, "Generate a case summary from authorised records", True
    ),
    Permission.AI_CASE_SUMMARY_READ: PermissionMeta(
        Permission.AI_CASE_SUMMARY_READ, "View case summaries for authorised cases", True
    ),
    Permission.AI_CASE_SUMMARY_REVIEW: PermissionMeta(
        Permission.AI_CASE_SUMMARY_REVIEW, "Approve or reject a case summary", True
    ),
    Permission.AI_DOCUMENT_CHECK_RUN: PermissionMeta(
        Permission.AI_DOCUMENT_CHECK_RUN, "Run a document check on an authorised file", True
    ),
    Permission.AI_DOCUMENT_CHECK_READ: PermissionMeta(
        Permission.AI_DOCUMENT_CHECK_READ, "View document check results", True
    ),
    Permission.AI_DOCUMENT_CHECK_REVIEW: PermissionMeta(
        Permission.AI_DOCUMENT_CHECK_REVIEW, "Confirm or dismiss document check findings", True
    ),
    Permission.AI_SUPPORT_PLAN_DRAFT_RUN: PermissionMeta(
        Permission.AI_SUPPORT_PLAN_DRAFT_RUN, "Generate a support-plan draft from authorised case records", True
    ),
    Permission.AI_SUPPORT_PLAN_DRAFT_READ: PermissionMeta(
        Permission.AI_SUPPORT_PLAN_DRAFT_READ, "View support-plan drafts and their sources", True
    ),
    Permission.AI_SUPPORT_PLAN_DRAFT_REVIEW: PermissionMeta(
        Permission.AI_SUPPORT_PLAN_DRAFT_REVIEW, "Approve or reject a support-plan draft", True
    ),
    Permission.AI_HOUSING_APPLICATION_RUN: PermissionMeta(
        Permission.AI_HOUSING_APPLICATION_RUN,
        "Analyse a housing application checklist and gaps",
        True,
    ),
    Permission.AI_HOUSING_APPLICATION_READ: PermissionMeta(
        Permission.AI_HOUSING_APPLICATION_READ, "View housing application analysis results", True
    ),
    Permission.AI_HOUSING_APPLICATION_REVIEW: PermissionMeta(
        Permission.AI_HOUSING_APPLICATION_REVIEW,
        "Confirm or dismiss housing application analysis findings",
        True,
    ),
    Permission.AI_COMPLIANCE_RUN: PermissionMeta(
        Permission.AI_COMPLIANCE_RUN,
        "Run a rules-based compliance sweep",
        True,
    ),
    Permission.AI_COMPLIANCE_READ: PermissionMeta(
        Permission.AI_COMPLIANCE_READ, "View compliance sweeps, rules, and findings", True
    ),
    Permission.AI_COMPLIANCE_REVIEW: PermissionMeta(
        Permission.AI_COMPLIANCE_REVIEW,
        "Review, dismiss, or resolve compliance findings",
        True,
    ),
    Permission.AI_TENANT_ASSISTANT_ASK: PermissionMeta(
        Permission.AI_TENANT_ASSISTANT_ASK,
        "Ask the Tenant Assistant using approved organisation content",
        True,
    ),
    Permission.AI_TENANT_ASSISTANT_READ: PermissionMeta(
        Permission.AI_TENANT_ASSISTANT_READ,
        "Read own Tenant Assistant conversation history",
        True,
    ),
    Permission.DUPLICATE_DETECTION_RUN: PermissionMeta(
        Permission.DUPLICATE_DETECTION_RUN,
        "Run search-based duplicate detection",
        True,
    ),
    Permission.DUPLICATE_DETECTION_READ: PermissionMeta(
        Permission.DUPLICATE_DETECTION_READ,
        "View duplicate detection runs and findings",
        True,
    ),
    Permission.DUPLICATE_DETECTION_REVIEW: PermissionMeta(
        Permission.DUPLICATE_DETECTION_REVIEW,
        "Confirm, dismiss, or defer potential duplicate findings",
        True,
    ),
    Permission.OPERATIONAL_SEARCH_RUN: PermissionMeta(
        Permission.OPERATIONAL_SEARCH_RUN,
        "Run natural-language search over authorised operational records",
        True,
    ),
    Permission.REPORT_DRAFTS_GENERATE: PermissionMeta(
        Permission.REPORT_DRAFTS_GENERATE,
        "Generate weekly or monthly operational report drafts",
        True,
    ),
    Permission.REPORT_DRAFTS_READ: PermissionMeta(
        Permission.REPORT_DRAFTS_READ,
        "View operational report drafts and metrics snapshots",
        True,
    ),
    Permission.REPORT_DRAFTS_REVIEW: PermissionMeta(
        Permission.REPORT_DRAFTS_REVIEW,
        "Edit, approve, or reject operational report drafts",
        True,
    ),
    Permission.AI_ACTIVITY_READ: PermissionMeta(
        Permission.AI_ACTIVITY_READ,
        "View authorised AI activity logs, confidence, and source references",
        True,
    ),
    Permission.AI_ACTIVITY_FEEDBACK_SUBMIT: PermissionMeta(
        Permission.AI_ACTIVITY_FEEDBACK_SUBMIT,
        "Report incorrect or unsupported AI responses",
        True,
    ),
    Permission.AI_ACTIVITY_FEEDBACK_REVIEW: PermissionMeta(
        Permission.AI_ACTIVITY_FEEDBACK_REVIEW,
        "Review and resolve wrong-answer feedback",
        True,
    ),
    Permission.AI_FEATURE_FLAGS_READ: PermissionMeta(
        Permission.AI_FEATURE_FLAGS_READ,
        "View organisation AI feature flag configuration and history",
        True,
    ),
    Permission.AI_FEATURE_FLAGS_MANAGE: PermissionMeta(
        Permission.AI_FEATURE_FLAGS_MANAGE,
        "Enable or disable organisation AI features and pilots",
        True,
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
