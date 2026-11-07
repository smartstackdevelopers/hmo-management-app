/**
 * F2.9 tenant timeline API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type TimelineItem = {
  dedupe_key: string;
  activity_type: string;
  occurred_at: string;
  sort_at: string;
  title: string;
  summary?: string | null;
  status?: string | null;
  responsible_user_id?: string | null;
  reference?: string | null;
  resource_type: string;
  resource_id: string;
  detail_api_path: string;
  can_view: boolean;
};

export type TimelinePage = {
  items: TimelineItem[];
  page: number;
  page_size: number;
  total: number;
};

async function tlFetch<T>(
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

export function fetchTenantTimeline(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId: string;
  page?: number;
  pageSize?: number;
  sort?: "newest" | "oldest";
  activityType?: string[];
}): Promise<TimelinePage> {
  const params = new URLSearchParams();
  if (options.page) params.set("page", String(options.page));
  if (options.pageSize) params.set("page_size", String(options.pageSize));
  if (options.sort) params.set("sort", options.sort);
  if (options.activityType?.length) {
    for (const t of options.activityType) {
      params.append("activity_type", t);
    }
  }
  const q = params.toString();
  return tlFetch<TimelinePage>(
    `/api/v1/tenants/${options.tenantId}/timeline${q ? `?${q}` : ""}`,
    {
      accessToken: options.accessToken,
      organisationId: options.organisationId,
      role: options.role,
    },
  );
}
