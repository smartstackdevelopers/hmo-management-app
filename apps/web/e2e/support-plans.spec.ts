import { expect, test } from "@playwright/test";
import { DASHBOARD_NAV, filterNavItems } from "../src/lib/navigation";

test.describe("support plans nav (F2.10)", () => {
  test("shows Support plans for staff with support_plans.read", () => {
    const nav = filterNavItems(DASHBOARD_NAV, {
      authenticated: true,
      role: "organisation_admin",
      permissions: ["support_plans.read", "tenants.read"],
    });
    expect(nav.map((i) => i.id)).toContain("support-plans-dashboard");
  });

  test("hides Support plans without permission", () => {
    const nav = filterNavItems(DASHBOARD_NAV, {
      authenticated: true,
      role: "landlord",
      permissions: ["properties.read", "timeline.read.landlord"],
    });
    expect(nav.map((i) => i.id)).not.toContain("support-plans-dashboard");
  });
});
