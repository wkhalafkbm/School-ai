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
];

describe("WorkflowActivityPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("fetches workflow items and renders them", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SEEDED_ITEMS,
      })
    );

    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText("admissions")).toBeInTheDocument();
    expect(screen.getByText("Sara Al-Rashidi")).toBeInTheDocument();
    expect(screen.getByText("Pathway recommendation approved by admissions officer")).toBeInTheDocument();
  });
});
