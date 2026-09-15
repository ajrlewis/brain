// @vitest-environment node
import { describe, expect, it, vi } from "vitest";
vi.mock("@/lib/session", () => ({ createSession: () => "signed-session", sessionCookie: "cortex-session", validCredentials: (_u: string, password: string) => password === "valid" }));
import { POST } from "@/app/api/auth/sign-in/route";
function request(password = "valid", headers: HeadersInit = {}) { return new Request("http://container:3000/api/auth/sign-in", { method: "POST", body: `username=cortex-user&password=${password}`, headers: { "content-type": "application/x-www-form-urlencoded", host: "cortex.example", ...headers } }); }
describe("local sign-in", () => {
  it("sets a separate HTTP-only same-site cookie and redirects", async () => { const response = await POST(request()); expect(response.status).toBe(303); expect(response.headers.get("location")).toBe("http://cortex.example/conversations"); const cookie = response.headers.get("set-cookie")!; expect(cookie).toContain("cortex-session=signed-session"); expect(cookie).toContain("HttpOnly"); expect(cookie).toContain("SameSite=lax"); expect(cookie).not.toContain("brain-session"); expect(cookie).not.toContain("Secure"); });
  it("uses secure cookies behind HTTPS", async () => { const response = await POST(request("valid", { "x-forwarded-proto": "https" })); expect(response.headers.get("set-cookie")).toContain("Secure"); });
  it("rejects bad credentials without a cookie", async () => { const response = await POST(request("bad")); expect(response.headers.get("location")).toContain("error=credentials"); expect(response.headers.get("set-cookie")).toBeNull(); });
});
