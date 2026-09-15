"use client";
import { useActionState, useEffect, useRef } from "react";
import { submitTurn, type TurnState } from "@/app/actions";
const messages: Record<NonNullable<TurnState["error"]>, string> = {
  unauthorized: "Your session is no longer valid. Sign in again.",
  not_found: "This conversation is no longer available.",
  conflict: "Another turn was saved first. The canonical history has been reloaded; review it and try again.",
  history_full: "This conversation has reached its message limit. Start a new conversation to continue.",
  rejected: "Enter a message between 1 and 8,000 characters. The model may also reject unsupported requests.",
  timeout: "The model took too long to respond. Your message was not saved; you can safely retry.",
  unavailable: "The model or Cortex API is temporarily unavailable. Your message was not saved; you can safely retry.",
  invalid_response: "Cortex returned an invalid response. Your message was not saved.",
  unexpected: "Something unexpected happened. Your message was not saved; you can safely retry.",
};
export function Composer({ conversationId }: { conversationId: string }) {
  const formRef = useRef<HTMLFormElement>(null); const action = submitTurn.bind(null, conversationId); const [state, formAction, pending] = useActionState(action, {});
  useEffect(() => { if (!state.error) formRef.current?.reset(); }, [state]);
  return <form ref={formRef} action={formAction} className="composer"><label htmlFor="message">Message Cortex</label><textarea id="message" name="content" maxLength={8000} required rows={3} disabled={pending} placeholder="What would you like to work on?" /><div className="composer-footer"><span aria-live="polite">{pending ? "Cortex is working…" : state.error ? messages[state.error] : "Messages are saved only after Cortex completes its response."}</span><button className="primary" type="submit" disabled={pending}>{pending ? "Working…" : "Send"}</button></div></form>;
}
