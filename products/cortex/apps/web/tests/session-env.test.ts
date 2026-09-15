// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
import { env } from "@/lib/env";
import { createSession, readSession, sessionCookie, validCredentials } from "@/lib/session";
const original = process.env;
describe("Cortex web configuration and session", () => {
  afterEach(() => { process.env = original; vi.unstubAllEnvs(); });
  it("requires a valid Cortex API URL and bearer", () => { process.env = { ...original, CORTEX_API_URL: "not-a-url", CORTEX_API_BEARER_TOKEN: "" }; expect(() => env()).toThrow(); });
  it("uses only Cortex-prefixed credentials and a signed opaque cookie", () => {
    process.env = { ...original, CORTEX_API_BEARER_TOKEN: "cortex-secret", CORTEX_WEB_USER: "cortex-user", CORTEX_WEB_PASSWORD: "cortex-password", CORTEX_WEB_SESSION_SECRET: "cortex-session-secret" };
    expect(validCredentials("cortex-user", "cortex-password")).toBe(true);
    expect(validCredentials("brain-admin", "brain-local-dev")).toBe(false);
    const value = createSession();
    expect(sessionCookie).toBe("cortex-session"); expect(value).not.toContain("cortex-user"); expect(value).not.toContain("cortex-secret"); expect(readSession(value)).toBe(true); expect(readSession(`${value}x`)).toBeNull();
  });
});
