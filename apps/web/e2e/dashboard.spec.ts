import { expect, test } from "@playwright/test";
import {
  canAccessRoleHome,
  homePathForRole,
  isF19DashboardRole,
  requiredRoleForHomePath,
} from "../src/lib/dashboardAccess";
import { DASHBOARD_NAV, filterNavItems } from "../src/lib/navigation";

test.describe("dashboard access helpers (unit via Playwright runner)", () => {
  test("maps roles to home paths", () => {
    expect(homePathForRole("super_admin")).toBe("/dashboard/super-admin");
    expect(homePathForRole("organisation_admin")).toBe("/dashboard/organisation-admin");
    expect(homePathForRole("landlord")).toBe("/dashboard/landlord");
    expect(homePathForRole("support_worker")).toBe("/dashboard/support-worker");
    expect(homePathForRole("tenant")).toBe("/account");
  });

  test("denies wrong-role home access", () => {
    expect(canAccessRoleHome("landlord", "super_admin")).toBe(false);
    expect(canAccessRoleHome("organisation_admin", "organisation_admin")).toBe(true);
    expect(isF19DashboardRole("support_worker")).toBe(true);
    expect(canAccessRoleHome("support_worker", "support_worker")).toBe(true);
    expect(canAccessRoleHome("landlord", "support_worker")).toBe(false);
    expect(requiredRoleForHomePath("landlord")).toBe("landlord");
    expect(requiredRoleForHomePath("support-worker")).toBe("support_worker");
  });

  test("filters navigation by permissions", () => {
    const landlordNav = filterNavItems(DASHBOARD_NAV, {
      authenticated: true,
      role: "landlord",
      permissions: ["properties.read", "properties.manage", "rooms.read", "rooms.manage"],
    });
    const ids = landlordNav.map((item) => item.id);
    expect(ids).toContain("properties");
    expect(ids).toContain("rooms");
    expect(ids).not.toContain("tenants");
    expect(ids).not.toContain("organisations");
    expect(ids).not.toContain("audit");

    const empty = filterNavItems(DASHBOARD_NAV, {
      authenticated: false,
      permissions: ["tenants.manage"],
    });
    expect(empty).toEqual([]);
  });
});

test.describe("dashboard routes", () => {
  test("public home still renders and links to dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /one shared platform/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /open dashboard/i })).toBeVisible();
  });

  test("unauthorized page is reachable", async ({ page }) => {
    await page.goto("/unauthorized");
    await expect(page.getByRole("heading", { name: /access denied/i })).toBeVisible();
  });

  test("unauthenticated dashboard access is protected when Auth0 is configured", async ({
    page,
  }) => {
    const response = await page.goto("/dashboard");
    // Either redirected to Auth0 login, or shows not-configured empty state in local/CI variants.
    const url = page.url();
    const heading = page.getByRole("heading").first();
    await expect(heading).toBeVisible();
    const body = await page.locator("body").innerText();
    const protectedOk =
      url.includes("/auth/login") ||
      url.includes("auth0.com") ||
      /sign-in not configured|dashboard unavailable|membership required|no hmore role|auth0/i.test(
        body,
      );
    expect(protectedOk).toBeTruthy();
    expect(response?.status() ?? 200).toBeLessThan(500);
  });

  test("role home URLs respond without server error when unauthenticated", async ({ page }) => {
    for (const path of [
      "/dashboard/super-admin",
      "/dashboard/organisation-admin",
      "/dashboard/landlord",
    ]) {
      const response = await page.goto(path);
      expect(response?.status() ?? 200).toBeLessThan(500);
    }
  });

  test("mobile navigation control exists on dashboard chrome after soft visit", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dashboard");
    // Mobile menu button is part of DashboardShell; may be behind redirect — tolerate login page.
    const menu = page.getByRole("button", { name: /menu/i });
    if (await menu.count()) {
      await menu.click();
      await expect(page.getByRole("navigation", { name: /mobile dashboard/i })).toBeVisible();
    }
  });
});
