/**
 * F2.10 structured support plans API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type SupportPlanListItem = {
  id: string;
  reference_number: string;
  title: string;
  status: string;
  planned_review_date?: string | null;
  tenant_id: string;
};

export type Paged<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

async function spFetch<T>(
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

export async function fetchSupportPlansDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId?: string;
  workerUserId?: string;
  planStatus?: string;
}): Promise<Record<string, unknown>> {
  const q = new URLSearchParams();
  if (options.tenantId) {
    q.set("tenant_id", options.tenantId);
  }
  if (options.workerUserId) {
    q.set("worker_user_id", options.workerUserId);
  }
  if (options.planStatus) {
    q.set("plan_status", options.planStatus);
  }
  const suffix = q.toString() ? `?${q.toString()}` : "";
  return spFetch<Record<string, unknown>>(`/api/v1/support-plans/dashboard${suffix}`, options);
}

export async function fetchTenantSupportPlans(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId: string;
  page?: number;
  pageSize?: number;
  status?: string;
}): Promise<Paged<SupportPlanListItem & Record<string, unknown>>> {
  const q = new URLSearchParams();
  q.set("page", String(options.page ?? 1));
  q.set("page_size", String(options.pageSize ?? 20));
  if (options.status) {
    q.set("status", options.status);
  }
  return spFetch(`/api/v1/tenants/${options.tenantId}/support-plans?${q.toString()}`, options);
}

export async function createSupportPlan(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId: string;
  body: {
    title: string;
    responsible_worker_user_id: string;
    description?: string;
    support_objectives?: string;
    start_date?: string;
    planned_review_date?: string;
  };
}): Promise<Record<string, unknown>> {
  return spFetch(`/api/v1/tenants/${options.tenantId}/support-plans`, {
    ...options,
    method: "POST",
    body: {
      tenant_id: options.tenantId,
      ...options.body,
    },
  });
}
