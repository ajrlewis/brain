import Link from "next/link";
import type { ReactNode } from "react";
import { ThemePicker } from "./theme-picker";
import type { ThemeName } from "@/lib/theme";
import type { PageSummary } from "@/lib/api";
export function AppShell({
  children,
  theme,
  user,
  pages,
}: {
  children: ReactNode;
  theme: ThemeName;
  user: string;
  pages: PageSummary[];
}) {
  const folders = [
    ...new Set(
      pages
        .map((page) => page.path.split("/").slice(0, -1).join("/"))
        .filter(Boolean),
    ),
  ];
  return (
    <>
      <header className="header">
        <Link href="/pages" className="brand">
          <span className="brand-mark">B</span>
          <span>Brain</span>
          <small>Knowledge console</small>
        </Link>
        <div className="account">
          <ThemePicker value={theme} />
          <span className="avatar" aria-hidden>
            {user[0].toUpperCase()}
          </span>
          <span>{user}</span>
          <form action="/api/auth/sign-out" method="post">
            <button className="sign-out">Sign out</button>
          </form>
        </div>
      </header>
      <div className="shell">
        <aside className="sidebar">
          <p className="eyebrow">Workspace</p>
          <nav>
            <Link href="/search">Search</Link>
            <Link href="/pages">Pages & folders</Link>
            <Link href="/skills">Skills</Link>
            <Link href="/references">Reference files</Link>
          </nav>
          {folders.length > 0 && (
            <div className="folder-tree">
              <p className="eyebrow">Folders</p>
              <ul>
                {folders.map((folder) => (
                  <li key={folder}>⌞ {folder.replaceAll("/", " / ")}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="sidebar-note">Read-only · governed by Brain</p>
        </aside>
        <main>{children}</main>
      </div>
    </>
  );
}
