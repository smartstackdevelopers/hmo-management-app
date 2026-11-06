import { expect, test } from "@playwright/test";
import { isEmergencyRequest, maintenancePriorityBadgeClass } from "../src/lib/maintenanceApi";

test.describe("maintenance helpers (unit via Playwright runner)", () => {
  test("priority badge distinguishes emergency", () => {
    expect(maintenancePriorityBadgeClass("emergency")).toContain("red");
    expect(maintenancePriorityBadgeClass("normal")).toContain("sky");
  });

  test("emergency helper uses backend flags", () => {
    expect(isEmergencyRequest({ is_emergency_priority: true, priority: "normal" })).toBe(true);
    expect(isEmergencyRequest({ is_emergency_priority: false, priority: "urgent" })).toBe(false);
  });
});
