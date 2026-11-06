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
