import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type PrivacyAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function privFetch<T>(path: string, options: PrivacyAuth, init?: RequestInit): Promise<T> {
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

export function fetchPrivacyDashboard(options: PrivacyAuth) {
  return privFetch<Record<string, unknown>>("/api/v1/privacy/dashboard", options);
}

export function bootstrapPrivacyCatalog(options: PrivacyAuth) {
  return privFetch<Record<string, unknown>>("/api/v1/privacy/bootstrap", options, { method: "POST" });
}

export function fetchPrivacyInventory(options: PrivacyAuth) {
  return privFetch<Record<string, unknown>[]>("/api/v1/privacy/inventory", options);
}

export function fetchDpiaRegister(options: PrivacyAuth) {
  return privFetch<Record<string, unknown>[]>("/api/v1/privacy/dpia", options);
}

export function fetchDataSubjectRequests(options: PrivacyAuth) {
  return privFetch<Record<string, unknown>[]>("/api/v1/privacy/data-subject-requests", options);
}

export function fetchPrivacyRisks(options: PrivacyAuth) {
  return privFetch<Record<string, unknown>[]>("/api/v1/privacy/risks", options);
}
