export const REPORT_DRAFT_NOTICE =
  "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW. Metrics come from authorised reporting summaries. Approval does not distribute the report.";

export function canGenerateReportDrafts(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("report_drafts.generate"));
}

export function canReadReportDrafts(permissions: string[] | undefined): boolean {
  return Boolean(
    permissions?.includes("report_drafts.read") ||
      permissions?.includes("report_drafts.generate") ||
      permissions?.includes("report_drafts.review"),
  );
}

export function canReviewReportDrafts(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("report_drafts.review"));
}
