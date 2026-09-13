import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { env } from "./env";
export const sessionCookie = "brain-session";
function signature(user: string) {
  return createHmac("sha256", env().LOCAL_WEB_SESSION_SECRET)
    .update(user)
    .digest("base64url");
}
export function createSession(user: string) {
  return `${encodeURIComponent(user)}.${signature(user)}`;
}
export function readSession(value?: string) {
  if (!value) return null;
  const split = value.lastIndexOf(".");
  if (split < 1) return null;
  const user = decodeURIComponent(value.slice(0, split));
  const actual = Buffer.from(value.slice(split + 1));
  const expected = Buffer.from(signature(user));
  return actual.length === expected.length && timingSafeEqual(actual, expected)
    ? user
    : null;
}
export function validCredentials(user: string, password: string) {
  const config = env();
  const actual = Buffer.from(`${user}\0${password}`);
  const expected = Buffer.from(
    `${config.LOCAL_WEB_USER}\0${config.LOCAL_WEB_PASSWORD}`,
  );
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}
