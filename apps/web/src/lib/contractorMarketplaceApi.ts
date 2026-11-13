import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function cmFetch<T>(path: string, accessToken: string, organisationId: string, init?: RequestInit): Promise<T> {
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

export function getContractorMarketplaceReports(accessToken: string, organisationId: string) {
  return cmFetch<Record<string, unknown>>(
    "/api/v1/contractor-marketplace/reports/dashboard",
    accessToken,
    organisationId,
  );
}

export function searchContractorMarketplace(accessToken: string, organisationId: string) {
  return cmFetch<Record<string, unknown>[]>(
    "/api/v1/contractor-marketplace/marketplace",
    accessToken,
    organisationId,
  );
}

export function listContractorWorkspaceJobs(accessToken: string, organisationId: string) {
  return cmFetch<Record<string, unknown>[]>(
    "/api/v1/contractor-marketplace/workspace/jobs",
    accessToken,
    organisationId,
  );
}
