import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type PerfAuth = { accessToken: string; organisationId: string; role?: string | null };

async function pFetch<T>(path: string, options: PerfAuth, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({ organisationId: options.organisationId, role: options.role }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function fetchPerformanceDashboard(options: PerfAuth) {
  return pFetch<Record<string, unknown>>("/api/v1/performance/dashboard", options);
}

export function runPerformanceBenchmark(options: PerfAuth, samples = 10) {
  return pFetch<Record<string, unknown>>(`/api/v1/performance/benchmarks/run?samples=${samples}`, options, {
    method: "POST",
  });
}
