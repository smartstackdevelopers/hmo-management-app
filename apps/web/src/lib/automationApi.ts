import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AutomationAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function autoFetch<T>(path: string, options: AutomationAuth, init?: RequestInit): Promise<T> {
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

export function fetchAutomationDashboard(options: AutomationAuth) {
  return autoFetch<Record<string, unknown>>("/api/v1/automation/dashboard", options);
}

export function fetchAutomationRules(
  options: AutomationAuth & { category?: string; is_enabled?: string; search?: string },
) {
  const params = new URLSearchParams();
  if (options.category) params.set("category", options.category);
  if (options.is_enabled) params.set("is_enabled", options.is_enabled);
  if (options.search) params.set("search", options.search);
  const q = params.toString();
  return autoFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/automation/rules${q ? `?${q}` : ""}`,
    options,
  );
}

export function createAutomationRule(options: AutomationAuth, body: Record<string, unknown>) {
  return autoFetch<Record<string, unknown>>("/api/v1/automation/rules", options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateAutomationRule(
  options: AutomationAuth,
  ruleId: string,
  body: Record<string, unknown>,
) {
  return autoFetch<Record<string, unknown>>(`/api/v1/automation/rules/${ruleId}`, options, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteAutomationRule(options: AutomationAuth, ruleId: string) {
  return autoFetch<Record<string, unknown>>(`/api/v1/automation/rules/${ruleId}`, options, {
    method: "DELETE",
  });
}

export function runAutomationRule(options: AutomationAuth, ruleId: string) {
  return autoFetch<Record<string, unknown>>(`/api/v1/automation/rules/${ruleId}/run`, options, {
    method: "POST",
  });
}

export function fetchAutomationRuns(options: AutomationAuth & { status?: string; rule_id?: string }) {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  if (options.rule_id) params.set("rule_id", options.rule_id);
  const q = params.toString();
  return autoFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/automation/runs${q ? `?${q}` : ""}`,
    options,
  );
}

export function retryAutomationRun(options: AutomationAuth, runId: string) {
  return autoFetch<Record<string, unknown>>(`/api/v1/automation/runs/${runId}/retry`, options, {
    method: "POST",
  });
}

export function fetchAutomationEscalations(options: AutomationAuth & { status?: string }) {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  const q = params.toString();
  return autoFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/automation/escalations${q ? `?${q}` : ""}`,
    options,
  );
}

export function updateAutomationEscalation(
  options: AutomationAuth,
  escalationId: string,
  status: string,
  resolution_note?: string,
) {
  return autoFetch<Record<string, unknown>>(`/api/v1/automation/escalations/${escalationId}`, options, {
    method: "PATCH",
    body: JSON.stringify({ status, resolution_note }),
  });
}

export function fetchAutomationComplianceIssues(options: AutomationAuth & { status?: string }) {
  const params = new URLSearchParams();
  if (options.status) params.set("status", options.status);
  const q = params.toString();
  return autoFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/automation/compliance-issues${q ? `?${q}` : ""}`,
    options,
  );
}
