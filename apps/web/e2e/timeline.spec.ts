import { expect, test } from "@playwright/test";
import { activityBadgeClass } from "../src/lib/timelineUi";

test.describe("F2.9 tenant timeline UI helpers", () => {
  test("maps activity types to badge classes", () => {
    expect(activityBadgeClass("meeting")).toContain("indigo");
    expect(activityBadgeClass("appointment")).toContain("violet");
    expect(activityBadgeClass("tenant_follow_up")).toContain("orange");
    expect(activityBadgeClass("unknown_type")).toContain("slate");
  });
});
