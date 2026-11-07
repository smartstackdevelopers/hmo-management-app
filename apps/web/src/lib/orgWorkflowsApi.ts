/**
 * F2.13 organisation workflows API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function wfFetch<T>(
  path: string,
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    method?: string;
    body?: unknown;
  },
): Promise<T> {
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
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function fetchOrgWorkflowsDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  return wfFetch<Record<string, unknown>>("/api/v1/org-workflows/dashboard", options);
}

export function listApprovalsInbox(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
  } & { page?: number; q?: string; source_type?: string },
) {
  const params = new URLSearchParams();
  params.set("page", String(options.page ?? 1));
  if (options.q) params.set("q", options.q);
  if (options.source_type) params.set("source_type", options.source_type);
  return wfFetch<{ items: Array<Record<string, unknown>>; total: number }>(
    `/api/v1/org-workflows/approvals/inbox?${params}`,
    options,
  );
}

export function listWorkflows(options: { accessToken: string; organisationId: string; role?: string | null }) {
  return wfFetch<{ items: Array<Record<string, unknown>> }>("/api/v1/org-workflows/workflows", options);
}

export function listCustomForms(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  publishedOnly?: boolean;
}) {
  const q = options.publishedOnly ? "?published_only=true" : "";
  return wfFetch<{ items: Array<Record<string, unknown>> }>(`/api/v1/org-workflows/forms${q}`, options);
}

export function listSharingGrants(options: { accessToken: string; organisationId: string; role?: string | null }) {
  return wfFetch<{ items: Array<Record<string, unknown>> }>("/api/v1/org-workflows/sharing", options);
}

export function listAuditEvents(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
  } & { page?: number; action?: string; resource_type?: string },
) {
  const params = new URLSearchParams({ page: String(options.page ?? 1), page_size: "20" });
  if (options.action) params.set("action", options.action);
  if (options.resource_type) params.set("resource_type", options.resource_type);
  return wfFetch<{ items: Array<Record<string, unknown>>; total: number }>(
    `/api/v1/audit-events?${params}`,
    options,
  );
}
