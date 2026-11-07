export const AI_LIMITATION_NOTICE =
  "AI assistance only — this sweep does not provide legal certification or an autonomous compliance decision. Final decisions remain with authorised human staff.";

export function canRunComplianceSweep(permissions: string[] | undefined): boolean {
  return Boolean(
    permissions?.includes("ai.compliance.run") || permissions?.includes("compliance.check"),
  );
}

export function canReviewComplianceFindings(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.compliance.review"));
}

export function resultLabel(result: string): string {
  switch (result) {
    case "potential_gap":
      return "Potential gap";
    case "needs_review":
      return "Needs review";
    case "unable_to_verify":
      return "Unable to verify";
    default:
      return result;
  }
}

export function reviewLabel(status: string): string {
  switch (status) {
    case "pending":
      return "Pending human review";
    case "confirmed":
      return "Human confirmed";
    case "dismissed":
      return "Dismissed";
    case "investigate":
      return "Further investigation";
    default:
      return status;
  }
}

export function analysisLayoutClass(): string {
  return "space-y-4 rounded-lg border border-amber-200 bg-amber-50/40 p-4";
}
