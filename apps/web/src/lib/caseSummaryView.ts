export const CASE_SUMMARY_SECTIONS = [
  ["overview", "Case overview"],
  ["background", "Background and current situation"],
  ["events", "Important events and case history"],
  ["recent_support", "Recent support activities and notes"],
  ["needs_and_goals", "Recorded needs and goals"],
  ["outstanding_actions", "Outstanding actions and follow-ups"],
  ["upcoming", "Upcoming appointments or reviews"],
] as const;

export type GenState = "idle" | "loading" | "error" | "ready";

export function nextGenState(event: "start" | "success" | "failure" | "reset"): GenState {
  if (event === "start") return "loading";
  if (event === "success") return "ready";
  if (event === "failure") return "error";
  return "idle";
}

export function canGenerateSummary(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.case_summary.run"));
}

export function canReviewSummary(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.case_summary.review"));
}

export function summaryLayoutClass(): string {
  return "mx-auto w-full max-w-4xl space-y-6 px-4 sm:px-0";
}

export function sectionEntries(sections: Record<string, unknown> | undefined): Array<{ key: string; label: string; body: string }> {
  const source = sections ?? {};
  return CASE_SUMMARY_SECTIONS.map(([key, label]) => ({
    key,
    label,
    body: String(source[key] ?? ""),
  })).filter((item) => item.body.trim().length > 0);
}

export function isSummaryStale(summary: { stale?: unknown }): boolean {
  return Boolean(summary.stale);
}
