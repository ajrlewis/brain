import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Home from "../app/page";

describe("Cortex home", () => {
  it("states the Brain and Cortex boundary", () => {
    const markup = renderToStaticMarkup(<Home />);

    expect(markup).toContain("Brain");
    expect(markup).toContain("Knows");
    expect(markup).toContain("Cortex");
    expect(markup).toContain("Thinks and acts");
  });
});
