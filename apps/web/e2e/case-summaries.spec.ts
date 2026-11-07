import { expect, test } from "@playwright/test";
import { DASHBOARD_NAV, filterNavItems } from "../src/lib/navigation";
import {
  canGenerateSummary,
  canReviewSummary,
  isSummaryStale,
  nextGenState,
  sectionEntries,
  summaryLayoutClass,
} from "../src/lib/caseSummaryView";

test.describe("case summary view helpers", () => {
  test("generation states and review permissions", () => {
    expect(nextGenState("start")).toBe("loading");
    expect(nextGenState("failure")).toBe("error");
    expect(nextGenState("success")).toBe("ready");
    expect(canGenerateSummary(["ai.case_summary.run"])).toBe(true);
    expect(canGenerateSummary(["ai.case_summary.read"])).toBe(false);
    expect(canReviewSummary(["ai.case_summary.review"])).toBe(true);
    expect(canReviewSummary(["ai.case_summary.run"])).toBe(false);
  });

  test("renders only populated sections and stale flag", () => {
    const entries = sectionEntries({
      overview: "AI-generated overview",
      background: "",
      events: "Unavailable — no authorised records of this type were found for this case.",
    });
    expect(entries.map((item) => item.key)).toEqual(["overview", "events"]);
    expect(isSummaryStale({ stale: true })).toBe(true);
    expect(isSummaryStale({})).toBe(false);
  });

  test("layout class is responsive", () => {
    const layout = summaryLayoutClass();
    expect(layout).toContain("max-w-4xl");
    expect(layout).toContain("sm:px-0");
    expect(layout).toContain("px-4");
  });

  test("navigation shows case summaries only with permission", () => {
    const hidden = filterNavItems(DASHBOARD_NAV, {
      authenticated: true,
      role: "support_worker",
      permissions: ["support_notes.read.assigned"],
    });
    expect(hidden.map((item) => item.id)).not.toContain("case-summaries");
    const shown = filterNavItems(DASHBOARD_NAV, {
      authenticated: true,
      role: "organisation_admin",
      permissions: ["ai.case_summary.review"],
    });
    expect(shown.map((item) => item.id)).toContain("case-summaries");
  });
});

test("case summaries route does not server-error when signed out", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const response = await page.goto("/dashboard/case-summaries");
  expect(response?.status() ?? 200).toBeLessThan(500);
  await expect(page.getByRole("heading").first()).toBeVisible();
});
