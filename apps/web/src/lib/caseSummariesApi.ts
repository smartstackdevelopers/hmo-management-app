import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Opts = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function csFetch<T>(path: string, options: Opts & { method?: string; body?: unknown }): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function generateCaseSummary(tenantId: string, options: Opts & { force?: boolean }) {
  return csFetch<Record<string, unknown>>("/api/v1/case-summaries", {
    ...options,
    method: "POST",
    body: { tenant_id: tenantId, force: options.force ?? false },
  });
}

export function fetchCaseSummary(summaryId: string, options: Opts) {
  return csFetch<Record<string, unknown>>(`/api/v1/case-summaries/${summaryId}`, options);
}

export function fetchCaseSummaryVersions(tenantId: string, options: Opts) {
  return csFetch<{ items: Array<Record<string, unknown>> }>(
    `/api/v1/case-summaries/tenants/${tenantId}/versions`,
    options,
  );
}

export function fetchCaseSummarySources(summaryId: string, options: Opts) {
  return csFetch<Record<string, unknown>>(`/api/v1/case-summaries/${summaryId}/sources`, options);
}

export function reviewCaseSummary(
  summaryId: string,
  decision: "approve" | "reject",
  options: Opts & { reviewComment?: string },
) {
  return csFetch<Record<string, unknown>>(`/api/v1/case-summaries/${summaryId}/review`, {
    ...options,
    method: "POST",
    body: { decision, review_comment: options.reviewComment },
  });
}

export function regenerateCaseSummary(summaryId: string, options: Opts) {
  return csFetch<Record<string, unknown>>(`/api/v1/case-summaries/${summaryId}/regenerate`, {
    ...options,
    method: "POST",
  });
}
