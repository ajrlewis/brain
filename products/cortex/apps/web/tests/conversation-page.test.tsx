import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
const { getConversation } = vi.hoisted(() => ({ getConversation: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getConversation };
});
vi.mock("@/components/composer", () => ({ Composer: () => <div>Composer</div> }));
import ConversationPage from "@/app/conversations/[id]/page";

const base = { id: "10000000-0000-4000-8000-000000000001", title: null, created_at: "2026-09-15T10:00:00Z", updated_at: "2026-09-15T10:00:00Z" };
describe("conversation page", () => {
  it("renders canonical sequence order and wraps long content", async () => {
    const long = "long content ".repeat(500);
    getConversation.mockResolvedValue({ ...base, messages: [
      { id: "30000000-0000-4000-8000-000000000002", sequence: 2, role: "assistant", content: long, created_at: base.created_at },
      { id: "30000000-0000-4000-8000-000000000001", sequence: 1, role: "user", content: "first", created_at: base.created_at },
    ] });
    const view = await ConversationPage({ params: Promise.resolve({ id: base.id }) }); render(view);
    const articles = screen.getAllByRole("article"); expect(articles[0]).toHaveTextContent("first"); expect(articles[1].textContent).toContain(long.slice(0, 200)); expect(articles[1]).toHaveClass("message");
  });
  it("renders a useful first-message state", async () => {
    getConversation.mockResolvedValue({ ...base, messages: [] });
    render(await ConversationPage({ params: Promise.resolve({ id: base.id }) }));
    expect(screen.getByRole("heading", { name: "What are you working on?" })).toBeInTheDocument();
  });
});
