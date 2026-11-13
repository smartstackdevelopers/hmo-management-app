import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function rFetch<T>(
  path: string,
  accessToken: string,
  organisationId: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({ organisationId }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function getRentPaymentsDashboard(accessToken: string, organisationId: string) {
  return rFetch<Record<string, unknown>>("/api/v1/rent-payments/dashboard", accessToken, organisationId);
}

export function listRentObligations(accessToken: string, organisationId: string) {
  return rFetch<Record<string, unknown>[]>("/api/v1/rent-payments/obligations", accessToken, organisationId);
}
