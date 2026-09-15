import { expect, test } from "@playwright/test";
test("sign in, create, continue, and reopen durable history", async ({ page }) => {
  const message = `Synthetic browser turn ${Date.now()}`;
  await page.goto("/");
  await page.getByLabel("Username").fill(process.env.CORTEX_WEB_TEST_USER ?? "cortex-user");
  await page.getByLabel("Password").fill(process.env.CORTEX_WEB_TEST_PASSWORD ?? "cortex-local-dev");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("button", { name: "New conversation" }).click();
  await page.getByLabel("Message Cortex").fill(message);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(message, { exact: true })).toBeVisible();
  await expect(page.getByText(`Synthetic response to: ${message}`, { exact: true })).toBeVisible();
  const conversationUrl = page.url();
  await page.goto("/conversations");
  await page.getByRole("link", { name: /^Conversation / }).first().click();
  await expect(page).toHaveURL(conversationUrl);
  await expect(page.getByText(message, { exact: true })).toBeVisible();
});
