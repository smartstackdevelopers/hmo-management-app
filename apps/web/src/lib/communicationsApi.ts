/**
 * F2.12 communication API client (organisation-scoped).
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function commFetch<T>(
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

export async function fetchCommunicationsDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<Record<string, unknown>> {
  return commFetch("/api/v1/communications/dashboard", options);
}

export async function listInbox(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  page?: number;
}) {
  const page = options.page ?? 1;
  return commFetch<{
    items: Array<Record<string, unknown>>;
    total: number;
  }>(`/api/v1/communications/messages/inbox?page=${page}&page_size=20`, options);
}

export async function listSent(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  page?: number;
}) {
  const page = options.page ?? 1;
  return commFetch<{
    items: Array<Record<string, unknown>>;
    total: number;
  }>(`/api/v1/communications/messages/sent?page=${page}&page_size=20`, options);
}

export async function listDeliveries(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  return commFetch<{
    items: Array<Record<string, unknown>>;
    total: number;
  }>("/api/v1/communications/deliveries?page=1&page_size=50", options);
}

export async function listAnnouncements(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  return commFetch<Array<Record<string, unknown>>>("/api/v1/communications/announcements", options);
}

export async function getPreferences(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  return commFetch<Record<string, unknown>>("/api/v1/communications/preferences", options);
}
