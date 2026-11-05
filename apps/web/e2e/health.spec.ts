import { expect, test } from "@playwright/test";

test("home page renders the web shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /one shared platform/i })).toBeVisible();
});

test("health page reports web process status", async ({ page }) => {
  await page.goto("/health");
  await expect(page.getByRole("heading", { name: /service status/i })).toBeVisible();
  await expect(page.getByText("hmore-web")).toBeVisible();
  await expect(page.getByText("ok", { exact: true })).toBeVisible();
});
