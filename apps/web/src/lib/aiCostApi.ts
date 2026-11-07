import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type FetchOpts = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  query?: Record<string, string | undefined>;
};

function buildUrl(path: string, query?: Record<string, string | undefined>): string {
  const url = new URL(`${API_BASE}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value) url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

async function aiFetch<T>(path: string, options: FetchOpts): Promise<T> {
  const response = await fetch(buildUrl(path, options.query), {
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export function fetchOrgAiDashboard(options: FetchOpts) {
  return aiFetch<Record<string, unknown>>("/api/v1/ai/dashboard", options);
}

export function fetchPlatformAiDashboard(options: Omit<FetchOpts, "organisationId"> & { organisationId?: string }) {
  const responseOpts = {
    accessToken: options.accessToken,
    organisationId: options.organisationId ?? "",
    role: options.role,
    query: options.query,
  };
  return aiFetch<Record<string, unknown>>("/api/v1/ai/platform/dashboard", responseOpts);
}

export function fetchBudgetStatus(options: FetchOpts) {
  return aiFetch<Record<string, unknown>>("/api/v1/ai/usage/status", options);
}
