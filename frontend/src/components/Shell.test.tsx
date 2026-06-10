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
  "Career & Alumni",
  "Workflow Activity",
];

describe("Shell", () => {
  it("renders a nav element", () => {
    render(<Shell>content</Shell>);
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("renders all eight journey-stage nav links", () => {
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
