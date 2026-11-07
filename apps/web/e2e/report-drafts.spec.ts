import { expect, test } from "@playwright/test";
import {
  REPORT_DRAFT_NOTICE,
  canGenerateReportDrafts,
  canReviewReportDrafts,
} from "../src/lib/reportDraftsView";

test.describe("report drafts helpers", () => {
  test("requires human review and permissions", () => {
    expect(REPORT_DRAFT_NOTICE).toContain("REQUIRES HUMAN REVIEW");
    expect(REPORT_DRAFT_NOTICE).toContain("does not distribute");
    expect(canGenerateReportDrafts([])).toBe(false);
    expect(canGenerateReportDrafts(["report_drafts.generate"])).toBe(true);
    expect(canReviewReportDrafts(["report_drafts.generate"])).toBe(false);
    expect(canReviewReportDrafts(["report_drafts.review"])).toBe(true);
  });
});
