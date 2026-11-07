export function canRunHousingApplicationAnalysis(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.housing_application.run"));
}

export function canReviewHousingApplicationAnalysis(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.housing_application.review"));
}

export function analysisLayoutClass(): string {
  return "space-y-4 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:px-5";
}

export function findingLabel(source: string | undefined): string {
  if (source === "rule") return "Rule-based";
  if (source === "evidence") return "Evidence checklist";
  if (source === "document") return "Document metadata";
  if (source === "ai") return "AI-generated";
  return "Recorded check";
}

export function outcomeLabel(outcome: string | undefined): string {
  if (outcome === "complete") return "Complete";
  if (outcome === "missing") return "Missing";
  if (outcome === "incomplete") return "Incomplete";
  if (outcome === "needs_review") return "Needs Review";
  if (outcome === "not_applicable") return "Not Applicable";
  if (outcome === "not_performed") return "Could not verify";
  return outcome || "Unknown";
}

export function visibleFindings(
  findings: Array<{ title?: string; code?: string; outcome?: string }>
): Array<{ title?: string; code?: string; outcome?: string }> {
  return findings.filter((item) => item.title || item.code);
}

export const AI_LIMITATION_NOTICE =
  "AI assistance only — this analysis does not determine housing eligibility, allocation, approval, or rejection. Final decisions remain with authorised human staff.";
