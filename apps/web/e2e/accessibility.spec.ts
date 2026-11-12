import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { verifyBrandContrastSamples } from "../src/lib/a11y/contrast";

const PUBLIC_PATHS = ["/", "/health", "/unauthorized"] as const;

test.describe("brand contrast (computed)", () => {
  test("HMore token pairs meet WCAG AA targets", () => {
    const results = verifyBrandContrastSamples();
    for (const row of results) {
      expect(row.pass, `${row.id} ratio ${row.ratio}`).toBeTruthy();
    }
  });
});

test.describe("automated axe scans (public routes)", () => {
  for (const path of PUBLIC_PATHS) {
    test(`no serious axe violations on ${path}`, async ({ page }) => {
      await page.goto(path);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
        .disableRules(["color-contrast"])
        .analyze();
      const serious = results.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
      expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
    });
  }
});

test.describe("keyboard and zoom (public home)", () => {
  test("skip link targets main content", async ({ page }) => {
    await page.goto("/");
    const skip = page.getByRole("link", { name: /skip to main content/i });
    await skip.focus();
    await expect(skip).toBeFocused();
    await skip.click();
    await expect(page.locator("#main-content")).toBeFocused();
  });

  test("primary actions are reachable by Tab", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
    expect(focused.length).toBeGreaterThan(0);
  });

  test("layout reflows at 200% zoom without horizontal scroll", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2);
  });
});
