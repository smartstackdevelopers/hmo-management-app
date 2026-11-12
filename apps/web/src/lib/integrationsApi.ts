import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type IntegrationAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function intFetch<T>(path: string, options: IntegrationAuth, init?: RequestInit): Promise<T> {
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

export function fetchIntegrationsDashboard(options: IntegrationAuth) {
  return intFetch<Record<string, unknown>>("/api/v1/integrations/dashboard", options);
}

export function fetchIntegrations(options: IntegrationAuth & { category?: string }) {
  const params = new URLSearchParams();
  if (options.category) params.set("category", options.category);
  const q = params.toString();
  return intFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/integrations${q ? `?${q}` : ""}`,
    options,
  );
}

export function createIntegration(options: IntegrationAuth, body: Record<string, unknown>) {
  return intFetch<Record<string, unknown>>("/api/v1/integrations", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateIntegration(
  options: IntegrationAuth,
  integrationId: string,
  body: Record<string, unknown>,
) {
  return intFetch<Record<string, unknown>>(`/api/v1/integrations/${integrationId}`, options, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function testIntegrationConnection(options: IntegrationAuth, integrationId: string) {
  return intFetch<Record<string, unknown>>(
    `/api/v1/integrations/${integrationId}/test-connection`,
    options,
    { method: "POST" },
  );
}

export function startIntegrationSync(
  options: IntegrationAuth,
  integrationId: string,
  direction = "health_check",
) {
  return intFetch<Record<string, unknown>>(`/api/v1/integrations/${integrationId}/sync`, options, {
    method: "POST",
    body: JSON.stringify({ direction }),
  });
}

export function fetchIntegrationSyncJobs(options: IntegrationAuth & { status?: string }) {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  const q = params.toString();
  return intFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/integrations/sync-jobs${q ? `?${q}` : ""}`,
    options,
  );
}

export function fetchIntegrationActivity(options: IntegrationAuth) {
  return intFetch<{ items: Record<string, unknown>[] }>("/api/v1/integrations/activity", options);
}

export function createIntegrationMapping(
  options: IntegrationAuth,
  integrationId: string,
  body: Record<string, unknown>,
) {
  return intFetch<Record<string, unknown>>(`/api/v1/integrations/${integrationId}/mappings`, options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
