"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { ApiError, appendTurn, createConversation } from "@/lib/api";
import { readSession, sessionCookie } from "@/lib/session";

export type TurnState = { error?: ApiError["kind"] };

async function requireSession() {
  const value = (await cookies()).get(sessionCookie)?.value;
  if (!readSession(value)) redirect("/sign-in");
}

export async function newConversation() {
  await requireSession();
  let conversation;
  try {
    conversation = await createConversation();
  } catch (error) {
    if (error instanceof ApiError && error.kind === "unauthorized")
      redirect("/sign-in?error=session");
    throw error;
  }
  redirect(`/conversations/${conversation.id}`);
}

export async function submitTurn(
  conversationId: string,
  _state: TurnState,
  formData: FormData,
): Promise<TurnState> {
  await requireSession();
  const content = String(formData.get("content") ?? "").trim();
  if (!content || content.length > 8_000) return { error: "rejected" };
  try {
    await appendTurn(conversationId, content);
    revalidatePath(`/conversations/${conversationId}`);
    return {};
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.kind === "conflict") revalidatePath(`/conversations/${conversationId}`);
      return { error: error.kind };
    }
    return { error: "unexpected" };
  }
}
