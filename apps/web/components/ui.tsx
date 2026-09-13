import Link from "next/link";
import type { ReactNode } from "react";
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function ButtonLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <Link className="button" href={href}>
      {children}
    </Link>
  );
}
export function Breadcrumbs({
  items,
}: {
  items: { label: string; href?: string }[];
}) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="breadcrumbs">
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`}>
            {item.href ? (
              <Link href={item.href}>{item.label}</Link>
            ) : (
              <span aria-current="page">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
export function EmptyState() {
  return (
    <Card>
      <h2>No pages yet</h2>
      <p>
        Authorized knowledge will appear here once it has been added to Brain.
      </p>
    </Card>
  );
}
export function ErrorState({ message }: { message: string }) {
  return (
    <Card className="state-error">
      <Badge tone="danger">Error</Badge>
      <h2>Knowledge unavailable</h2>
      <p>{message}</p>
      <ButtonLink href="/pages">Try again</ButtonLink>
    </Card>
  );
}
