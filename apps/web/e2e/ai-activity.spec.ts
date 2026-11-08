import { expect, test } from "@playwright/test";
import {
  CONFIDENCE_UNAVAILABLE,
  FEEDBACK_CATEGORIES,
  canReadAiActivity,
  canReviewAiFeedback,
  canSubmitAiFeedback,
  formatConfidence,
} from "../src/lib/aiActivityView";

test.describe("AI activity helpers", () => {
  test("permissions and confidence unavailable", () => {
    expect(canReadAiActivity([])).toBe(false);
    expect(canReadAiActivity(["ai.activity.read"])).toBe(true);
    expect(canSubmitAiFeedback(["ai.activity.feedback.submit"])).toBe(true);
    expect(canReviewAiFeedback(["ai.activity.read"])).toBe(false);
    expect(canReviewAiFeedback(["ai.activity.feedback.review"])).toBe(true);
    expect(FEEDBACK_CATEGORIES.length).toBeGreaterThanOrEqual(7);
    expect(formatConfidence(null)).toBe(CONFIDENCE_UNAVAILABLE);
    expect(formatConfidence({ kind: "unavailable", label: CONFIDENCE_UNAVAILABLE })).toBe(
      CONFIDENCE_UNAVAILABLE,
    );
    expect(
      formatConfidence({
        kind: "retrieval_coverage",
        label: "Based on retrieved sources (not a calibrated accuracy score)",
        percentage: null,
      }),
    ).toContain("retrieved sources");
  });
});
