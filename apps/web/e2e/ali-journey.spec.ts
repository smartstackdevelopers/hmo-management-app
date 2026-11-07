import { expect, test } from "@playwright/test";

/**
 * F2.15 Ali journey — UI route smoke (no Auth0; paths must exist).
 * Full journey is verified via apps/api/tests/test_f215_ali_end_to_end.py (PostgreSQL).
 */

const ALI_ROUTE_HINTS = [
  "/dashboard/case-assignments",
  "/dashboard/maintenance",
  "/dashboard/org-workflows/approvals",
  "/dashboard/reports",
];

for (const path of ALI_ROUTE_HINTS) {
  test(`Ali journey route resolves: ${path}`, async ({ page }) => {
    const res = await page.goto(path, { waitUntil: "domcontentloaded" });
    expect(res?.status()).toBeLessThan(500);
  });
}
