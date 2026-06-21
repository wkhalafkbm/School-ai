import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

const PAGES = [
  { label: "Admissions", path: "../app/admissions/page" },
  { label: "Enrollment", path: "../app/enrollment/page" },
  { label: "Teaching Readiness", path: "../app/teaching-readiness/page" },
  { label: "Academic Risk", path: "../app/academic-risk/page" },
  { label: "Progression", path: "../app/progression/page" },
  { label: "Career & Alumni", path: "../app/career-alumni/page" },
  { label: "Workflow Activity", path: "../app/workflow-activity/page" },
];

describe("Placeholder pages", () => {
  it.each(PAGES)("$label page renders its heading", async ({ label, path }) => {
    const { default: Page } = await import(path);
    render(<Page />);
    expect(screen.getByRole("heading", { name: label })).toBeInTheDocument();
  });
});
