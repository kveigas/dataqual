import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "playwright/test";

test("empty evidence workspace is truthful, responsive, and accessible", async ({ page }) => {
  await page.route("**/api/v1/datasets", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Evidence before quality claims." }),
  ).toBeVisible();
  await expect(page.getByText(/No canonical datasets yet/i)).toBeVisible();
  await expect(page.getByText(/remain conditional on evidence/i)).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("mobile viewport has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/datasets", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.goto("/");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
});
