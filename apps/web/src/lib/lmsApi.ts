import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function lFetch<T>(path: string, accessToken: string, organisationId: string, init?: RequestInit): Promise<T> {
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

export function getLmsLearnDashboard(accessToken: string, organisationId: string) {
  return lFetch<Record<string, unknown>>("/api/v1/lms/learn/dashboard", accessToken, organisationId);
}

export function listLmsCourses(accessToken: string, organisationId: string) {
  return lFetch<Record<string, unknown>[]>("/api/v1/lms/learn/courses", accessToken, organisationId);
}
