/**
 * F1.6 core-records API helpers. Backend enforces RBAC + organisation isolation.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type PageResult<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export async function fetchRecordsPage<T>(
  path: string,
  options: {
    accessToken: string;
    organisationId: string;
    role?: string;
    query?: Record<string, string | undefined>;
  },
): Promise<PageResult<T>> {
  const url = new URL(`${API_BASE}${path}`);
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value) {
        url.searchParams.set(key, value);
      }
    }
  }
  const response = await fetch(url, {
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
    throw new Error(`API ${response.status}`);
  }
  return response.json() as Promise<PageResult<T>>;
}
