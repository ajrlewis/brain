import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { env } from "./env";

export const sessionCookie = "cortex-session";

function signature(value: string) {
  return createHmac("sha256", env().CORTEX_WEB_SESSION_SECRET)
    .update(value)
    .digest("base64url");
}

export function createSession() {
  const marker = "authenticated";
  return `${marker}.${signature(marker)}`;
}

export function readSession(value?: string) {
  if (!value) return null;
  const split = value.lastIndexOf(".");
  if (split < 1) return null;
  const marker = value.slice(0, split);
  if (marker !== "authenticated") return null;
  const actual = Buffer.from(value.slice(split + 1));
  const expected = Buffer.from(signature(marker));
  return actual.length === expected.length && timingSafeEqual(actual, expected)
    ? true
    : null;
}

export function validCredentials(user: string, password: string) {
  const config = env();
  const actual = Buffer.from(`${user}\0${password}`);
  const expected = Buffer.from(
    `${config.CORTEX_WEB_USER}\0${config.CORTEX_WEB_PASSWORD}`,
  );
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}
