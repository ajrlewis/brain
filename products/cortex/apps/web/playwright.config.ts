import { defineConfig } from "@playwright/test";
export default defineConfig({ testDir: "./e2e", use: { baseURL: process.env.CORTEX_WEB_TEST_URL ?? "http://127.0.0.1:3100" }, timeout: 30_000 });
