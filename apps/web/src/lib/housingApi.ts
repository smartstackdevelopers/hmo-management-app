/**
 * F2.5 housing applications / waiting list / approvals API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function housingFetch<T>(
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

export type HousingApplication = {
  id: string;
  reference_number: string;
  tenant_id: string;
  status: string;
  priority: string;
  housing_requirements: string;
  accommodation_type?: string | null;
  reviewer_user_id?: string | null;
  on_waiting_list: boolean;
  waiting_list_position?: number | null;
  information_required_notes?: string | null;
  submitted_at?: string | null;
};

export type WaitingListEntry = {
  id: string;
  application_id: string;
  position: number;
  status: string;
  priority: string;
  application_reference?: string | null;
  application_status?: string | null;
  tenant_id?: string | null;
};

export function fetchApplications(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  status?: string;
  pendingApprovals?: boolean;
  q?: string;
}): Promise<Page<HousingApplication>> {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  if (options.pendingApprovals) params.set("pending_approvals", "true");
  if (options.q) params.set("q", options.q);
  const qs = params.toString();
  return housingFetch(`/api/v1/housing-applications${qs ? `?${qs}` : ""}`, options);
}

export function createApplication(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<HousingApplication> {
  return housingFetch("/api/v1/housing-applications", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function fetchApplication(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
}): Promise<HousingApplication> {
  return housingFetch(`/api/v1/housing-applications/${options.applicationId}`, options);
}

export function submitApplication(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
}): Promise<HousingApplication> {
  return housingFetch(`/api/v1/housing-applications/${options.applicationId}/submit`, {
    ...options,
    method: "POST",
  });
}

export function decideApplication(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
  body: Record<string, unknown>;
}): Promise<unknown> {
  return housingFetch(`/api/v1/housing-applications/${options.applicationId}/decide`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function requestApplicationInformation(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
  notes: string;
}): Promise<HousingApplication> {
  return housingFetch(
    `/api/v1/housing-applications/${options.applicationId}/request-information`,
    {
      ...options,
      method: "POST",
      body: { notes: options.notes },
    },
  );
}

export function fetchWaitingList(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<Page<WaitingListEntry>> {
  return housingFetch("/api/v1/waiting-list?status=active", options);
}

export function addToWaitingList(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<WaitingListEntry> {
  return housingFetch("/api/v1/waiting-list", {
    ...options,
    method: "POST",
    body: options.body,
  });
}
