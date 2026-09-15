import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ConversationShell } from "@/components/conversation-shell";
import { ApiError, listConversations } from "@/lib/api";
import { readSession, sessionCookie } from "@/lib/session";
export const dynamic = "force-dynamic";
export default async function ConversationsLayout({ children }: { children: React.ReactNode }) {
  const user = readSession((await cookies()).get(sessionCookie)?.value); if (!user) redirect("/sign-in");
  let conversations; try { conversations = (await listConversations()).conversations; } catch (error) { if (error instanceof ApiError && error.kind === "unauthorized") redirect("/sign-in?error=session"); return <ConversationShell conversations={[]} user="Local user"><section className="state"><h1>Cortex is unavailable.</h1><p>Your conversations could not be loaded. Please try again shortly.</p></section></ConversationShell>; }
  return <ConversationShell conversations={conversations} user="Local user">{children}</ConversationShell>;
}
