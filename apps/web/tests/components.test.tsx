import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge, EmptyState } from "@/components/ui";
import { Markdown } from "@/components/markdown";
describe("semantic components", () => {
  it("renders status and empty states", () => {
    render(
      <>
        <Badge tone="success">Ready</Badge>
        <EmptyState />
      </>,
    );
    expect(screen.getByText("Ready")).toHaveClass("badge-success");
    expect(
      screen.getByRole("heading", { name: "No pages yet" }),
    ).toBeInTheDocument();
  });
  it("drops raw untrusted HTML while retaining markdown", () => {
    const { container } = render(
      <Markdown
        content={
          "# Safe\n<script>alert(1)</script><style>body{display:none}</style>\n[link](https://example.test)"
        }
      />,
    );
    expect(screen.getByRole("heading", { name: "Safe" })).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("style")).toBeNull();
    expect(screen.getByRole("link")).toHaveAttribute(
      "rel",
      expect.stringContaining("noopener"),
    );
  });
});
