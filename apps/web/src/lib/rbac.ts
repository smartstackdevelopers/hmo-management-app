/**
 * Frontend RBAC helpers (F1.4).
 * UI checks are convenience only — the API enforces authorization.
 */

export const APPROVED_ROLES = [
  "super_admin",
  "organisation_admin",
  "landlord",
  "tenant",
  "support_worker",
  "maintenance_contractor",
] as const;

export type ApprovedRole = (typeof APPROVED_ROLES)[number];

export type PermissionId = string;

export type AuthorizationSnapshot = {
  user_id: string;
  authorization_version: number;
  active_role: ApprovedRole | string | null;
  active_organisation_id: string | null;
  permissions: PermissionId[];
  memberships: Array<{
    id: string;
    role: string;
    organisation_id: string | null;
    status: string;
  }>;
};

export function isApprovedRole(value: string): value is ApprovedRole {
  return (APPROVED_ROLES as readonly string[]).includes(value);
}

export function can(permissions: PermissionId[] | undefined, permission: PermissionId): boolean {
  if (!permissions || permissions.length === 0) {
    return false;
  }
  return permissions.includes(permission);
}

export function canAny(
  permissions: PermissionId[] | undefined,
  required: PermissionId[],
): boolean {
  return required.some((permission) => can(permissions, permission));
}

export function canAll(
  permissions: PermissionId[] | undefined,
  required: PermissionId[],
): boolean {
  return required.every((permission) => can(permissions, permission));
}

export type ApiAuthErrorKind = "unauthenticated" | "forbidden" | "other";

export function classifyApiStatus(status: number): ApiAuthErrorKind {
  if (status === 401) {
    return "unauthenticated";
  }
  if (status === 403) {
    return "forbidden";
  }
  return "other";
}

/** Headers that select among server-side memberships only (never invent roles). */
export function authzContextHeaders(options: {
  organisationId?: string | null;
  role?: string | null;
}): Record<string, string> {
  const headers: Record<string, string> = {};
  if (options.organisationId) {
    headers["X-Organisation-Id"] = options.organisationId;
  }
  if (options.role && isApprovedRole(options.role)) {
    headers["X-HMore-Role"] = options.role;
  }
  return headers;
}

export const UNAUTHORIZED_PATH = "/unauthorized";
export const LOGIN_PATH = "/auth/login";
