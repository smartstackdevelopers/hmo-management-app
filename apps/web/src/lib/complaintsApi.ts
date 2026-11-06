/**
 * F2.7 complaints workflow API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function complaintsFetch<T>(
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

export type Complaint = {
  id: string;
  reference_number: string;
  title: string;
  description: string;
  category_code: string;
  priority: string;
  status: string;
  tenant_id?: string | null;
  assigned_user_id?: string | null;
  property_id?: string | null;
  submitted_at: string;
  acknowledge_due_at?: string | null;
  response_due_at?: string | null;
  resolution_summary?: string | null;
  tenant_visible_summary?: string | null;
  is_overdue: boolean;
  open_escalation: boolean;
  file_ids: string[];
};

export type ComplaintDashboard = {
  total: number;
  open_count: number;
  by_priority: Record<string, number>;
  awaiting_investigation: number;
  upcoming_deadlines: number;
  overdue: number;
  escalated: number;
  recently_resolved: number;
};

export type HistoryEvent = {
  id: string;
  event_type: string;
  summary: string;
  detail?: string | null;
  created_at: string;
  is_tenant_visible: boolean;
};

export type ComplaintNote = {
  id: string;
  visibility: string;
  body: string;
  is_follow_up: boolean;
  created_at: string;
};

export function priorityBadgeClass(priority: string): string {
  if (priority === "urgent") return "bg-red-100 text-red-900 border-red-300";
  if (priority === "high") return "bg-orange-100 text-orange-900 border-orange-300";
  if (priority === "low") return "bg-slate-100 text-slate-700 border-slate-300";
  return "bg-sky-100 text-sky-900 border-sky-300";
}

export function isComplaintOverdue(complaint: Pick<Complaint, "is_overdue">): boolean {
  return Boolean(complaint.is_overdue);
}

export async function fetchComplaintDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<ComplaintDashboard> {
  return complaintsFetch("/api/v1/complaints/dashboard", options);
}

export async function listComplaints(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  status?: string;
  priority?: string;
  overdueOnly?: boolean;
  escalatedOnly?: boolean;
  q?: string;
  page?: number;
}): Promise<Page<Complaint>> {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  if (options.priority) params.set("priority", options.priority);
  if (options.overdueOnly) params.set("overdue_only", "true");
  if (options.escalatedOnly) params.set("escalated_only", "true");
  if (options.q) params.set("q", options.q);
  if (options.page) params.set("page", String(options.page));
  const qs = params.toString();
  return complaintsFetch(`/api/v1/complaints${qs ? `?${qs}` : ""}`, options);
}

export async function fetchComplaint(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
}): Promise<Complaint> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}`, options);
}

export async function createComplaint(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: {
    title: string;
    description: string;
    category_code?: string;
    priority?: string;
    tenant_id?: string;
    property_id?: string;
  };
}): Promise<Complaint> {
  return complaintsFetch("/api/v1/complaints", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function transitionComplaint(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
  body: {
    status: string;
    note?: string;
    resolution_summary?: string;
    tenant_visible_summary?: string;
  };
}): Promise<Complaint> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/transition`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function changeComplaintPriority(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
  priority: string;
  reason: string;
}): Promise<Complaint> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/priority`, {
    ...options,
    method: "POST",
    body: { priority: options.priority, reason: options.reason },
  });
}

export async function assignComplaint(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
  assignedUserId: string | null;
  note?: string;
}): Promise<Complaint> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/assign`, {
    ...options,
    method: "POST",
    body: { assigned_user_id: options.assignedUserId, note: options.note },
  });
}

export async function addComplaintNote(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
  body: { body: string; visibility?: string; is_follow_up?: boolean };
}): Promise<ComplaintNote> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/notes`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function listComplaintNotes(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
}): Promise<ComplaintNote[]> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/notes`, options);
}

export async function listComplaintHistory(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
}): Promise<HistoryEvent[]> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/history`, options);
}

export async function escalateComplaint(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
  reason: string;
  idempotencyKey?: string;
}): Promise<unknown> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/escalate`, {
    ...options,
    method: "POST",
    body: { reason: options.reason, idempotency_key: options.idempotencyKey },
  });
}

export async function updateComplaintDeadlines(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  complaintId: string;
  responseDueAt?: string;
  acknowledgeDueAt?: string;
  reason: string;
}): Promise<Complaint> {
  return complaintsFetch(`/api/v1/complaints/${options.complaintId}/deadlines`, {
    ...options,
    method: "POST",
    body: {
      response_due_at: options.responseDueAt,
      acknowledge_due_at: options.acknowledgeDueAt,
      reason: options.reason,
    },
  });
}

export async function seedComplaintDefaults(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<{ status: string }> {
  return complaintsFetch("/api/v1/complaints/seed-defaults", {
    ...options,
    method: "POST",
    body: {},
  });
}
