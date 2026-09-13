import { expect, test } from "@playwright/test";
test("signs in and browses Northstar inventory and detail", async ({
  page,
}) => {
  await page.goto("/sign-in");
  await page.getByLabel("Username").fill("brain-admin");
  await page.getByLabel("Password").fill("brain-local-dev");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible();
  const first = page.locator("tbody a").first();
  await expect(first).toBeVisible();
  const title = await first.textContent();
  await first.click();
  await expect(
    page.locator(".title-row").getByRole("heading", { name: title ?? "" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Provenance" })).toBeVisible();
});
