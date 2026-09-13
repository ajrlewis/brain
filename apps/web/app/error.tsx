"use client";
import { ErrorState } from "@/components/ui";
export default function ErrorPage() {
  return (
    <div id="content" className="content">
      <ErrorState message="The console encountered an unexpected error." />
    </div>
  );
}
