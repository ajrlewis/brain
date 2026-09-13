import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:3000" },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000/pages",
    reuseExistingServer: true,
    env: {
      BRAIN_API_URL: "http://127.0.0.1:8000",
      LOCAL_BEARER_TOKEN: "brain-local-dev",
    },
  },
});
