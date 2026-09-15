"use client";
import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { ConversationResponse } from "@/lib/generated/api";

type Message = z.infer<typeof ConversationResponse>["messages"][number];
const errors: Record<string, string> = {
  conversation_not_found: "This conversation is no longer available. Nothing was saved.",
  conversation_conflict: "Another turn was saved first. Canonical history has been reloaded.",
  conversation_history_full: "This conversation has reached its message limit. Nothing was saved.",
  model_timeout: "The model took too long. Nothing was saved; you can safely retry.",
  model_unavailable: "Cortex is temporarily unavailable. Nothing was saved; you can safely retry.",
  model_rejected_request: "The model rejected this request. Nothing was saved.",
  invalid_model_response: "Cortex returned an invalid response. Nothing was saved.",
  conversation_error: "Something unexpected happened. Nothing was saved; you can safely retry.",
};

export function Composer({ conversationId, initialMessages = [] }: { conversationId: string; initialMessages?: Message[] }) {
  const router = useRouter(); const [messages, setMessages] = useState(initialMessages); const [userText, setUserText] = useState(""); const [assistantText, setAssistantText] = useState(""); const [pending, setPending] = useState(false); const [status, setStatus] = useState("Messages are saved only after Cortex completes its response."); const abort = useRef<AbortController | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); const content = userText.trim(); if (!content || content.length > 8_000 || pending) return;
    setPending(true); setAssistantText(""); setStatus("Cortex is responding. This turn is not saved yet."); abort.current = new AbortController(); let terminal = false;
    try {
      const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/turns/stream`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }), signal: abort.current.signal });
      if (!response.ok || !response.body) throw new Error(); const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) { const { value, done } = await reader.read(); buffer += decoder.decode(value, { stream: !done }); let boundary: number; while ((boundary = buffer.indexOf("\n\n")) >= 0) { const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2); const match = frame.match(/^event: (delta|completed|error)\ndata: (.+)$/s); if (!match) throw new Error(); const data = JSON.parse(match[2]); if (match[1] === "delta") setAssistantText((value) => value + String(data.text)); else if (match[1] === "completed") { const parsed = ConversationResponse.parse(data.conversation); setMessages([...parsed.messages].sort((a, b) => a.sequence - b.sequence)); setUserText(""); setAssistantText(""); setStatus("Response saved."); terminal = true; router.refresh(); } else { setAssistantText(""); setStatus(errors[String(data.error)] ?? errors.conversation_error); terminal = true; if (data.error === "conversation_conflict") router.refresh(); } } if (done) break; }
      if (!terminal) throw new Error();
    } catch (error) { setAssistantText(""); setStatus(error instanceof DOMException && error.name === "AbortError" ? "Stopped. Nothing was saved." : errors.conversation_error); }
    finally { setPending(false); abort.current = null; }
  }
  return <><section className="messages" aria-label="Messages">{messages.length ? messages.map((message) => <article className={`message message-${message.role}`} key={message.id}><p className="message-role">{message.role === "user" ? "You" : "Cortex"}</p><div>{message.content}</div></article>) : !pending && <div className="empty-message"><h2>What are you working on?</h2><p>Send the first message to begin. Nothing is saved until Cortex completes the turn.</p></div>}{pending && <div className="transient-turn" aria-label="Unsaved response"><article className="message message-user transient"><p className="message-role">You · not saved</p><div>{userText}</div></article>{assistantText && <article className="message transient"><p className="message-role">Cortex · not saved</p><div>{assistantText}</div></article>}</div>}</section><form onSubmit={submit} className="composer"><label htmlFor="message">Message Cortex</label><textarea id="message" value={userText} onChange={(event) => setUserText(event.target.value)} maxLength={8000} required rows={3} disabled={pending} placeholder="What would you like to work on?" /><div className="composer-footer"><span aria-live="polite">{status}</span><div>{pending && <button className="text-button stop-button" type="button" onClick={() => abort.current?.abort()}>Stop</button>}<button className="primary" type="submit" disabled={pending}>{pending ? "Working…" : "Send"}</button></div></div></form></>;
}
