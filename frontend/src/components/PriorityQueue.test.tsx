import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PriorityQueue from "./PriorityQueue";

const ITEMS = [
  { student_id: "s-001", student_name: "Alice Smith", stage: "academic_progress", status: "urgent" as const, reason: "LMS risk flag raised" },
  { student_id: "s-002", student_name: "Bob Jones", stage: "graduation_planning", status: "needs_attention" as const, reason: "Missing graduation audit" },
  { student_id: "s-003", student_name: "Carol Wu", stage: "onboarding", status: "watch" as const, reason: "Incomplete onboarding tasks" },
];

describe("PriorityQueue", () => {
  it("renders one row per item", () => {
    const { container } = render(<PriorityQueue items={ITEMS} />);
    const rows = container.querySelectorAll("[data-testid='queue-row']");
    expect(rows).toHaveLength(3);
  });

  it("displays the student name in each row", () => {
    render(<PriorityQueue items={ITEMS} />);
    expect(screen.getByText("Alice Smith")).toBeTruthy();
    expect(screen.getByText("Bob Jones")).toBeTruthy();
    expect(screen.getByText("Carol Wu")).toBeTruthy();
  });

  it("displays the reason in each row", () => {
    render(<PriorityQueue items={ITEMS} />);
    expect(screen.getByText("LMS risk flag raised")).toBeTruthy();
    expect(screen.getByText("Missing graduation audit")).toBeTruthy();
    expect(screen.getByText("Incomplete onboarding tasks")).toBeTruthy();
  });

  it("renders a StatusBadge for each row", () => {
    const { container } = render(<PriorityQueue items={ITEMS} />);
    const badges = container.querySelectorAll("[data-testid='queue-row'] span");
    expect(badges.length).toBeGreaterThanOrEqual(3);
  });

  it("links each row to the correct stage page with student query param", () => {
    const { container } = render(<PriorityQueue items={ITEMS} />);
    const links = container.querySelectorAll("a[data-testid='queue-row']");
    expect(links[0].getAttribute("href")).toBe("/academic-risk?student=s-001");
    expect(links[1].getAttribute("href")).toBe("/progression?student=s-002");
    expect(links[2].getAttribute("href")).toBe("/admissions?student=s-003");
  });

  it("displays the stage label in each row", () => {
    render(<PriorityQueue items={ITEMS} />);
    expect(screen.getByText("Academic Progress")).toBeTruthy();
    expect(screen.getByText("Graduation Planning")).toBeTruthy();
    expect(screen.getByText("Onboarding")).toBeTruthy();
  });

  // Issue #66 added a GPA-trend source to the queue. Its rows are ordinary
  // queue rows, so the component needs no special case — these are copied
  // verbatim from the endpoint's response so that stays true.
  const TREND_ITEMS = [
    {
      student_id: "stu-003",
      student_name: "Fahad Al-Ajmi",
      stage: "academic_progress",
      status: "urgent" as const,
      reason: "GPA declined 1.90 → 1.40 in 2024-Fall (sharp drop)",
    },
    {
      student_id: "stu-013",
      student_name: "Noura Al-Sabah",
      stage: "academic_progress",
      status: "watch" as const,
      reason:
        "GPA declined 2.90 → 2.65 → 2.40 across 2023-Fall–2024-Fall, a total of 0.50 over two terms (sustained decline)",
    },
  ];

  it("renders GPA-trend rows with their reason and tier intact", () => {
    render(<PriorityQueue items={TREND_ITEMS} />);
    expect(screen.getByText(TREND_ITEMS[0].reason)).toBeTruthy();
    expect(screen.getByText(TREND_ITEMS[1].reason)).toBeTruthy();
    expect(screen.getByText("Urgent")).toBeTruthy();
    expect(screen.getByText("Watch")).toBeTruthy();
  });

  it("routes GPA-trend rows to the Academic Risk page", () => {
    const { container } = render(<PriorityQueue items={TREND_ITEMS} />);
    const links = container.querySelectorAll("a[data-testid='queue-row']");
    expect(links[0].getAttribute("href")).toBe("/academic-risk?student=stu-003");
    expect(links[1].getAttribute("href")).toBe("/academic-risk?student=stu-013");
  });
});
