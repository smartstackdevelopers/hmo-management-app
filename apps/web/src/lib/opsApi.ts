/**
 * F2.2 rota / visits / tasks API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function opsFetch<T>(
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

export type Shift = {
  id: string;
  staff_user_id: string;
  shift_date: string;
  starts_at: string;
  ends_at: string;
  shift_type: string;
  status: string;
  location?: string | null;
};

export type Visit = {
  id: string;
  tenant_id: string;
  assigned_staff_user_id: string;
  scheduled_at: string;
  purpose: string;
  status: string;
};

export type TaskItem = {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_at?: string | null;
  overdue: boolean;
  assigned_user_id: string;
};

export function fetchShifts(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<Page<Shift>> {
  return opsFetch("/api/v1/shifts", options);
}

export function fetchVisits(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  upcomingOnly?: boolean;
}): Promise<Page<Visit>> {
  const params = new URLSearchParams();
  if (options.upcomingOnly) params.set("upcoming_only", "true");
  return opsFetch(`/api/v1/visits?${params}`, options);
}

export function fetchTasks(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  overdueOnly?: boolean;
}): Promise<Page<TaskItem>> {
  const params = new URLSearchParams();
  if (options.overdueOnly) params.set("overdue_only", "true");
  return opsFetch(`/api/v1/tasks?${params}`, options);
}

export function createShift(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<Shift> {
  return opsFetch("/api/v1/shifts", { ...options, method: "POST", body: options.body });
}

export function createVisit(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<Visit> {
  return opsFetch("/api/v1/visits", { ...options, method: "POST", body: options.body });
}

export function createTask(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<TaskItem> {
  return opsFetch("/api/v1/tasks", { ...options, method: "POST", body: options.body });
}
