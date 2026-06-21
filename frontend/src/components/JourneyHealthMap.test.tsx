import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import JourneyHealthMap from "./JourneyHealthMap";
import { STATUS_CLASSES } from "@/lib/status";

const HEALTH = {
  onboarding: "watch" as const,
  registration: "on_track" as const,
  academic_progress: "urgent" as const,
  graduation_planning: "urgent" as const,
  career: "needs_attention" as const,
};

const STAGE_LABELS = {
  onboarding: "Onboarding",
  registration: "Registration",
  academic_progress: "Academic Progress",
  graduation_planning: "Graduation Planning",
  career: "Career",
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
