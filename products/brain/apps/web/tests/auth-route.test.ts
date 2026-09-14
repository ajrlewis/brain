import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  createSession: () => "signed-session",
  sessionCookie: "brain-session",
  validCredentials: (_user: string, password: string) => password === "valid",
}));

import { POST } from "@/app/api/auth/sign-in/route";

function signInRequest(password = "valid", headers: HeadersInit = {}) {
  const form = `username=brain-admin&password=${encodeURIComponent(password)}`;
  return new Request("http://container:3000/api/auth/sign-in", {
    method: "POST",
    body: form,
    headers: {
      "content-type": "application/x-www-form-urlencoded",
      host: "console.example:3000",
      ...headers,
    },
  });
}

describe("local sign-in route", () => {
  it("redirects to the public HTTP host with a local-compatible cookie", async () => {
    const response = await POST(signInRequest());

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://console.example:3000/pages",
    );
    expect(response.headers.get("set-cookie")).not.toContain("Secure");
  });

  it("honors HTTPS reverse-proxy headers", async () => {
    const response = await POST(
      signInRequest("valid", {
        "x-forwarded-host": "brain.example",
        "x-forwarded-proto": "https",
      }),
    );

    expect(response.headers.get("location")).toBe("https://brain.example/pages");
    expect(response.headers.get("set-cookie")).toContain("Secure");
  });

  it("keeps failed sign-in redirects on the public host", async () => {
    const response = await POST(signInRequest("invalid"));

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://console.example:3000/sign-in?error=credentials",
    );
  });
});
