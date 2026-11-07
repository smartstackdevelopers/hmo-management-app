import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function reportFetch<T>(
  path: string,
  options: { accessToken: string; organisationId: string; role?: string | null },
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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

export function fetchReportingDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  return reportFetch<Record<string, unknown>>("/api/v1/reports/dashboard", options);
}

export function exportReportUrl(
  reportType: "housing" | "complaints" | "caseload",
  format: "csv" | "pdf" | "xlsx",
) {
  return `${API_BASE}/api/v1/reports/export/${reportType}/${format}`;
}
