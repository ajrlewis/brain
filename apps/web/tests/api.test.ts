import { afterEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
vi.mock("@/lib/env", () => ({
  env: () => ({
    BRAIN_API_URL: "http://api.test",
    LOCAL_BEARER_TOKEN: "server-secret",
  }),
}));
import { ApiError, getPages } from "@/lib/api";
const page = {
  id: "10000000-0000-0000-0000-000000000001",
  slug: "hello",
  title: "Hello",
  path: "handbook/hello",
  current_version_id: "20000000-0000-0000-0000-000000000001",
  content_hash: "abc",
};
describe("API transport", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("validates success and sends auth only server-side", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify([page])));
    vi.stubGlobal("fetch", fetcher);
    await expect(getPages()).resolves.toEqual([page]);
    expect(fetcher).toHaveBeenCalledWith(
      "http://api.test/pages",
      expect.objectContaining({
        headers: { Authorization: "Bearer server-secret" },
      }),
    );
  });
  it.each([
    [403, "access"],
    [404, "found"],
    [500, "unexpected"],
  ])("maps HTTP %s", async (status, text) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status })),
    );
    await expect(getPages()).rejects.toMatchObject({ status });
    await expect(getPages()).rejects.toThrow(text as string);
  });
  it("rejects schema drift", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify([{ id: "bad" }]))),
    );
    await expect(getPages()).rejects.toEqual(
      new ApiError(502, "Brain API returned an invalid response."),
    );
  });
  it("maps connection failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(getPages()).rejects.toMatchObject({ status: 503 });
  });
});
