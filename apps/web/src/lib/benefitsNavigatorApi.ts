import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function bnFetch<T>(path: string, accessToken: string, organisationId: string, init?: RequestInit): Promise<T> {
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

export function getBenefitsNavigatorReports(accessToken: string, organisationId: string) {
  return bnFetch<Record<string, unknown>>("/api/v1/benefits-navigator/reports/dashboard", accessToken, organisationId);
}

export function getTenantBenefitsDashboard(accessToken: string, organisationId: string) {
  return bnFetch<Record<string, unknown>>("/api/v1/benefits-navigator/tenant/dashboard", accessToken, organisationId);
}

export function searchBenefits(accessToken: string, organisationId: string) {
  return bnFetch<Record<string, unknown>[]>("/api/v1/benefits-navigator/search", accessToken, organisationId);
}
