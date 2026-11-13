import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HubAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function hubFetch<T>(path: string, options: HubAuth, init?: RequestInit): Promise<T> {
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
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function fetchIntegrationHubDashboard(options: HubAuth) {
  return hubFetch<Record<string, unknown>>("/api/v1/integration-hub/dashboard", options);
}

export function fetchHubProviders(options: HubAuth & { category?: string }) {
  const params = new URLSearchParams();
  if (options.category) params.set("category", options.category);
  const q = params.toString();
  return hubFetch<Record<string, unknown>[]>(`/api/v1/integration-hub/providers${q ? `?${q}` : ""}`, options);
}

export function fetchHubHealth(options: HubAuth) {
  return hubFetch<Record<string, unknown>[]>("/api/v1/integration-hub/health", options);
}
