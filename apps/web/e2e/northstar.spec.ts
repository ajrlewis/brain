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

  await page.getByRole("link", { name: "Search" }).click();
  await page.getByLabel("Search knowledge").fill("Orion revenue");
  await page.getByRole("button", { name: "Search" }).click();
  const project = page.getByRole("link", { name: "Project Orion" }).first();
  await expect(project).toBeVisible();
  await expect(page.getByText("Revenue is £45m", { exact: false })).toBeVisible();
  await project.click();
  await expect(
    page.locator(".title-row").getByRole("heading", { name: "Project Orion" }),
  ).toBeVisible();
});
