import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import KpiCards from "./KpiCards";

const METRICS = {
  students_needing_attention: 3,
  at_risk_detected_early: 1,
  registration_issues_resolved: 0,
  graduation_delays_prevented: 1,
  faculty_overload_alerts: 1,
};

describe("KpiCards", () => {
  it("renders five cards", () => {
    const { container } = render(<KpiCards metrics={METRICS} />);
    const cards = container.querySelectorAll("[data-testid='kpi-card']");
    expect(cards).toHaveLength(5);
  });

  it("displays the numeric value for each metric", () => {
    render(<KpiCards metrics={METRICS} />);
    expect(screen.getByTestId("kpi-students_needing_attention")).toHaveTextContent("3");
    expect(screen.getByTestId("kpi-at_risk_detected_early")).toHaveTextContent("1");
    expect(screen.getByTestId("kpi-registration_issues_resolved")).toHaveTextContent("0");
    expect(screen.getByTestId("kpi-graduation_delays_prevented")).toHaveTextContent("1");
    expect(screen.getByTestId("kpi-faculty_overload_alerts")).toHaveTextContent("1");
  });

  it("displays a human-readable label for each card", () => {
    render(<KpiCards metrics={METRICS} />);
    expect(screen.getByText("Students Needing Attention")).toBeTruthy();
    expect(screen.getByText("At-Risk Detected Early")).toBeTruthy();
    expect(screen.getByText("Registration Issues Resolved")).toBeTruthy();
    expect(screen.getByText("Graduation Delays Prevented")).toBeTruthy();
    expect(screen.getByText("Faculty Overload Alerts")).toBeTruthy();
  });
});
