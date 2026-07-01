import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("home renders one h1 and article links", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.getByRole("link").first()).toBeVisible();
});

test("no accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

for (const width of [320, 768, 1024, 1440]) {
  test(`screenshot @ ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page).toHaveScreenshot(`home-${width}.png`, { fullPage: true });
  });
}
