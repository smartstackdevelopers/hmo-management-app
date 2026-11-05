/**
 * Organisation context helpers (F1.5).
 * Frontend context is advisory — the API validates membership server-side.
 */

import {
  authzContextHeaders,
  classifyApiStatus,
  type ApprovedRole,
  UNAUTHORIZED_PATH,
  LOGIN_PATH,
} from "@/lib/rbac";

export type OrganisationMembership = {
  id: string;
  role: string;
  organisation_id: string | null;
  status: string;
};

export function activeMemberships(
  memberships: OrganisationMembership[] | undefined,
): OrganisationMembership[] {
  if (!memberships) {
    return [];
  }
  return memberships.filter((membership) => membership.status === "active");
}

export function canSelectOrganisation(
  memberships: OrganisationMembership[] | undefined,
  organisationId: string,
): boolean {
  return activeMemberships(memberships).some(
    (membership) => membership.organisation_id === organisationId,
  );
}

export function organisationRequestHeaders(options: {
  organisationId: string;
  role?: ApprovedRole | string | null;
}): Record<string, string> {
  return authzContextHeaders({
    organisationId: options.organisationId,
    role: options.role,
  });
}

export function handleOrganisationApiError(status: number): string {
  const kind = classifyApiStatus(status);
  if (kind === "unauthenticated") {
    return LOGIN_PATH;
  }
  if (kind === "forbidden") {
    return UNAUTHORIZED_PATH;
  }
  return UNAUTHORIZED_PATH;
}
