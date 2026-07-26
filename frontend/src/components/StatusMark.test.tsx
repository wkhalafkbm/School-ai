import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusMark from "./StatusMark";
import { StatusCode } from "@/lib/status";

const ALL_CODES: StatusCode[] = ["on_track", "watch", "needs_attention", "urgent", "opportunity"];

// Expected labels are written out here rather than read back from STATUS_CLASSES,
// so the test disagrees with the module if either side drifts.
const EXPECTED_LABELS: Record<StatusCode, string> = {
  on_track: "On Track",
  watch: "Watch",
  needs_attention: "Needs Attention",
  urgent: "Urgent",
  opportunity: "Opportunity",
};

// Written out for the same reason as EXPECTED_LABELS above.
const EXPECTED_ACCENTS: Record<StatusCode, string> = {
  on_track: "bg-green-500",
  watch: "bg-amber-500",
  needs_attention: "bg-orange-500",
  urgent: "bg-red-500",
  opportunity: "bg-teal-500",
};

describe("StatusMark", () => {
  it("renders the status label, cased up by the stylesheet so the text stays readable", () => {
    for (const code of ALL_CODES) {
      const { unmount } = render(<StatusMark code={code} />);
      const label = screen.getByText(EXPECTED_LABELS[code]);
      expect(label.className).toContain("uppercase");
      unmount();
    }
  });

  it("colours both the rail and the dot with the status accent, for every status code", () => {
    for (const code of ALL_CODES) {
      const { unmount } = render(<StatusMark code={code} />);
      expect(screen.getByTestId("status-rail").className).toContain(EXPECTED_ACCENTS[code]);
      expect(screen.getByTestId("status-dot").className).toContain(EXPECTED_ACCENTS[code]);
      unmount();
    }
  });

  it("occupies a fixed-width column that does not vary with the status shown", () => {
    const widths = ALL_CODES.map((code) => {
      const { container, unmount } = render(<StatusMark code={code} />);
      const root = container.firstElementChild as HTMLElement;
      const className = root.className;
      unmount();
      return className;
    });

    // "Watch" and "Needs Attention" must reserve the same horizontal space,
    // so whatever follows the mark starts at the same offset on every row.
    expect(new Set(widths).size).toBe(1);
    expect(widths[0]).toContain("w-40");
    expect(widths[0]).toContain("shrink-0");
  });

  it("degrades to a neutral mark showing the raw code when the status is unrecognised", () => {
    const unknown = "deferred_pending_review" as StatusCode;

    expect(() => render(<StatusMark code={unknown} />)).not.toThrow();

    expect(screen.getByText("deferred_pending_review")).toBeTruthy();
    const rail = screen.getByTestId("status-rail");
    expect(rail.className).toContain("bg-gray-400");
    for (const accent of Object.values(EXPECTED_ACCENTS)) {
      expect(rail.className).not.toContain(accent);
    }
  });
});
