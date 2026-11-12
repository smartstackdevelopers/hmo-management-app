/**
 * Central navigation config for the F1.9 dashboard shell.
 * Visibility is filtered by API permissions — never treat UI hiding as authorization.
 */

import { canAny, type ApprovedRole, type PermissionId } from "@/lib/rbac";

export type NavItem = {
  id: string;
  label: string;
  href: string;
  /** Any of these permissions grants visibility. Empty = visible when authenticated. */
  anyOf?: PermissionId[];
  /** Limit to these roles even if a permission matches (optional). */
  roles?: ApprovedRole[];
  section?: "primary" | "records" | "platform" | "account";
};

export const DASHBOARD_NAV: NavItem[] = [
  {
    id: "home",
    label: "Dashboard home",
    href: "/dashboard",
    section: "primary",
  },
  {
    id: "tenants",
    label: "Tenants",
    href: "/tenants",
    anyOf: ["tenants.read", "tenants.manage"],
    section: "records",
  },
  {
    id: "properties",
    label: "Properties",
    href: "/properties",
    anyOf: ["properties.read", "properties.manage"],
    section: "records",
  },
  {
    id: "landlord-enterprise",
    label: "Landlord enterprise",
    href: "/dashboard/landlord",
    anyOf: [
      "properties.manage",
      "rent_records.manage",
      "inspections.manage",
      "repairs.status.read",
      "maintenance.read.property",
    ],
    roles: ["landlord", "organisation_admin", "super_admin"],
    section: "records",
  },
  {
    id: "rooms",
    label: "Rooms",
    href: "/rooms",
    anyOf: ["rooms.read", "rooms.manage"],
    section: "records",
  },
  {
    id: "files",
    label: "Private files",
    href: "/dashboard/files",
    anyOf: ["files.read", "files.manage"],
    section: "records",
  },
  {
    id: "documents",
    label: "Documents",
    href: "/dashboard/documents",
    anyOf: ["documents.read.meta"],
    section: "records",
  },
  {
    id: "communications",
    label: "Communications",
    href: "/dashboard/communications",
    anyOf: [
      "communication.messages.read",
      "communication.deliveries.read",
      "communication.reminders.manage",
      "communication.announcements.read",
    ],
    section: "records",
  },
  {
    id: "community-directory",
    label: "Community directory",
    href: "/dashboard/community-directory",
    anyOf: ["organisations.manage", "organisation.settings.manage"],
    roles: ["organisation_admin", "super_admin"],
    section: "records",
  },
  {
    id: "help-near-me",
    label: "Help Near Me reports",
    href: "/dashboard/help-near-me",
    anyOf: ["organisations.manage", "organisation.settings.manage"],
    roles: ["organisation_admin", "super_admin"],
    section: "records",
  },
  {
    id: "employment-support",
    label: "Employment support",
    href: "/dashboard/employment-support",
    anyOf: [
      "employment.prep.read.assigned",
      "employment_support.manage.assigned",
      "tenants.manage",
    ],
    roles: ["support_worker", "organisation_admin", "super_admin"],
    section: "records",
  },
  {
    id: "wellbeing-resources",
    label: "Wellbeing resources",
    href: "/dashboard/wellbeing-resources",
    anyOf: ["wellbeing.resources.manage", "tenants.manage"],
    roles: ["organisation_admin", "super_admin"],
    section: "records",
  },
  {
    id: "ali-journey",
    label: "Ali journey (F2.15)",
    href: "/dashboard/journeys/ali",
    section: "platform",
  },
  {
    id: "reports",
    label: "Reports",
    href: "/dashboard/reports",
    anyOf: [
      "reports.dashboard.view",
      "reports.housing.view",
      "reports.complaints.view",
      "reports.caseload.view",
      "reports.read",
    ],
    section: "records",
  },
  {
    id: "automation",
    label: "Automation",
    href: "/dashboard/automation",
    anyOf: ["automation.rules.read", "automation.rules.manage", "automation.runs.read"],
    section: "records",
  },
  {
    id: "ai-costs",
    label: "AI costs",
    href: "/dashboard/ai-costs",
    anyOf: ["ai.cost.dashboard.view", "ai.platform.cost.view", "ai.usage.read"],
    section: "platform",
  },
  {
    id: "case-summaries",
    label: "Case summaries",
    href: "/dashboard/case-summaries",
    anyOf: ["ai.case_summary.run", "ai.case_summary.read", "ai.case_summary.review"],
    section: "records",
  },
  {
    id: "notes-analysis",
    label: "Notes analysis",
    href: "/dashboard/notes-analysis",
    anyOf: [
      "ai.notes.analysis.inbox.read",
      "ai.notes.analysis.read",
      "ai.notes.analysis.review",
      "ai.notes.analysis.run",
    ],
    section: "records",
  },
  {
    id: "org-workflows",
    label: "Approvals & workflows",
    href: "/dashboard/org-workflows",
    anyOf: [
      "approvals.inbox.read",
      "organisation.workflows.manage",
      "organisation.forms.manage",
      "organisation.forms.submit",
      "secure_sharing.read",
    ],
    section: "records",
  },
  {
    id: "organisations",
    label: "Organisations",
    href: "/dashboard/super-admin/organisations",
    anyOf: ["organisations.create", "organisations.manage", "organisations.read"],
    roles: ["super_admin"],
    section: "platform",
  },
  {
    id: "caseload",
    label: "Caseload",
    href: "/dashboard/support-worker",
    anyOf: ["support_notes.read.assigned"],
    roles: ["support_worker"],
    section: "records",
  },
  {
    id: "tenant-timeline",
    label: "Tenant timeline",
    href: "/dashboard/support-worker",
    anyOf: ["timeline.read"],
    roles: ["support_worker", "organisation_admin"],
    section: "records",
  },
  {
    id: "support-plans-dashboard",
    label: "Support plans",
    href: "/dashboard/support-plans",
    anyOf: ["support_plans.read", "support_plans.manage"],
    roles: ["support_worker", "organisation_admin", "super_admin"],
    section: "records",
  },
  {
    id: "case-assignments",
    label: "Case assignments",
    href: "/dashboard/case-assignments",
    anyOf: ["tenants.manage"],
    roles: ["organisation_admin"],
    section: "records",
  },
  {
    id: "handovers",
    label: "Handovers",
    href: "/dashboard/handovers",
    anyOf: ["support_notes.read.assigned", "tenants.manage"],
    section: "records",
  },
  {
    id: "rota",
    label: "Rota",
    href: "/dashboard/rota",
    anyOf: ["organisation.users.manage", "organisation.users.read", "visits.manage.assigned"],
    section: "records",
  },
  {
    id: "visits",
    label: "Visits",
    href: "/dashboard/visits",
    anyOf: ["visits.manage.assigned", "tenants.manage"],
    section: "records",
  },
  {
    id: "tasks",
    label: "Tasks",
    href: "/dashboard/tasks",
    anyOf: ["tasks.manage.assigned", "tenants.manage"],
    section: "records",
  },
  {
    id: "training",
    label: "Training",
    href: "/dashboard/training",
    anyOf: ["training.records.manage", "training.records.read.own"],
    section: "records",
  },
  {
    id: "safeguarding",
    label: "Safeguarding",
    href: "/dashboard/safeguarding",
    anyOf: ["safeguarding.reminders.manage", "safeguarding.reminders.manage.assigned"],
    section: "records",
  },
  {
    id: "compliance-agent",
    label: "Compliance agent",
    href: "/dashboard/compliance-agent",
    anyOf: ["ai.compliance.run", "ai.compliance.read", "compliance.check"],
    section: "records",
  },
  {
    id: "operational-search",
    label: "Operational search",
    href: "/dashboard/operational-search",
    anyOf: ["operational_search.run"],
    section: "records",
  },
  {
    id: "report-drafts",
    label: "Report drafts",
    href: "/dashboard/report-drafts",
    anyOf: ["report_drafts.generate", "report_drafts.read", "report_drafts.review"],
    section: "records",
  },
  {
    id: "ai-activity",
    label: "AI activity",
    href: "/dashboard/ai-activity",
    anyOf: [
      "ai.activity.read",
      "ai.activity.feedback.submit",
      "ai.activity.feedback.review",
    ],
    section: "records",
  },
  {
    id: "ai-feature-flags",
    label: "AI feature flags",
    href: "/dashboard/ai-feature-flags",
    anyOf: ["ai.feature_flags.read", "ai.feature_flags.manage"],
    section: "records",
  },



  {
    id: "duplicate-detection",
    label: "Duplicate detection",
    href: "/dashboard/duplicate-detection",
    anyOf: [
      "duplicate_detection.run",
      "duplicate_detection.read",
      "duplicate_detection.review",
    ],
    section: "records",
  },
  {
    id: "tenant-assistant",
    label: "Tenant assistant",
    href: "/dashboard/tenant-assistant",
    anyOf: ["ai.tenant_assistant.ask"],
    section: "records",
  },
  {
    id: "incidents",
    label: "Incidents",
    href: "/dashboard/incidents",
    anyOf: ["incidents.manage", "incidents.read.assigned", "incidents.create.assigned"],
    section: "records",
  },
  {
    id: "workload",
    label: "Workload",
    href: "/dashboard/workload",
    anyOf: ["workload.read", "workload.read.own"],
    section: "records",
  },
  {
    id: "housing-applications",
    label: "Housing applications",
    href: "/dashboard/housing-applications",
    anyOf: [
      "applications.manage",
      "applications.review",
      "applications.read.own",
      "applications.read.assigned",
      "applications.create.own",
      "applications.create.assigned",
    ],
    section: "records",
  },
  {
    id: "complaints",
    label: "Complaints",
    href: "/dashboard/complaints",
    anyOf: [
      "complaints.manage",
      "complaints.read.own",
      "complaints.read.assigned",
      "complaints.create.own",
      "complaints.create.assigned",
      "complaints.read.property",
    ],
    section: "records",
  },
  {
    id: "maintenance",
    label: "Maintenance",
    href: "/dashboard/maintenance",
    anyOf: [
      "maintenance.manage",
      "maintenance.read.own",
      "maintenance.read.assigned",
      "maintenance.create.own",
      "maintenance.create.assigned",
      "maintenance.read.property",
    ],
    section: "records",
  },
  {
    id: "waiting-list",
    label: "Waiting list",
    href: "/dashboard/waiting-list",
    anyOf: ["waiting_list.manage", "waiting_list.read"],
    section: "records",
  },
  {
    id: "occupancy-survey",
    label: "Occupancy survey",
    href: "/dashboard/occupancy-survey",
    anyOf: ["occupancy.read", "occupancy.alerts.manage", "inspections.manage"],
    section: "records",
  },
  {
    id: "audit",
    label: "Audit logs",
    href: "/dashboard/audit",
    anyOf: ["audit_logs.read"],
    section: "platform",
  },
  {
    id: "account",
    label: "Account",
    href: "/account",
    section: "account",
  },
  {
    id: "health",
    label: "Service status",
    href: "/health",
    section: "account",
  },
];

export function filterNavItems(
  items: NavItem[],
  options: {
    permissions?: PermissionId[];
    role?: string | null;
    authenticated: boolean;
  },
): NavItem[] {
  if (!options.authenticated) {
    return [];
  }
  return items.filter((item) => {
    if (item.roles && item.roles.length > 0) {
      if (!options.role || !item.roles.includes(options.role as ApprovedRole)) {
        return false;
      }
    }
    if (!item.anyOf || item.anyOf.length === 0) {
      return true;
    }
    return canAny(options.permissions, item.anyOf);
  });
}

export function groupNavItems(items: NavItem[]): Record<string, NavItem[]> {
  const groups: Record<string, NavItem[]> = {
    primary: [],
    records: [],
    platform: [],
    account: [],
  };
  for (const item of items) {
    const key = item.section ?? "primary";
    groups[key] = groups[key] ?? [];
    groups[key].push(item);
  }
  return groups;
}
