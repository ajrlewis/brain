import { z } from "zod";

const safeColor = z
  .string()
  .regex(
    /^(#[0-9a-fA-F]{6}|(rgb|hsl)a?\([\d\s.,%/-]+\))$/,
    "unsafe CSS colour",
  );
export const themeTokens = z.object({
  primary: safeColor,
  accent: safeColor,
  surface: safeColor,
  surfaceRaised: safeColor,
  text: safeColor,
  textMuted: safeColor,
  border: safeColor,
  focus: safeColor,
  success: safeColor,
  warning: safeColor,
  danger: safeColor,
});
export type ThemeTokens = z.infer<typeof themeTokens>;
export const themes = {
  brain: themeTokens.parse({
    primary: "#334155",
    accent: "#0f766e",
    surface: "#f8fafc",
    surfaceRaised: "#ffffff",
    text: "#0f172a",
    textMuted: "#475569",
    border: "#cbd5e1",
    focus: "#2563eb",
    success: "#15803d",
    warning: "#a16207",
    danger: "#b91c1c",
  }),
  northstar: themeTokens.parse({
    primary: "#173b57",
    accent: "#b45309",
    surface: "#f5f2eb",
    surfaceRaised: "#fffdf8",
    text: "#17242e",
    textMuted: "#52616b",
    border: "#c9c2b4",
    focus: "#075985",
    success: "#347044",
    warning: "#9a5b05",
    danger: "#a33131",
  }),
} satisfies Record<string, ThemeTokens>;
export type ThemeName = keyof typeof themes;
export function isThemeName(value: string): value is ThemeName {
  return value in themes;
}
export function themeStyle(theme: ThemeTokens): React.CSSProperties {
  return Object.fromEntries(
    Object.entries(theme).map(([key, value]) => [
      `--${key.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)}`,
      value,
    ]),
  ) as React.CSSProperties;
}
