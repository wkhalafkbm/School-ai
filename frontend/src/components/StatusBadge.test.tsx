import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusBadge from "./StatusBadge";
import { StatusCode, STATUS_CLASSES } from "@/lib/status";

const ALL_CODES: StatusCode[] = ["on_track", "watch", "needs_attention", "urgent", "opportunity"];

describe("StatusBadge", () => {
  it("renders a chip element with the on_track color class", () => {
    const { container } = render(<StatusBadge code="on_track" />);
    const chip = container.querySelector("span");
    expect(chip).not.toBeNull();
    expect(chip!.className).toContain("bg-green-100");
    expect(chip!.className).toContain("text-green-700");
  });

  it("renders the human-readable label and correct color classes for every status code", () => {
    for (const code of ALL_CODES) {
      const { container, unmount } = render(<StatusBadge code={code} />);
      expect(screen.getByText(STATUS_CLASSES[code].label)).toBeTruthy();
      const chip = container.querySelector("span")!;
      for (const cls of STATUS_CLASSES[code].classes.split(" ")) {
        expect(chip.className).toContain(cls);
      }
      unmount();
    }
  });

  it("renders as an inline accent chip, not a full-width block", () => {
    const { container } = render(<StatusBadge code="urgent" />);
    const chip = container.querySelector("span")!;
    expect(chip.className).toContain("inline-flex");
    expect(chip.className).not.toContain("w-full");
    expect(chip.className).not.toContain("block");
  });
});
