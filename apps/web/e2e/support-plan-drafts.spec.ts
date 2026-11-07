import { expect, test } from "@playwright/test";
import {
  canApplySupportPlanDraft,
  canReviewSupportPlanDraft,
  canRunSupportPlanDraft,
  draftLayoutClass,
  originLabel,
  visibleGaps,
} from "../src/lib/supportPlanDraftView";

test.describe("support plan draft view helpers", () => {
  test("labels AI and human-edited drafts separately from an approved plan", () => {
    expect(originLabel("ai")).toContain("not an approved support plan");
    expect(originLabel("human_edited")).toContain("Human-edited");
    expect(originLabel("human_edited")).toContain("not an approved support plan");
  });

  test("permissions hide review and apply controls", () => {
    expect(canRunSupportPlanDraft(["ai.support_plan_draft.run"])).toBe(true);
    expect(canRunSupportPlanDraft(["support_plans.read"])).toBe(false);
    expect(canReviewSupportPlanDraft(["ai.support_plan_draft.review"])).toBe(true);
    expect(canReviewSupportPlanDraft(["ai.support_plan_draft.run"])).toBe(false);
    expect(canApplySupportPlanDraft(["support_plans.manage"], "approved")).toBe(true);
    expect(canApplySupportPlanDraft(["support_plans.manage"], "draft")).toBe(false);
    expect(canApplySupportPlanDraft(["ai.support_plan_draft.review"], "approved")).toBe(false);
  });

  test("shows gaps and a responsive draft layout", () => {
    expect(visibleGaps(["No needs text is stored.", "  "])).toEqual(["No needs text is stored."]);
    expect(draftLayoutClass()).toContain("sm:px-5");
  });
});
