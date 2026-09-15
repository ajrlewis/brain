import "server-only";
import { z } from "zod";

const environment = z.object({
  CORTEX_API_URL: z.string().url().default("http://127.0.0.1:8100"),
  CORTEX_API_BEARER_TOKEN: z.string().trim().min(1),
  CORTEX_WEB_USER: z.string().trim().min(1).default("cortex-user"),
  CORTEX_WEB_PASSWORD: z.string().min(8).default("cortex-local-dev"),
  CORTEX_WEB_SESSION_SECRET: z
    .string()
    .min(16)
    .default("cortex-local-session-secret"),
});

export function env() {
  return environment.parse(process.env);
}
