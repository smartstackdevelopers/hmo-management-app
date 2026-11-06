/**
 * Role dashboard home routing. Roles come from the API authorization snapshot only.
 */

import type { ApprovedRole } from "@/lib/rbac";

export const ROLE_DASHBOARD_HOMES: Record<
  "super_admin" | "organisation_admin" | "landlord" | "support_worker",
  string
> = {
  super_admin: "/dashboard/super-admin",
  organisation_admin: "/dashboard/organisation-admin",
  landlord: "/dashboard/landlord",
  support_worker: "/dashboard/support-worker",
};

/** F1.9 role homes plus F2.1 Support Worker caseload home. */
export const F19_DASHBOARD_ROLES = [
  "super_admin",
  "organisation_admin",
  "landlord",
  "support_worker",
] as const;

export type F19DashboardRole = (typeof F19_DASHBOARD_ROLES)[number];

export function isF19DashboardRole(role: string | null | undefined): role is F19DashboardRole {
  return Boolean(role && (F19_DASHBOARD_ROLES as readonly string[]).includes(role));
}

export function homePathForRole(role: string | null | undefined): string {
  if (role && role in ROLE_DASHBOARD_HOMES) {
    return ROLE_DASHBOARD_HOMES[role as keyof typeof ROLE_DASHBOARD_HOMES];
  }
  return "/account";
}

export function canAccessRoleHome(
  activeRole: string | null | undefined,
  required: F19DashboardRole,
): boolean {
  return activeRole === required;
}

/** Map a path segment to the required role for that home. */
export function requiredRoleForHomePath(segment: string): F19DashboardRole | null {
  if (segment === "super-admin") {
    return "super_admin";
  }
  if (segment === "organisation-admin") {
    return "organisation_admin";
  }
  if (segment === "landlord") {
    return "landlord";
  }
  if (segment === "support-worker") {
    return "support_worker";
  }
  return null;
}

export function roleDisplayName(role: string | null | undefined): string {
  switch (role) {
    case "super_admin":
      return "Super Admin";
    case "organisation_admin":
      return "Organisation Admin";
    case "landlord":
      return "Landlord";
    case "tenant":
      return "Tenant";
    case "support_worker":
      return "Support Worker";
    case "maintenance_contractor":
      return "Maintenance & Contractors";
    default:
      return role ?? "Unknown role";
  }
}

export function isApprovedRoleValue(role: string): role is ApprovedRole {
  return (
    role === "super_admin" ||
    role === "organisation_admin" ||
    role === "landlord" ||
    role === "tenant" ||
    role === "support_worker" ||
    role === "maintenance_contractor"
  );
}
