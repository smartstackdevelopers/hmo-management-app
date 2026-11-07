import { expect, test } from "@playwright/test";
import {
  DUPLICATE_DETECTION_NOTICE,
  canReadDuplicateDetection,
  canReviewDuplicateFindings,
  canRunDuplicateDetection,
  matchStrengthLabel,
  reviewStatusLabel,
} from "../src/lib/duplicateDetectionView";

test.describe("duplicate detection helpers", () => {
  test("shows human-review notice and strength labels", () => {
    expect(DUPLICATE_DETECTION_NOTICE).toContain("Potential Duplicates — Human Review Required");
    expect(DUPLICATE_DETECTION_NOTICE).toContain("never deletes or merges");
    expect(matchStrengthLabel("possible")).toContain("review carefully");
    expect(reviewStatusLabel("confirmed_duplicate")).toContain("unchanged");
  });

  test("permissions gate run and review", () => {
    expect(canRunDuplicateDetection([])).toBe(false);
    expect(canRunDuplicateDetection(["duplicate_detection.run"])).toBe(true);
    expect(canReadDuplicateDetection(["duplicate_detection.read"])).toBe(true);
    expect(canReviewDuplicateFindings(["duplicate_detection.run"])).toBe(false);
    expect(canReviewDuplicateFindings(["duplicate_detection.review"])).toBe(true);
  });
});
