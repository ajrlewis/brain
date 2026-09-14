import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/shell";
import { isThemeName, themes, themeStyle } from "@/lib/theme";
import { readSession, sessionCookie } from "@/lib/session";
import { getPages } from "@/lib/api";
export const dynamic = "force-dynamic";
export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const jar = await cookies();
  const user = readSession(jar.get(sessionCookie)?.value);
  if (!user) redirect("/sign-in");
  const stored = jar.get("brain-theme")?.value ?? "northstar";
  const name = isThemeName(stored) ? stored : "brain";
  const pages = await getPages().catch(() => []);
  return (
    <div data-theme={name} style={themeStyle(themes[name])}>
      <a className="skip-link" href="#content">
        Skip to content
      </a>
      <AppShell theme={name} user={user} pages={pages}>
        {children}
      </AppShell>
    </div>
  );
}
