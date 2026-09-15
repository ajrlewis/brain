import { notFound, redirect } from "next/navigation";
import { Composer } from "@/components/composer";
import { ApiError, getConversation } from "@/lib/api";
export default async function ConversationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; let conversation; try { conversation = await getConversation(id); } catch (error) { if (error instanceof ApiError && error.kind === "not_found") notFound(); if (error instanceof ApiError && error.kind === "unauthorized") redirect("/sign-in?error=session"); return <section className="state"><h1>Conversation unavailable.</h1><p>We could not load this conversation. Please try again shortly.</p></section>; }
  const messages = [...conversation.messages].sort((a, b) => a.sequence - b.sequence);
  return <div className="conversation-view"><header className="conversation-header"><p className="eyebrow">Conversation</p><h1>{conversation.title || `Conversation ${conversation.id.slice(0, 8)}`}</h1></header><section className="messages" aria-label="Messages">{messages.length ? messages.map((message) => <article className={`message message-${message.role}`} key={message.id}><p className="message-role">{message.role === "user" ? "You" : "Cortex"}</p><div>{message.content}</div></article>) : <div className="empty-message"><h2>What are you working on?</h2><p>Send the first message to begin. Nothing is saved until Cortex completes the turn.</p></div>}</section><Composer conversationId={conversation.id} /></div>;
}
