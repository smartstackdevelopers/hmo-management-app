import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type WellbeingResource = {
  id: string;
  kind: string;
  category: string;
  title: string;
  description: string | null;
  verification_status: string;
  is_saved?: boolean;
};

async function wellbeingFetch<T>(
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

export function createWellbeingResource(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}) {
  return wellbeingFetch<WellbeingResource>("/api/v1/wellbeing/admin/resources", {
    ...options,
    method: "POST",
  });
}

export function createWellbeingDirectoryEntry(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}) {
  return wellbeingFetch<Record<string, unknown>>("/api/v1/wellbeing/admin/directory", {
    ...options,
    method: "POST",
  });
}
