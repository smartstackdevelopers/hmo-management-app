/**
 * F5.2 Help Near Me admin / geocode API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type OutdatedReport = {
  id: string;
  service_id: string;
  reason: string;
  details: string | null;
  status: string;
  resolution_notes: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  reporter_user_id: string | null;
  service_name: string | null;
  service_category: string | null;
};

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function helpFetch<T>(
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
    throw new Error((await response.text()) || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function listAdminReports(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  status?: string;
  category?: string;
  q?: string;
  page?: number;
}) {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  if (options.category) params.set("category", options.category);
  if (options.q) params.set("q", options.q);
  if (options.page) params.set("page", String(options.page));
  const query = params.toString();
  return helpFetch<Page<OutdatedReport>>(
    `/api/v1/help-near-me/reports/admin${query ? `?${query}` : ""}`,
    options,
  );
}

export function getAdminReport(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  reportId: string;
}) {
  return helpFetch<OutdatedReport>(`/api/v1/help-near-me/reports/admin/${options.reportId}`, options);
}

export function updateAdminReport(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  reportId: string;
  status: string;
  resolution_notes?: string | null;
}) {
  return helpFetch<OutdatedReport>(`/api/v1/help-near-me/reports/admin/${options.reportId}`, {
    ...options,
    method: "PATCH",
    body: {
      status: options.status,
      resolution_notes: options.resolution_notes ?? null,
    },
  });
}

export function geocodeCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
}) {
  return helpFetch<{
    id: string;
    latitude: number | null;
    longitude: number | null;
    geocode_status: string;
    geocode_provider: string | null;
    geocoded_at: string | null;
  }>(`/api/v1/help-near-me/services/${options.serviceId}/geocode`, {
    ...options,
    method: "POST",
  });
}
