import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type FinanceAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function finFetch<T>(path: string, options: FinanceAuth, init?: RequestInit): Promise<T> {
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
  if (response.status === 204) return undefined as T;
  const ct = response.headers.get("content-type") || "";
  if (ct.includes("application/json")) return response.json() as Promise<T>;
  return response.blob() as Promise<T>;
}

export function fetchFinanceDashboard(options: FinanceAuth) {
  return finFetch<Record<string, unknown>>("/api/v1/finance/dashboard", options);
}

export function fetchFinanceRecords(options: FinanceAuth) {
  return finFetch<{ items: Record<string, unknown>[] }>("/api/v1/finance/records", options);
}

export function createFinanceRecord(options: FinanceAuth, body: Record<string, unknown>) {
  return finFetch<Record<string, unknown>>("/api/v1/finance/records", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchFinanceBudgets(options: FinanceAuth) {
  return finFetch<{ items: Record<string, unknown>[] }>("/api/v1/finance/budgets", options);
}

export function createFinanceBudget(options: FinanceAuth, body: Record<string, unknown>) {
  return finFetch<Record<string, unknown>>("/api/v1/finance/budgets", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function downloadFinanceExport(options: FinanceAuth, format: "csv" | "pdf" | "xlsx") {
  const blob = (await finFetch<Blob>(`/api/v1/finance/exports/records?export_format=${format}`, options)) as Blob;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `finance-records.${format === "xlsx" ? "xlsx" : format}`;
  a.click();
  URL.revokeObjectURL(url);
}
