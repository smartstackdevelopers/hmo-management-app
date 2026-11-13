import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AaAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function aaFetch<T>(path: string, options: AaAuth, init?: RequestInit): Promise<T> {
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

export function fetchAdvancedAutomationDashboard(options: AaAuth) {
  return aaFetch<Record<string, unknown>>("/api/v1/advanced-automation/dashboard", options);
}

export function fetchWorkflowTemplates(options: AaAuth) {
  return aaFetch<Record<string, unknown>[]>("/api/v1/advanced-automation/templates", options);
}

export function fetchWorkflows(options: AaAuth) {
  return aaFetch<Record<string, unknown>[]>("/api/v1/advanced-automation/workflows", options);
}
