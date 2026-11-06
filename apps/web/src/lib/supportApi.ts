/**
 * F2.1 support caseload / daily log / handover API client (browser + server).
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CaseAssignment = {
  id: string;
  organisation_id: string;
  tenant_id: string;
  support_worker_user_id: string;
  status: string;
  assigned_at: string;
  ended_at?: string | null;
  assignment_notes?: string | null;
  tenant_preferred_name?: string | null;
  tenant_full_name?: string | null;
  support_worker_display_name?: string | null;
  recent_log_count?: number | null;
  pending_handover_count?: number | null;
};

export type DailyLog = {
  id: string;
  organisation_id: string;
  tenant_id: string;
  author_user_id: string;
  log_date: string;
  logged_at: string;
  activity_category: string;
  summary: string;
  notes: string;
  interaction_type?: string | null;
  follow_up_required: boolean;
  next_action?: string | null;
  status: string;
};

export type Handover = {
  id: string;
  organisation_id: string;
  tenant_id: string;
  created_by_user_id: string;
  recipient_user_id: string;
  handover_at: string;
  summary: string;
  case_updates?: string | null;
  outstanding_tasks?: string | null;
  follow_up_actions?: string | null;
  priority: string;
  status: string;
  acknowledged_at?: string | null;
  completed_at?: string | null;
};

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function supportFetch<T>(
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
  return (await response.json()) as T;
}

export function fetchCaseload(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  q?: string;
  page?: number;
}): Promise<Page<CaseAssignment>> {
  const params = new URLSearchParams();
  params.set("page", String(options.page ?? 1));
  if (options.q) {
    params.set("q", options.q);
  }
  return supportFetch(`/api/v1/caseload?${params}`, options);
}

export function fetchCaseDetail(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId: string;
}): Promise<{
  tenant: Record<string, unknown>;
  assignments: CaseAssignment[];
  recent_logs: DailyLog[];
  recent_handovers: Handover[];
}> {
  return supportFetch(`/api/v1/caseload/tenants/${options.tenantId}`, options);
}

export function createDailyLog(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<DailyLog> {
  return supportFetch(`/api/v1/daily-logs`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function fetchHandovers(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  pendingOnly?: boolean;
}): Promise<Page<Handover>> {
  const params = new URLSearchParams();
  if (options.pendingOnly) {
    params.set("pending_only", "true");
  }
  return supportFetch(`/api/v1/handovers?${params}`, options);
}

export function createHandover(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}): Promise<Handover> {
  return supportFetch(`/api/v1/handovers`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function transitionHandover(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  handoverId: string;
  action: "submit" | "acknowledge" | "complete" | "cancel";
}): Promise<Handover> {
  return supportFetch(`/api/v1/handovers/${options.handoverId}/${options.action}`, {
    ...options,
    method: "POST",
  });
}

export function createCaseAssignment(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: { tenant_id: string; support_worker_user_id: string; assignment_notes?: string };
}): Promise<CaseAssignment> {
  return supportFetch(`/api/v1/case-assignments`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}
