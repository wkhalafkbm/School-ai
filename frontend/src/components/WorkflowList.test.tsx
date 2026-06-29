import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    stage: "enrollment",
    trigger: "Hold placed by finance office",
    owner_name: "Khalid Al-Fadli",
    owner_role: "registrar specialist",
    status: "in_progress",
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
    const table = screen.getByRole("table");
    expect(within(table).getByText("admissions")).toBeInTheDocument();
    expect(within(table).getByText("enrollment")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — each item shows trigger and owner name
  // -------------------------------------------------------------------------

  it("renders the trigger for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(
      screen.getByText("Pathway recommendation approved by admissions officer")
    ).toBeInTheDocument();
    expect(screen.getByText("Hold placed by finance office")).toBeInTheDocument();
  });

  it("renders the owner name for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.getByText("Khalid Al-Fadli")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — table structure with column headers
  // -------------------------------------------------------------------------

  it("renders a table with all required column headers", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /stage/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /trigger/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /owner/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /role/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /status/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /due date/i })).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — StatusBadge renders status label, not raw status string
  // -------------------------------------------------------------------------

  it("renders StatusBadge label for pending status (Watch) and in_progress (On Track)", () => {
    render(<WorkflowList items={ITEMS} />);
    const table = screen.getByRole("table");
    expect(within(table).getByText("Watch")).toBeInTheDocument();
    expect(within(table).getByText("On Track")).toBeInTheDocument();
    // raw status strings must not appear inside table rows
    expect(within(table).queryByText("pending")).not.toBeInTheDocument();
    expect(within(table).queryByText("in_progress")).not.toBeInTheDocument();
  });

  it.each([
    ["in_review", "Watch"],
    ["completed", "On Track"],
    ["overdue", "Urgent"],
    ["blocked", "Needs Attention"],
  ])("maps WorkflowStatus %s to badge label %s", (status, expectedLabel) => {
    render(
      <WorkflowList
        items={[{ ...ITEMS[0], id: "wfl-x", status: status as import("@/lib/status").WorkflowStatus }]}
      />
    );
    expect(within(screen.getByRole("table")).getByText(expectedLabel)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — owner role and due date columns are rendered
  // -------------------------------------------------------------------------

  it("renders the owner role for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("admissions officer")).toBeInTheDocument();
    expect(screen.getByText("registrar specialist")).toBeInTheDocument();
  });

  it("renders the due date for each workflow item", () => {
    render(<WorkflowList items={ITEMS} />);
    expect(screen.getByText("2025-09-15")).toBeInTheDocument();
    expect(screen.getByText("2025-09-10")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — filter by stage hides non-matching rows
  // -------------------------------------------------------------------------

  it("filters rows to only show the selected stage", async () => {
    render(<WorkflowList items={ITEMS} />);
    const stageSelect = screen.getByRole("combobox", { name: /filter by stage/i });
    await userEvent.selectOptions(stageSelect, "admissions");
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.queryByText("Khalid Al-Fadli")).not.toBeInTheDocument();
  });

  it("shows all rows when stage filter is reset to all", async () => {
    render(<WorkflowList items={ITEMS} />);
    const stageSelect = screen.getByRole("combobox", { name: /filter by stage/i });
    await userEvent.selectOptions(stageSelect, "admissions");
    await userEvent.selectOptions(stageSelect, "");
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.getByText("Khalid Al-Fadli")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — filter by status hides non-matching rows
  // -------------------------------------------------------------------------

  it("filters rows to only show the selected status", async () => {
    render(<WorkflowList items={ITEMS} />);
    const statusSelect = screen.getByRole("combobox", { name: /filter by status/i });
    await userEvent.selectOptions(statusSelect, "pending");
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.queryByText("Khalid Al-Fadli")).not.toBeInTheDocument();
  });

  it("shows all rows when status filter is reset to all", async () => {
    render(<WorkflowList items={ITEMS} />);
    const statusSelect = screen.getByRole("combobox", { name: /filter by status/i });
    await userEvent.selectOptions(statusSelect, "pending");
    await userEvent.selectOptions(statusSelect, "");
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.getByText("Khalid Al-Fadli")).toBeInTheDocument();
  });
});
