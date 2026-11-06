import { expect, test } from "@playwright/test";
import {
  evidenceStatusLabel,
  isBlockingEvidenceStatus,
  packReadinessWarning,
  type Readiness,
} from "../src/lib/evidenceApi";

test.describe("evidence helpers (unit via Playwright runner)", () => {
  test("labels evidence statuses", () => {
    expect(evidenceStatusLabel("under_review")).toBe("under review");
    expect(evidenceStatusLabel("not_applicable")).toBe("not applicable");
  });

  test("flags blocking required statuses", () => {
    expect(isBlockingEvidenceStatus("pending", true)).toBe(true);
    expect(isBlockingEvidenceStatus("rejected", true)).toBe(true);
    expect(isBlockingEvidenceStatus("accepted", true)).toBe(false);
    expect(isBlockingEvidenceStatus("not_applicable", true)).toBe(false);
    expect(isBlockingEvidenceStatus("pending", false)).toBe(false);
  });

  test("readiness warning for incomplete packs", () => {
    const incomplete: Readiness = {
      application_id: "a",
      ready: false,
      is_complete: false,
      required_total: 2,
      required_accepted: 1,
      outstanding: [{ id: "1", title: "Proof of identity", status: "missing" }],
    };
    expect(packReadinessWarning(incomplete)).toMatch(/Proof of identity/);
    expect(
      packReadinessWarning({
        ...incomplete,
        is_complete: true,
        ready: true,
        outstanding: [],
      }),
    ).toBeNull();
  });
});
