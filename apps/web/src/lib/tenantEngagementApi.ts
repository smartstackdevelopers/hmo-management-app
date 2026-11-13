import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function teFetch<T>(path: string, accessToken: string, organisationId: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({ organisationId }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function getTenantEngagementDashboard(accessToken: string, organisationId: string) {
  return teFetch<Record<string, unknown>>("/api/v1/tenant-engagement/tenant/dashboard", accessToken, organisationId);
}

export function getEngagementReports(accessToken: string, organisationId: string) {
  return teFetch<Record<string, unknown>>("/api/v1/tenant-engagement/reports/dashboard", accessToken, organisationId);
}
