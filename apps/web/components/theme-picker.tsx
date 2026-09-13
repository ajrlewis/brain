"use client";
import { useRouter } from "next/navigation";
import type { ThemeName } from "@/lib/theme";
export function ThemePicker({ value }: { value: ThemeName }) {
  const router = useRouter();
  return (
    <label className="theme-picker">
      Theme{" "}
      <select
        aria-label="Company theme"
        value={value}
        onChange={(event) => {
          document.cookie = `brain-theme=${event.target.value}; path=/; max-age=31536000; samesite=lax`;
          router.refresh();
        }}
      >
        <option value="brain">Brain</option>
        <option value="northstar">Northstar</option>
      </select>
    </label>
  );
}
