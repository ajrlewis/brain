import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, searchPages: vi.fn() };
});

import SearchPage from "@/app/(console)/search/page";
import { ApiError, searchPages } from "@/lib/api";

const mockedSearch = vi.mocked(searchPages);

describe("search page states", () => {
  beforeEach(() => mockedSearch.mockReset());

  it("shows the initial empty prompt", async () => {
    render(await SearchPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText("Start with a question or phrase")).toBeVisible();
  });

  it("rejects whitespace without calling the backend", async () => {
    render(await SearchPage({ searchParams: Promise.resolve({ q: "   " }) }));
    expect(screen.getByText("Enter a meaningful query")).toBeVisible();
    expect(mockedSearch).not.toHaveBeenCalled();
  });

  it("distinguishes denied and backend-failure responses", async () => {
    mockedSearch.mockRejectedValueOnce(new ApiError(403, "No access."));
    const denied = render(
      await SearchPage({ searchParams: Promise.resolve({ q: "secret" }) }),
    );
    expect(screen.getByText("Search access denied")).toBeVisible();
    denied.unmount();

    mockedSearch.mockRejectedValueOnce(new ApiError(503, "Offline."));
    render(await SearchPage({ searchParams: Promise.resolve({ q: "facts" }) }));
    expect(screen.getByText("Search unavailable")).toBeVisible();
  });

  it("shows an authorized empty result", async () => {
    mockedSearch.mockResolvedValue({ query: "none", results: [] });
    render(await SearchPage({ searchParams: Promise.resolve({ q: "none" }) }));
    expect(screen.getByText("No authorized results")).toBeVisible();
  });
});
