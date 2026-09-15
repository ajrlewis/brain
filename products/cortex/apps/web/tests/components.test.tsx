import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
vi.mock("@/app/actions", () => ({ newConversation: vi.fn(), submitTurn: vi.fn() }));
import { ConversationShell, conversationLabel } from "@/components/conversation-shell";
import { Composer } from "@/components/composer";
const summary = (id: string, title: string | null = null) => ({ id, title, created_at: "2026-09-15T10:00:00Z", updated_at: "2026-09-15T10:00:00Z" });
describe("conversation components", () => {
  it("renders fallback labels and empty navigation", () => { expect(conversationLabel(summary("12345678-0000-4000-8000-000000000001"))).toBe("Conversation 12345678"); const { rerender } = render(<ConversationShell conversations={[]} user="local-user"><p>Empty state</p></ConversationShell>); expect(screen.getByText("No conversations yet.")).toBeInTheDocument(); rerender(<ConversationShell conversations={[summary("12345678-0000-4000-8000-000000000001", "Synthetic title")]} user="local-user"><p>Content</p></ConversationShell>); expect(screen.getByRole("link", { name: "Synthetic title" })).toBeInTheDocument(); });
  it("enforces composer bounds and exposes durable semantics", () => { render(<Composer conversationId="123" />); const input = screen.getByLabelText("Message Cortex"); expect(input).toHaveAttribute("maxlength", "8000"); expect(input).toBeRequired(); fireEvent.change(input, { target: { value: "x".repeat(8001) } }); expect((input as HTMLTextAreaElement).value).toHaveLength(8001); expect(screen.getByText(/saved only after Cortex completes/)).toBeInTheDocument(); });
});
