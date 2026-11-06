/**
 * F2.3 training / safeguarding API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function complianceFetch<T>(
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

export type TrainingRecord = {
  id: string;
  staff_user_id: string;
  title: string;
  category: string;
  provider?: string | null;
  completion_date?: string | null;
  expiry_date?: string | null;
  status: string;
  effective_status: string;
  notes?: string | null;
};

export type SafeguardingReminder = {
  id: string;
  title: string;
  category: string;
  description?: string | null;
  due_at: string;
  priority: string;
  status: string;
  assigned_user_id: string;
  tenant_id?: string | null;
};

export function fetchTraining(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    expiringOnly?: boolean;
    expiredOnly?: boolean;
  },
): Promise<Page<TrainingRecord>> {
  const params = new URLSearchParams();
  if (options.expiringOnly) params.set("expiring_only", "true");
  if (options.expiredOnly) params.set("expired_only", "true");
  const qs = params.toString();
  return complianceFetch(`/api/v1/training${qs ? `?${qs}` : ""}`, options);
}

export function createTraining(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    body: Record<string, unknown>;
  },
): Promise<TrainingRecord> {
  return complianceFetch("/api/v1/training", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function fetchSafeguardingReminders(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    overdueOnly?: boolean;
  },
): Promise<Page<SafeguardingReminder>> {
  const params = new URLSearchParams();
  if (options.overdueOnly) params.set("overdue_only", "true");
  const qs = params.toString();
  return complianceFetch(`/api/v1/safeguarding-reminders${qs ? `?${qs}` : ""}`, options);
}

export function createSafeguardingReminder(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    body: Record<string, unknown>;
  },
): Promise<SafeguardingReminder> {
  return complianceFetch("/api/v1/safeguarding-reminders", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function acknowledgeSafeguardingReminder(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    reminderId: string;
  },
): Promise<SafeguardingReminder> {
  return complianceFetch(`/api/v1/safeguarding-reminders/${options.reminderId}/acknowledge`, {
    ...options,
    method: "POST",
  });
}

export function completeSafeguardingReminder(
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    reminderId: string;
  },
): Promise<SafeguardingReminder> {
  return complianceFetch(`/api/v1/safeguarding-reminders/${options.reminderId}/complete`, {
    ...options,
    method: "POST",
  });
}
