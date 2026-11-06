/**
 * F2.8 maintenance and repairs API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function maintenanceFetch<T>(
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

export type MaintenanceRequest = {
  id: string;
  reference_number: string;
  title: string;
  description: string;
  category_code: string;
  priority: string;
  status: string;
  property_id: string;
  room_id?: string | null;
  tenant_id?: string | null;
  reported_by_user_id?: string | null;
  assigned_user_id?: string | null;
  requires_approval: boolean;
  approval_status?: string | null;
  scheduled_visit_at?: string | null;
  visit_timezone: string;
  reported_at: string;
  acknowledged_at?: string | null;
  completed_at?: string | null;
  closed_at?: string | null;
  work_notes?: string | null;
  completion_summary?: string | null;
  is_emergency_priority: boolean;
  show_emergency_panel: boolean;
  emergency_kind_hint?: string | null;
  file_ids: string[];
  created_at: string;
};

export type MaintenanceDashboard = {
  total: number;
  open_count: number;
  by_priority: Record<string, number>;
  emergency: number;
  urgent_and_emergency: number;
  awaiting_approval: number;
  scheduled_visits: number;
  in_progress: number;
  overdue_scheduled: number;
  recently_completed: number;
};

export type MaintenanceHistoryEvent = {
  id: string;
  event_type: string;
  summary: string;
  detail?: string | null;
  created_at: string;
};

export type MaintenanceNote = {
  id: string;
  visibility: string;
  body: string;
  created_at: string;
};

export type MaintenanceVisit = {
  id: string;
  request_id: string;
  assignee_user_id?: string | null;
  scheduled_at: string;
  timezone: string;
  status: string;
  work_notes?: string | null;
  cancel_reason?: string | null;
  completed_at?: string | null;
};

export type MaintenanceCategory = {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  triggers_emergency_panel: boolean;
  emergency_kind?: string | null;
};

export type EmergencyContent = {
  kind: string;
  title: string;
  body: string;
  requires_formal_approval: boolean;
  approved_for_use: boolean;
};

export type RequestFileLink = {
  file_id: string;
  caption?: string | null;
  photo_kind: string;
  created_at: string;
};

export function maintenancePriorityBadgeClass(priority: string): string {
  if (priority === "emergency") return "bg-red-200 text-red-950 border-red-500 font-semibold";
  if (priority === "urgent") return "bg-red-100 text-red-900 border-red-300";
  if (priority === "high") return "bg-orange-100 text-orange-900 border-orange-300";
  if (priority === "low") return "bg-slate-100 text-slate-700 border-slate-300";
  return "bg-sky-100 text-sky-900 border-sky-300";
}

export function isEmergencyRequest(row: Pick<MaintenanceRequest, "is_emergency_priority" | "priority">): boolean {
  return row.is_emergency_priority || row.priority === "emergency";
}

export async function seedMaintenanceDefaults(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<{ status: string }> {
  return maintenanceFetch("/api/v1/maintenance/seed-defaults", { ...options, method: "POST", body: {} });
}

export async function listMaintenanceCategories(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<MaintenanceCategory[]> {
  return maintenanceFetch("/api/v1/maintenance/categories", options);
}

export async function fetchMaintenanceDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<MaintenanceDashboard> {
  return maintenanceFetch("/api/v1/maintenance/dashboard", options);
}

export async function listMaintenanceRequests(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  status?: string;
  priority?: string;
  propertyId?: string;
  pendingApproval?: boolean;
  q?: string;
  page?: number;
}): Promise<Page<MaintenanceRequest>> {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  if (options.priority) params.set("priority", options.priority);
  if (options.propertyId) params.set("property_id", options.propertyId);
  if (options.pendingApproval) params.set("pending_approval", "true");
  if (options.q) params.set("q", options.q);
  if (options.page) params.set("page", String(options.page));
  const qs = params.toString();
  return maintenanceFetch(`/api/v1/maintenance${qs ? `?${qs}` : ""}`, options);
}

export async function fetchMaintenanceRequest(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}`, options);
}

export async function createMaintenanceRequest(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: {
    title: string;
    description: string;
    category_code?: string;
    priority?: string;
    property_id: string;
    room_id?: string | null;
    tenant_id?: string | null;
    requires_approval?: boolean;
  };
}): Promise<MaintenanceRequest> {
  return maintenanceFetch("/api/v1/maintenance", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function transitionMaintenance(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  body: { status: string; note?: string };
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/transition`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function changeMaintenancePriority(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  priority: string;
  reason: string;
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/priority`, {
    ...options,
    method: "POST",
    body: { priority: options.priority, reason: options.reason },
  });
}

export async function assignMaintenance(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  assignedUserId: string | null;
  note?: string;
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/assign`, {
    ...options,
    method: "POST",
    body: { assigned_user_id: options.assignedUserId, note: options.note },
  });
}

export async function maintenanceApproval(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  decision: "approved" | "rejected";
  reason?: string;
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/approval`, {
    ...options,
    method: "POST",
    body: { decision: options.decision, reason: options.reason },
  });
}

export async function scheduleMaintenanceVisit(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  scheduled_at: string;
  timezone?: string;
  assignee_user_id?: string | null;
  link_tenant_visit_id?: string | null;
}): Promise<MaintenanceVisit> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/schedule`, {
    ...options,
    method: "POST",
    body: {
      scheduled_at: options.scheduled_at,
      timezone: options.timezone ?? "Europe/London",
      assignee_user_id: options.assignee_user_id,
      link_tenant_visit_id: options.link_tenant_visit_id,
    },
  });
}

export async function listMaintenanceVisits(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
}): Promise<MaintenanceVisit[]> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/visits`, options);
}

export async function rescheduleMaintenanceVisit(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  visitId: string;
  scheduled_at: string;
  timezone?: string;
  assignee_user_id?: string | null;
}): Promise<MaintenanceVisit> {
  return maintenanceFetch(
    `/api/v1/maintenance/${options.requestId}/visits/${options.visitId}/reschedule`,
    {
      ...options,
      method: "POST",
      body: {
        scheduled_at: options.scheduled_at,
        timezone: options.timezone ?? "Europe/London",
        assignee_user_id: options.assignee_user_id,
      },
    },
  );
}

export async function cancelMaintenanceVisit(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  visitId: string;
  reason: string;
}): Promise<MaintenanceVisit> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/visits/${options.visitId}/cancel`, {
    ...options,
    method: "POST",
    body: { reason: options.reason },
  });
}

export async function completeMaintenanceVisitOutcome(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  visitId: string;
  work_notes?: string;
  missed?: boolean;
}): Promise<MaintenanceVisit> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/visits/${options.visitId}/complete`, {
    ...options,
    method: "POST",
    body: { work_notes: options.work_notes, missed: options.missed ?? false },
  });
}

export async function addMaintenanceNote(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  body: { body: string; visibility?: string };
}): Promise<MaintenanceNote> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/notes`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function listMaintenanceNotes(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
}): Promise<MaintenanceNote[]> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/notes`, options);
}

export async function listMaintenanceHistory(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
}): Promise<MaintenanceHistoryEvent[]> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/history`, options);
}

export async function listMaintenanceFiles(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
}): Promise<RequestFileLink[]> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/files`, options);
}

export async function completeMaintenanceWork(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  work_notes: string;
  completion_summary?: string;
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/complete`, {
    ...options,
    method: "POST",
    body: { work_notes: options.work_notes, completion_summary: options.completion_summary },
  });
}

export async function associateMaintenancePhoto(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  file_id: string;
  caption?: string;
  photo_kind?: string;
}): Promise<MaintenanceRequest> {
  return maintenanceFetch(`/api/v1/maintenance/${options.requestId}/files`, {
    ...options,
    method: "POST",
    body: {
      file_id: options.file_id,
      caption: options.caption,
      photo_kind: options.photo_kind ?? "problem",
    },
  });
}

export async function uploadMaintenancePhotoMultipart(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  requestId: string;
  file: File;
  caption?: string;
  photoKind?: string;
}): Promise<MaintenanceRequest> {
  const fd = new FormData();
  fd.append("upload", options.file);
  if (options.caption) fd.append("caption", options.caption);
  if (options.photoKind) fd.append("photo_kind", options.photoKind);

  const response = await fetch(`${API_BASE}/api/v1/maintenance/${options.requestId}/files/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
    body: fd,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error((await response.text()) || `Upload failed (${response.status})`);
  }
  return (await response.json()) as MaintenanceRequest;
}

export function maintenancePhotoDownloadUrl(
  requestId: string,
  fileId: string,
  apiBase: string = API_BASE,
): string {
  return `${apiBase}/api/v1/maintenance/${requestId}/files/${fileId}/content`;
}

export async function fetchEmergencyContent(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  kind: "gas" | "fire";
}): Promise<EmergencyContent> {
  return maintenanceFetch(`/api/v1/maintenance/emergency/${options.kind}`, options);
}
