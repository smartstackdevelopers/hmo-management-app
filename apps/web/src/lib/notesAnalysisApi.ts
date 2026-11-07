import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Opts = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function naFetch<T>(path: string, options: Opts & { method?: string; body?: unknown }): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export function fetchNotesAnalysisInbox(options: Opts) {
  return naFetch<{ items: Array<Record<string, unknown>> }>("/api/v1/notes-analysis/inbox", options);
}

export function fetchNotesAnalysis(analysisId: string, options: Opts) {
  return naFetch<Record<string, unknown>>(`/api/v1/notes-analysis/analyses/${analysisId}`, options);
}

export function runNotesAnalysis(dailyLogId: string, options: Opts & { force?: boolean }) {
  return naFetch<Record<string, unknown>>("/api/v1/notes-analysis/analyse", {
    ...options,
    method: "POST",
    body: { daily_log_id: dailyLogId, force: options.force ?? false },
  });
}

export function decideSuggestion(
  suggestionId: string,
  decision: "approve" | "reject" | "dismiss",
  options: Opts & { reviewerNote?: string; editedBody?: string },
) {
  return naFetch<Record<string, unknown>>(`/api/v1/notes-analysis/suggestions/${suggestionId}/decide`, {
    ...options,
    method: "POST",
    body: {
      decision,
      reviewer_note: options.reviewerNote,
      edited_body: options.editedBody,
    },
  });
}

export function reviewAnalysis(
  analysisId: string,
  decision: "approve" | "partially_approve" | "reject",
  options: Opts & { reviewComment?: string },
) {
  return naFetch<Record<string, unknown>>(`/api/v1/notes-analysis/analyses/${analysisId}/review`, {
    ...options,
    method: "POST",
    body: { decision, review_comment: options.reviewComment },
  });
}
