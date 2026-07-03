import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { act } from "react";
import EnrollmentPage from "./page";

class StubEventSource {
  static instances: StubEventSource[] = [];
  listeners: Record<string, ((event: { data: string }) => void)[]> = {};
  closed = false;
  onerror: ((event: unknown) => void) | null = null;

  constructor(public url: string) {
    StubEventSource.instances.push(this);
  }

  addEventListener(type: string, cb: (event: { data: string }) => void) {
    (this.listeners[type] ??= []).push(cb);
  }

  close() {
    this.closed = true;
  }

  emit(type: string, data: unknown) {
    for (const cb of this.listeners[type] ?? []) {
      cb({ data: JSON.stringify(data) });
    }
  }
}

const MOCK_PROFILE = {
  stage_summary: {
    health: "needs_attention",
    registration_complete: 28,
    registration_pending: 12,
    registration_blocked: 5,
  },
  student: {
    id: "stu-002",
    name: "Mariam Al-Kandari",
    program_name: "Information Systems",
    year_level: 1,
    gpa: 3.1,
    onboarding_tasks: [
      { task_name: "Submit Photo ID Copy", category: "documentation", completed: true, due_date: "2024-09-15" },
      { task_name: "Complete Medical Form", category: "health", completed: false, due_date: "2024-09-15" },
      { task_name: "Attend Orientation Session", category: "orientation", completed: true, due_date: "2024-09-05" },
      { task_name: "Register for Campus ID Card", category: "administration", completed: false, due_date: "2024-09-20" },
      { task_name: "Set Up University Email", category: "IT", completed: true, due_date: "2024-09-10" },
      { task_name: "Complete Financial Aid Forms", category: "financial", completed: false, due_date: "2024-09-25" },
      { task_name: "Sign Code of Conduct", category: "administration", completed: true, due_date: "2024-09-10" },
    ],
  },
  registration_blockers: [
    { type: "financial_aid_hold", description: "Pending tuition payment for 2024-Fall semester", rules_engine_result: "fail" },
    { type: "prerequisite", description: "IS201 requires completion of CS101 (min. grade D)", rules_engine_result: "fail" },
    { type: "credit_limit", description: "15 credits exceeds the 12-credit limit for first-year students", rules_engine_result: "fail" },
    { type: "conflict", description: "CS101-01 (Sun/Tue 09:00–10:15) conflicts with MATH101-01 (Sun/Tue/Thu 09:00–09:50)", rules_engine_result: "fail" },
    { type: "admin_hold", description: "Missing registrar signature on change-of-major form", rules_engine_result: "fail" },
    { type: "missing_document", description: "Required document not submitted: Complete Medical Form", rules_engine_result: "fail" },
  ],
  suggested_schedule: {
    sections: [
      { course: "CS101", section: "CS101-01", days: ["Sun", "Tue"], time: "09:00–10:15", room: "B101" },
      { course: "MATH101", section: "MATH101-02", days: ["Mon", "Wed"], time: "09:00–10:15", room: "A202" },
      { course: "IS201", section: "IS201-01", days: ["Mon", "Wed"], time: "09:00–10:15", room: "D101", note: "Pending prerequisite clearance" },
    ],
    note: "Switch MATH101 from section 01 (Sun/Tue) to **section 02 (Mon/Wed)** to resolve the time conflict with CS101.",
  },
};

function renderResolvedPage(data: unknown = MOCK_PROFILE) {
  const result = render(<EnrollmentPage />);
  const es = StubEventSource.instances[StubEventSource.instances.length - 1];

  act(() => {
    es.emit("base", data);
  });
  act(() => {
    es.emit("done", {});
  });

  return result;
}

beforeEach(() => {
  StubEventSource.instances = [];
  vi.stubGlobal("EventSource", StubEventSource);
});

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: page renders stage header with health
// ---------------------------------------------------------------------------

describe("EnrollmentPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the Enrollment heading and health status", () => {
    renderResolvedPage();

    expect(screen.getByText("Enrollment")).toBeInTheDocument();
    expect(screen.getByText("Needs Attention")).toBeInTheDocument();
  });

  it("shows fallback note immediately on base, and clears the refining badge on done", () => {
    render(<EnrollmentPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    expect(screen.getByText(/Switch MATH101 from section 01/i)).toBeInTheDocument();
    expect(screen.getByText(/AI refining/i)).toBeInTheDocument();

    act(() => {
      es.emit("done", {});
    });

    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
  });

  it("updates the suggested schedule note independently as its field event arrives", () => {
    render(<EnrollmentPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    act(() => {
      es.emit("field", {
        path: "suggested_schedule.note",
        value: "Live agent: switch MATH101 to section 02.",
      });
    });

    expect(screen.getByText("Live agent: switch MATH101 to section 02.")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — stage summary shows registration counts
  // -------------------------------------------------------------------------

  it("shows registration complete, pending, and blocked counts", () => {
    renderResolvedPage();

    expect(screen.getByText("28")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — student card shows Mariam with onboarding tasks
  // -------------------------------------------------------------------------

  it("shows Mariam Al-Kandari's name and program", () => {
    renderResolvedPage();

    expect(screen.getByText("Mariam Al-Kandari")).toBeInTheDocument();
    expect(screen.getByText("Information Systems")).toBeInTheDocument();
  });

  it("renders onboarding tasks with completion indicators", () => {
    renderResolvedPage();

    expect(screen.getByText("Submit Photo ID Copy")).toBeInTheDocument();
    expect(screen.getByText("Complete Medical Form")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — registration blockers listed with types
  // -------------------------------------------------------------------------

  it("lists all six registration blocker types", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/financial.?aid.?hold/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/prerequisite/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/credit.?limit/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/conflict/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/admin.?hold/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/missing.?document/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows blocker descriptions", () => {
    renderResolvedPage();

    expect(screen.getByText(/Pending tuition payment/i)).toBeInTheDocument();
    expect(screen.getByText(/IS201 requires completion of CS101/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — rules engine results shown, no "confidence" text
  // -------------------------------------------------------------------------

  it("shows rules engine result labels", () => {
    renderResolvedPage();

    const failLabels = screen.getAllByText(/^fail$/i);
    expect(failLabels.length).toBeGreaterThanOrEqual(6);
  });

  it("does not show confidence labels on blockers", () => {
    renderResolvedPage();

    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — suggested schedule displayed before the action button
  // -------------------------------------------------------------------------

  it("renders the suggested schedule before the action button", () => {
    const { container } = renderResolvedPage();

    const scheduleEl = container.querySelector("[data-testid='suggested-schedule']");
    const actionEl = container.querySelector("[data-testid='validate-schedule-btn']");
    expect(scheduleEl).not.toBeNull();
    expect(actionEl).not.toBeNull();

    const all = Array.from(container.querySelectorAll("*"));
    expect(all.indexOf(scheduleEl!)).toBeLessThan(all.indexOf(actionEl!));
  });

  it("shows schedule section codes and note", () => {
    renderResolvedPage();

    expect(screen.getByText("MATH101-02")).toBeInTheDocument();
    expect(screen.getByText(/Switch MATH101 from section 01/i)).toBeInTheDocument();
  });

  it("renders suggested schedule note markdown as HTML, not raw syntax", () => {
    const { container } = renderResolvedPage();

    const strongEls = Array.from(container.querySelectorAll("strong")).filter(
      (el) => el.textContent === "section 02 (Mon/Wed)"
    );
    expect(strongEls).toHaveLength(1);
    expect(container.textContent).not.toContain("**section 02 (Mon/Wed)**");
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — "Validate Schedule" button opens approval modal
  // -------------------------------------------------------------------------

  it("renders the Validate Schedule button", () => {
    renderResolvedPage();

    expect(
      screen.getByRole("button", { name: /validate schedule/i })
    ).toBeInTheDocument();
  });

  it("clicking Validate Schedule opens an approval modal", () => {
    renderResolvedPage();

    const btn = screen.getByRole("button", { name: /validate schedule/i });
    fireEvent.click(btn);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 8 — confirming approval fires 3 POST /api/workflows calls
  // -------------------------------------------------------------------------

  it("confirming approval fires three workflow POST requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    const btn = screen.getByRole("button", { name: /validate schedule/i });
    fireEvent.click(btn);
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(3);
    });
  });

  it("the three POST calls target distinct owners", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /validate schedule/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postBodies = fetchMock.mock.calls
        .filter(([, opts]: any[]) => opts?.method === "POST")
        .map(([, opts]: any[]) => JSON.parse(opts.body as string));
      expect(postBodies).toHaveLength(3);
      const roles = postBodies.map((b: { owner_role: string }) => b.owner_role);
      const uniqueRoles = new Set(roles);
      expect(uniqueRoles.size).toBe(3);
    });
  });
});
