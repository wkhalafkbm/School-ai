import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import JourneyHealthMap from "./JourneyHealthMap";
import { STATUS_CLASSES } from "@/lib/status";

const HEALTH = {
  admissions: "watch" as const,
  enrollment: "on_track" as const,
  academic_risk: "urgent" as const,
  progression: "urgent" as const,
  career_alumni: "needs_attention" as const,
};

// The labels the nav uses for the same stages — the map and the sidebar name a
// stage the same way or the Overview reads as a different product (#68).
const STAGE_LABELS = {
  admissions: "Admissions",
  enrollment: "Enrollment",
  academic_risk: "Academic Risk",
  progression: "Progression",
  career_alumni: "Career & Alumni",
};

describe("JourneyHealthMap", () => {
  it("renders one badge per stage (five total)", () => {
    const { container } = render(<JourneyHealthMap health={HEALTH} />);
    const badges = container.querySelectorAll("[data-testid='health-badge']");
    expect(badges).toHaveLength(5);
  });

  it("renders the human-readable stage label for each stage", () => {
    render(<JourneyHealthMap health={HEALTH} />);
    for (const label of Object.values(STAGE_LABELS)) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("applies the correct color classes from STATUS_CLASSES for each stage", () => {
    const { container } = render(<JourneyHealthMap health={HEALTH} />);
    const badges = container.querySelectorAll("[data-testid='health-badge']");
    const stages = Object.keys(HEALTH) as (keyof typeof HEALTH)[];
    stages.forEach((stage, i) => {
      const code = HEALTH[stage];
      for (const cls of STATUS_CLASSES[code].classes.split(" ")) {
        expect((badges[i] as HTMLElement).className).toContain(cls);
      }
    });
  });
});
