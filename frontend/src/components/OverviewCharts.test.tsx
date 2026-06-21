import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import OverviewCharts from "./OverviewCharts";

const CHART_DATA = {
  enrollments_by_semester: [
    { semester: "Fall 2022", count: 10 },
    { semester: "Spring 2023", count: 15 },
    { semester: "Fall 2023", count: 12 },
  ],
  gpa_distribution: [
    { bucket: "<2.0", count: 5 },
    { bucket: "2.0-2.5", count: 8 },
    { bucket: "2.5-3.0", count: 12 },
    { bucket: "3.0-3.5", count: 20 },
    { bucket: "3.5-4.0", count: 15 },
  ],
  intervention_outcomes: [
    { status: "completed", count: 8 },
    { status: "in_progress", count: 3 },
    { status: "pending", count: 2 },
  ],
  lms_risk_by_semester: [
    { semester: "Fall 2022", at_risk: 2, total: 10 },
    { semester: "Spring 2023", at_risk: 4, total: 15 },
  ],
};

describe("OverviewCharts", () => {
  it("renders four chart sections", () => {
    const { container } = render(<OverviewCharts data={CHART_DATA} />);
    const charts = container.querySelectorAll("[data-testid='chart-section']");
    expect(charts).toHaveLength(4);
  });

  it("enrollments chart has one bar per semester", () => {
    const { container } = render(<OverviewCharts data={CHART_DATA} />);
    const bars = container.querySelectorAll("[data-testid='enrollments-bar']");
    expect(bars).toHaveLength(3);
  });

  it("GPA distribution chart has one bar per bucket", () => {
    const { container } = render(<OverviewCharts data={CHART_DATA} />);
    const bars = container.querySelectorAll("[data-testid='gpa-bar']");
    expect(bars).toHaveLength(5);
  });

  it("intervention outcomes chart has one bar per status", () => {
    const { container } = render(<OverviewCharts data={CHART_DATA} />);
    const bars = container.querySelectorAll("[data-testid='intervention-bar']");
    expect(bars).toHaveLength(3);
  });

  it("LMS risk chart has one group per semester", () => {
    const { container } = render(<OverviewCharts data={CHART_DATA} />);
    const groups = container.querySelectorAll("[data-testid='lms-risk-group']");
    expect(groups).toHaveLength(2);
  });

  it("renders a heading for each chart section", () => {
    render(<OverviewCharts data={CHART_DATA} />);
    expect(screen.getByText("Enrollments by Semester")).toBeTruthy();
    expect(screen.getByText("GPA Distribution")).toBeTruthy();
    expect(screen.getByText("Intervention Outcomes")).toBeTruthy();
    expect(screen.getByText("LMS Risk by Semester")).toBeTruthy();
  });
});
