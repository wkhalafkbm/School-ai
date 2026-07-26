/**
 * Integration test for AC 7: items created by EnrollmentActions appear in
 * Workflow Activity. Renders both pages sequentially within the same test so
 * the exact payloads sent by the enrollment page are what the workflow
 * activity page receives and displays.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, within, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { act } from "react";

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
    ],
  },
  registration_blockers: [
    { type: "financial_aid_hold", description: "Pending tuition payment", rules_engine_result: "fail" },
  ],
  suggested_schedule: {
    sections: [{ course: "CS101", section: "CS101-01", days: ["Sun", "Tue"], time: "09:00–10:15" }],
    note: "Switch MATH101 to section 02.",
  },
};

describe("Enrollment → Workflow Activity integration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("items posted on enrollment approval appear in Workflow Activity", async () => {
    // --- Phase 1: render Enrollment page and capture what gets POSTed ---

    const postedBodies: Record<string, string>[] = [];

    const fetchMock = vi.fn(
      async (url: string, opts?: RequestInit): Promise<{ ok: boolean; json: () => Promise<unknown> }> => {
        if (opts?.method === "POST") {
          postedBodies.push(JSON.parse(opts.body as string));
          return { ok: true, json: async () => ({ id: `wfl-new-${postedBodies.length}` }) };
        }
        return { ok: true, json: async () => ({}) };
      }
    );

    vi.stubGlobal("fetch", fetchMock);
    StubEventSource.instances = [];
    vi.stubGlobal("EventSource", StubEventSource);

    const { default: EnrollmentPage } = await import("./page");
    render(<EnrollmentPage />);
    const es = StubEventSource.instances[0];
    act(() => {
      es.emit("base", MOCK_PROFILE);
    });
    act(() => {
      es.emit("done", {});
    });

    fireEvent.click(screen.getByRole("button", { name: /validate schedule/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => expect(postedBodies).toHaveLength(3));

    // --- Phase 2: render Workflow Activity with those exact items ---

    cleanup();

    const workflowItems = postedBodies.map((body, i) => ({
      id: `wfl-new-${i + 1}`,
      stage: body.stage,
      trigger: body.trigger,
      owner_name: body.owner_name,
      owner_role: body.owner_role,
      status: body.status,
      description: body.description,
      due_date: null,
    }));

    fetchMock.mockImplementation(async () => ({
      ok: true,
      json: async () => workflowItems,
    }));

    const { default: WorkflowActivityPage } = await import(
      "../workflow-activity/page"
    );
    render(await WorkflowActivityPage());

    // Every trigger sent by EnrollmentActions must be visible in Workflow Activity
    for (const body of postedBodies) {
      expect(screen.getByText(body.trigger)).toBeInTheDocument();
    }

    // All three owner roles must be visible (registrar, financial aid, document verification)
    const renderedRoles = postedBodies.map((b) => b.owner_name);
    for (const name of renderedRoles) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }

    // All items are enrollment stage — scope to table rows to exclude filter
    // dropdown, which lists the raw stage id rather than its label
    const table = screen.getByRole("table");
    const stageLabels = within(table).getAllByText("Enrollment");
    expect(stageLabels).toHaveLength(3);
  });
});
