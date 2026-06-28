import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import WorkflowList from "./WorkflowList";

const ITEMS = [
  {
    id: "wfl-001",
    stage: "admissions",
    trigger: "Pathway recommendation approved by admissions officer",
    owner_name: "Sara Al-Rashidi",
    owner_role: "admissions officer",
    status: "pending",
    description: "Conditional admission — Computer Science",
    due_date: "2025-09-15",
  },
  {
    id: "wfl-002",
    stage: "registration",
    trigger: "Hold placed by finance office",
    owner_name: "Khalid Al-Fadli",
    owner_role: "registrar specialist",
    status: "in_review",
    description: "Resolve financial hold before registration deadline.",
    due_date: "2025-09-10",
  },
];

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: WorkflowList renders each item's stage
// ---------------------------------------------------------------------------

describe("WorkflowList", () => {
  it("renders the stage for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("admissions")).toBeInTheDocument();
    expect(screen.getByText("registration")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — each item shows trigger, owner, and status
  // -------------------------------------------------------------------------

  it("renders the trigger for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("Pathway recommendation approved by admissions officer")).toBeInTheDocument();
    expect(screen.getByText("Hold placed by finance office")).toBeInTheDocument();
  });

  it("renders the owner name for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.getByText("Khalid Al-Fadli")).toBeInTheDocument();
  });

  it("renders the status for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("in_review")).toBeInTheDocument();
  });
});
