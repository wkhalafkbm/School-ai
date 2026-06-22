import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AdmissionsStageHeader from "./AdmissionsStageHeader";

const SUMMARY = {
  health: "watch" as const,
  applicant_count: 1,
  pending_review_count: 1,
};

describe("AdmissionsStageHeader", () => {
  // Cycle 1 — tracer bullet: heading renders
  it("renders the Admissions heading", () => {
    render(<AdmissionsStageHeader summary={SUMMARY} />);
    expect(screen.getByRole("heading", { name: /admissions/i })).toBeInTheDocument();
  });

  // Cycle 2 — shows health badge and applicant count
  it("shows a health badge reflecting the current status", () => {
    render(<AdmissionsStageHeader summary={SUMMARY} />);
    expect(screen.getByTestId("health-badge")).toBeInTheDocument();
    expect(screen.getByTestId("health-badge")).toHaveTextContent(/watch/i);
  });

  it("shows the applicant count", () => {
    render(<AdmissionsStageHeader summary={SUMMARY} />);
    expect(screen.getByTestId("applicant-count")).toHaveTextContent("1");
  });

  it("shows the pending review count", () => {
    render(<AdmissionsStageHeader summary={SUMMARY} />);
    expect(screen.getByTestId("pending-review-count")).toHaveTextContent("1");
  });

  it("uses health status as an accent only — not as a background fill", () => {
    const { container } = render(<AdmissionsStageHeader summary={{ ...SUMMARY, health: "urgent" }} />);
    const heading = container.querySelector("h1, h2");
    expect(heading?.className).not.toMatch(/bg-red/);
  });
});
