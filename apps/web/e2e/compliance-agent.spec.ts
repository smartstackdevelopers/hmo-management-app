import { expect, test } from "@playwright/test";
import {
  AI_LIMITATION_NOTICE,
  canReviewComplianceFindings,
  canRunComplianceSweep,
  resultLabel,
} from "../src/lib/complianceAgentView";

test.describe("compliance agent helpers", () => {
  test("shows the AI limitation notice and labels results", () => {
    expect(AI_LIMITATION_NOTICE).toContain("does not provide legal certification");
    expect(resultLabel("potential_gap")).toBe("Potential gap");
    expect(resultLabel("unable_to_verify")).toBe("Unable to verify");
  });

  test("permissions hide run and review controls", () => {
    expect(canRunComplianceSweep([])).toBe(false);
    expect(canRunComplianceSweep(["ai.compliance.run"])).toBe(true);
    expect(canRunComplianceSweep(["compliance.check"])).toBe(true);
    expect(canReviewComplianceFindings(["ai.compliance.run"])).toBe(false);
    expect(canReviewComplianceFindings(["ai.compliance.review"])).toBe(true);
  });
});
