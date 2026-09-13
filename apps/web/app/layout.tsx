import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Brain knowledge",
  description: "Read-only governed knowledge console",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
