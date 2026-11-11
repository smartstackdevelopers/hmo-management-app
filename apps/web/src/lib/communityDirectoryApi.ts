/**
 * F5.1 community directory admin API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CommunityService = {
  id: string;
  category: string;
  name: string;
  description: string | null;
  address_line: string | null;
  opening_days: string | null;
  opening_hours: string | null;
  eligibility: string | null;
  referral_requirements: string | null;
  contact: string | null;
  service_instructions: string | null;
  clothing_service_type: string | null;
  verification_status: string;
  information_source: string | null;
  verification_notes?: string | null;
  verified_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  is_published: boolean;
  created_by_user_id?: string | null;
  updated_by_user_id?: string | null;
  verified_by_user_id?: string | null;
};

export type VerificationEvent = {
  id: string;
  service_id: string;
  from_status: string | null;
  to_status: string;
  action: string;
  notes: string | null;
  actor_user_id: string | null;
  created_at: string;
};

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

async function directoryFetch<T>(
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

export function listAdminCommunityServices(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  q?: string;
  category?: string;
  verification_status?: string;
  page?: number;
  page_size?: number;
}) {
  const params = new URLSearchParams();
  if (options.q) params.set("q", options.q);
  if (options.category) params.set("category", options.category);
  if (options.verification_status) params.set("verification_status", options.verification_status);
  if (options.page) params.set("page", String(options.page));
  if (options.page_size) params.set("page_size", String(options.page_size));
  const query = params.toString();
  return directoryFetch<Page<CommunityService>>(
    `/api/v1/community-services/admin${query ? `?${query}` : ""}`,
    options,
  );
}

export function getAdminCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
}) {
  return directoryFetch<CommunityService>(
    `/api/v1/community-services/${options.serviceId}/admin`,
    options,
  );
}

export function createCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}) {
  return directoryFetch<CommunityService>("/api/v1/community-services", {
    ...options,
    method: "POST",
  });
}

export function updateCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
  body: Record<string, unknown>;
}) {
  return directoryFetch<CommunityService>(`/api/v1/community-services/${options.serviceId}`, {
    ...options,
    method: "PATCH",
  });
}

export function verifyCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
  notes?: string | null;
  publish?: boolean;
}) {
  return directoryFetch<CommunityService>(
    `/api/v1/community-services/${options.serviceId}/verify`,
    {
      ...options,
      method: "POST",
      body: { notes: options.notes ?? null, publish: options.publish ?? true },
    },
  );
}

export function flagOutdatedCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
  notes?: string | null;
}) {
  return directoryFetch<CommunityService>(
    `/api/v1/community-services/${options.serviceId}/flag-outdated`,
    {
      ...options,
      method: "POST",
      body: { notes: options.notes ?? null },
    },
  );
}

export function deactivateCommunityService(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
  notes?: string | null;
}) {
  return directoryFetch<CommunityService>(
    `/api/v1/community-services/${options.serviceId}/deactivate`,
    {
      ...options,
      method: "POST",
      body: { notes: options.notes ?? null },
    },
  );
}

export function listVerificationHistory(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
}) {
  return directoryFetch<{ items: VerificationEvent[] }>(
    `/api/v1/community-services/${options.serviceId}/verification-history`,
    options,
  );
}
