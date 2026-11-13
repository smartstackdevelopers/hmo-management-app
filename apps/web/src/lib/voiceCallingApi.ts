import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function vFetch<T>(
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

export function getVoiceDashboard(accessToken: string, organisationId: string) {
  return vFetch<Record<string, unknown>>("/api/v1/voice-calling/dashboard", accessToken, organisationId);
}

export function listVoiceCalls(accessToken: string, organisationId: string) {
  return vFetch<Record<string, unknown>[]>("/api/v1/voice-calling/calls", accessToken, organisationId);
}
