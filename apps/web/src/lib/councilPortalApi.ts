import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CouncilAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function cpFetch<T>(path: string, options: CouncilAuth, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function fetchCouncilAdminDashboard(options: CouncilAuth) {
  return cpFetch<Record<string, unknown>>("/api/v1/council-portal/admin/dashboard", options);
}

export function inviteCouncilOfficer(options: CouncilAuth, body: Record<string, unknown>) {
  return cpFetch<Record<string, unknown>>("/api/v1/council-portal/admin/officers", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function createCouncilShare(options: CouncilAuth, body: Record<string, unknown>) {
  return cpFetch<Record<string, unknown>>("/api/v1/council-portal/admin/shares", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function revokeCouncilShare(options: CouncilAuth, shareId: string) {
  return cpFetch<Record<string, unknown>>(
    `/api/v1/council-portal/admin/shares/${shareId}/revoke`,
    options,
    { method: "POST" },
  );
}

export function fetchCouncilOfficerInbox(options: CouncilAuth) {
  return cpFetch<{ items: Record<string, unknown>[]; disclaimer?: string }>(
    "/api/v1/council-portal/officer/inbox",
    options,
  );
}
