import "server-only";
import { z } from "zod";
const environment = z.object({
  BRAIN_API_URL: z.string().url().default("http://127.0.0.1:8000"),
  LOCAL_BEARER_TOKEN: z.string().min(1),
  LOCAL_WEB_USER: z.string().min(1).default("brain-admin"),
  LOCAL_WEB_PASSWORD: z.string().min(8).default("brain-local-dev"),
  LOCAL_WEB_SESSION_SECRET: z
    .string()
    .min(16)
    .default("brain-local-session-secret"),
});
export function env() {
  return environment.parse(process.env);
}
