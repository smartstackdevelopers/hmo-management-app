import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ReportAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

export type ReportCategory = "housing" | "complaints" | "caseload" | "occupancy" | "plans";
export type ExportFormat = "csv" | "pdf" | "xlsx";

async function reportFetch<T>(path: string, options: ReportAuth, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return undefined as T;
}

export function fetchReportingDashboard(options: ReportAuth & { createdFrom?: string; createdTo?: string }) {
  const params = new URLSearchParams();
  if (options.createdFrom) params.set("created_from", options.createdFrom);
  if (options.createdTo) params.set("created_to", options.createdTo);
  const q = params.toString();
  return reportFetch<Record<string, unknown>>(`/api/v1/reports/dashboard${q ? `?${q}` : ""}`, options);
}

export function fetchReportSummary(
  category: ReportCategory,
  options: ReportAuth & {
    created_from?: string;
    created_to?: string;
    status?: string;
    building?: string;
    property_id?: string;
    support_worker_user_id?: string;
  },
) {
  const params = new URLSearchParams();
  for (const key of [
    "created_from",
    "created_to",
    "status",
    "building",
    "property_id",
    "support_worker_user_id",
  ] as const) {
    const v = options[key];
    if (v) params.set(key, v);
  }
  const q = params.toString();
  return reportFetch<Record<string, unknown>>(`/api/v1/reports/${category}/summary${q ? `?${q}` : ""}`, options);
}

export function fetchReportRows(
  category: ReportCategory,
  options: ReportAuth & {
    page?: number;
    page_size?: number;
    created_from?: string;
    created_to?: string;
    status?: string;
    building?: string;
    property_id?: string;
    support_worker_user_id?: string;
  },
) {
  const params = new URLSearchParams();
  for (const key of [
    "created_from",
    "created_to",
    "status",
    "building",
    "property_id",
    "support_worker_user_id",
    "page",
    "page_size",
  ] as const) {
    const v = options[key];
    if (v == null || v === "") continue;
    params.set(key, String(v));
  }
  const q = params.toString();
  return reportFetch<{ items: Record<string, unknown>[]; total: number; page: number; page_size: number }>(
    `/api/v1/reports/${category}/rows${q ? `?${q}` : ""}`,
    options,
  );
}

export function exportReportUrl(
  reportType: ReportCategory,
  format: ExportFormat,
  query?: Record<string, string | undefined>,
) {
  const params = new URLSearchParams();
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v) params.set(k, v);
    }
  }
  const q = params.toString();
  return `${API_BASE}/api/v1/reports/export/${reportType}/${format}${q ? `?${q}` : ""}`;
}

export async function downloadReportExport(
  reportType: ReportCategory,
  format: ExportFormat,
  options: ReportAuth & { createdFrom?: string; createdTo?: string },
) {
  const params = new URLSearchParams();
  if (options.createdFrom) params.set("created_from", options.createdFrom);
  if (options.createdTo) params.set("created_to", options.createdTo);
  const q = params.toString();
  const response = await fetch(`${API_BASE}/api/v1/reports/export/${reportType}/${format}${q ? `?${q}` : ""}`, {
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
  });
  if (!response.ok) throw new Error(await response.text());
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `hmore-${reportType}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export function fetchSchedules(options: ReportAuth) {
  return reportFetch<{ items: Record<string, unknown>[] }>("/api/v1/reports/schedules", options);
}

export function createSchedule(options: ReportAuth, body: Record<string, unknown>) {
  return reportFetch<Record<string, unknown>>("/api/v1/reports/schedules", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateSchedule(options: ReportAuth, scheduleId: string, body: Record<string, unknown>) {
  return reportFetch<Record<string, unknown>>(`/api/v1/reports/schedules/${scheduleId}`, options, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function fetchScheduleRuns(options: ReportAuth, scheduleId?: string) {
  const q = scheduleId ? `?schedule_id=${scheduleId}` : "";
  return reportFetch<{ items: Record<string, unknown>[] }>(`/api/v1/reports/schedules/runs${q}`, options);
}

export function retryScheduleRun(options: ReportAuth, runId: string) {
  return reportFetch<Record<string, unknown>>(`/api/v1/reports/schedules/runs/${runId}/retry`, options, {
    method: "POST",
  });
}

export function fetchAlerts(options: ReportAuth & { status?: string; page?: number }) {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  if (options.page) params.set("page", String(options.page));
  const q = params.toString();
  return reportFetch<{ items: Record<string, unknown>[]; total: number }>(
    `/api/v1/reports/alerts${q ? `?${q}` : ""}`,
    options,
  );
}

export function updateAlertStatus(options: ReportAuth, alertId: string, status: string) {
  return reportFetch<Record<string, unknown>>(`/api/v1/reports/alerts/${alertId}`, options, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function fetchAlertThresholds(options: ReportAuth) {
  return reportFetch<{ items: Record<string, unknown>[] }>("/api/v1/reports/alerts/thresholds", options);
}

export function evaluateAlerts(options: ReportAuth) {
  return reportFetch<Record<string, unknown>>("/api/v1/reports/alerts/evaluate", options, { method: "POST" });
}
