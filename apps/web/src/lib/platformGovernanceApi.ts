import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type GovAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function govFetch<T>(path: string, options: GovAuth, init?: RequestInit): Promise<T> {
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

export function fetchOrgGovernanceDashboard(options: GovAuth) {
  return govFetch<Record<string, unknown>>("/api/v1/platform-governance/org/dashboard", options);
}
