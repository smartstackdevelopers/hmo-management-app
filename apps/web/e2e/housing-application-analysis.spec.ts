import { expect, test } from "@playwright/test";
import {
  AI_LIMITATION_NOTICE,
  analysisLayoutClass,
  canReviewHousingApplicationAnalysis,
  canRunHousingApplicationAnalysis,
  findingLabel,
  outcomeLabel,
  visibleFindings,
} from "../src/lib/housingApplicationAnalysisView";

test.describe("housing application analysis helpers", () => {
  test("shows the AI limitation notice and labels sources", () => {
    expect(AI_LIMITATION_NOTICE).toContain("does not determine housing eligibility");
    expect(findingLabel("rule")).toBe("Rule-based");
    expect(findingLabel("evidence")).toBe("Evidence checklist");
    expect(outcomeLabel("needs_review")).toBe("Needs Review");
  });

  test("permissions hide run and review controls", () => {
    expect(canRunHousingApplicationAnalysis(["ai.housing_application.run"])).toBe(true);
    expect(canRunHousingApplicationAnalysis(["applications.review"])).toBe(false);
    expect(canReviewHousingApplicationAnalysis(["ai.housing_application.review"])).toBe(true);
    expect(canReviewHousingApplicationAnalysis(["ai.housing_application.run"])).toBe(false);
  });

  test("filters empty findings and uses responsive layout", () => {
    expect(visibleFindings([{ title: "Proof of identity", outcome: "missing" }, { title: "" }])).toHaveLength(1);
    expect(analysisLayoutClass()).toContain("sm:px-5");
  });
});
