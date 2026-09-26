import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Shell from "./Shell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

const NAV_LINKS = [
  "Overview",
  "Admissions",
  "Enrollment",
  "Teaching Readiness",
  "Academic Risk",
  "Progression",
  "Academic Quality",
  "Career & Alumni",
  "Workflow Activity",
];

describe("Shell", () => {
  it("renders a nav element", () => {
    render(<Shell>content</Shell>);
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("renders all nine journey-stage nav links", () => {
    render(<Shell>content</Shell>);
    NAV_LINKS.forEach((label) => {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    });
  });

  it("renders children in the content area", () => {
    render(<Shell><p>page body</p></Shell>);
    expect(screen.getByText("page body")).toBeInTheDocument();
  });
});

// Issue #96 — Academic Quality (Agent 10) is a journey stage the sidebar knows
// about. It sits after Progression: program quality is judged once students
// have moved through the stages that feed it.
describe("Shell sidebar — Academic Quality stage (#96)", () => {
  it("links to the Academic Quality page", () => {
    render(<Shell>content</Shell>);
    expect(screen.getByRole("link", { name: "Academic Quality" })).toHaveAttribute(
      "href",
      "/academic-quality"
    );
  });

  it("places Academic Quality directly after Progression", () => {
    render(<Shell>content</Shell>);
    const labels = screen
      .getAllByRole("link")
      .map((link) => link.textContent);
    const progression = labels.indexOf("Progression");
    expect(progression).toBeGreaterThan(-1);
    expect(labels[progression + 1]).toBe("Academic Quality");
  });
});
