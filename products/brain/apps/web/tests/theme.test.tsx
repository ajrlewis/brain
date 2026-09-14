import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { themeStyle, themeTokens, themes } from "@/lib/theme";
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));
import { ThemePicker } from "@/components/theme-picker";
describe("themes", () => {
  it("validates complete safe semantic palettes", () => {
    expect(themeTokens.parse(themes.brain)).toEqual(themes.brain);
    expect(() =>
      themeTokens.parse({ ...themes.brain, primary: "url(javascript:x)" }),
    ).toThrow();
  });
  it("maps tokens to CSS properties", () => {
    expect(themeStyle(themes.northstar)).toMatchObject({
      "--primary": "#173b57",
      "--surface-raised": "#fffdf8",
    });
  });
  it("switches the runtime theme cookie", () => {
    render(<ThemePicker value="brain" />);
    fireEvent.change(screen.getByLabelText("Company theme"), {
      target: { value: "northstar" },
    });
    expect(document.cookie).toContain("brain-theme=northstar");
  });
});
