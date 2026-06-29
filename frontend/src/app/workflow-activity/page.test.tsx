import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Cycle 3 — WorkflowActivityPage fetches /api/workflows and renders items
// ---------------------------------------------------------------------------

const SEEDED_ITEMS = [
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
    trigger: "Financial hold cleared by registrar",
    owner_name: "Khalid Al-Fadli",
    owner_role: "registrar specialist",
    status: "in_progress",
    description: "Enrollment unblocked after hold resolution.",
    due_date: "2025-09-10",
  },
];

describe("WorkflowActivityPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("fetches workflow items and renders them in a table", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SEEDED_ITEMS,
      })
    );

    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.getByText("admissions officer")).toBeInTheDocument();
    expect(screen.getByText("2025-09-15")).toBeInTheDocument();
    expect(screen.getByText("Watch")).toBeInTheDocument();
  });

  it("renders the page heading", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SEEDED_ITEMS,
      })
    );

    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByRole("heading", { name: /workflow activity/i })).toBeInTheDocument();
  });

  it("renders items from multiple stages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SEEDED_ITEMS,
      })
    );

    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText("Pathway recommendation approved by admissions officer")).toBeInTheDocument();
    expect(screen.getByText("Financial hold cleared by registrar")).toBeInTheDocument();
    expect(screen.getByText("Khalid Al-Fadli")).toBeInTheDocument();
  });
});
