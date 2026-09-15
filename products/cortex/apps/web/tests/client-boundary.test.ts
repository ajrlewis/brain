// @vitest-environment node
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
describe("browser boundary", () => {
  it("keeps server configuration out of Client Components", () => {
    const composer = readFileSync(new URL("../components/composer.tsx", import.meta.url), "utf8");
    expect(composer).not.toContain("@/lib/env"); expect(composer).not.toContain("CORTEX_API_BEARER_TOKEN"); expect(composer).not.toContain("Authorization");
  });
});
