/**
 * F2.4 incidents / follow-ups / workload API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function incidentsFetch<T>(
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

export type Incident = {
  id: string;
  reference_number: string;
  title: string;
  category: string;
  description: string;
  occurred_at: string;
  severity: string;
  status: string;
  open_follow_up_count: number;
  reviewer_user_id?: string | null;
};

export type FollowUp = {
  id: string;
  incident_id: string;
  description: string;
  assigned_user_id: string;
  priority: string;
  due_at?: string | null;
  status: string;
};

export type WorkloadResponse = {
  organisation_id: string;
  scope: string;
  staff: Array<{
    staff_user_id: string;
    assigned_tenants: number;
    open_tasks: number;
    overdue_tasks: number;
    upcoming_visits: number;
    pending_handovers: number;
    open_incident_follow_ups: number;
    overdue_incident_follow_ups: number;
  }>;
};

export function fetchIncidents(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  status?: string;
}): Promise<Page<Incident>> {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  const qs = params.toString();
  return incidentsFetch(`/api/v1/incidents${qs ? `?${qs}` : ""}`, options);
}

export function createIncident(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<Incident> {
  return incidentsFetch("/api/v1/incidents", { ...options, method: "POST", body: options.body });
}

export function fetchIncident(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  incidentId: string;
}): Promise<Incident> {
  return incidentsFetch(`/api/v1/incidents/${options.incidentId}`, options);
}

export function submitIncident(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  incidentId: string;
}): Promise<Incident> {
  return incidentsFetch(`/api/v1/incidents/${options.incidentId}/submit`, {
    ...options,
    method: "POST",
  });
}

export function patchIncident(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  incidentId: string;
  body: Record<string, unknown>;
}): Promise<Incident> {
  return incidentsFetch(`/api/v1/incidents/${options.incidentId}`, {
    ...options,
    method: "PATCH",
    body: options.body,
  });
}

export function fetchIncidentFollowUps(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  incidentId: string;
}): Promise<Page<FollowUp>> {
  return incidentsFetch(`/api/v1/incidents/${options.incidentId}/follow-ups`, options);
}

export function createFollowUp(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  incidentId: string;
  body: Record<string, unknown>;
}): Promise<FollowUp> {
  return incidentsFetch(`/api/v1/incidents/${options.incidentId}/follow-ups`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function completeFollowUp(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  followUpId: string;
}): Promise<FollowUp> {
  return incidentsFetch(`/api/v1/incident-follow-ups/${options.followUpId}/complete`, {
    ...options,
    method: "POST",
  });
}

export function fetchWorkload(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  staffUserId?: string;
}): Promise<WorkloadResponse> {
  const params = new URLSearchParams();
  if (options.staffUserId) params.set("staff_user_id", options.staffUserId);
  const qs = params.toString();
  return incidentsFetch(`/api/v1/workload${qs ? `?${qs}` : ""}`, options);
}
