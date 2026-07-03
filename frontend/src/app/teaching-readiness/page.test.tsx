import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { act } from "react";
import TeachingReadinessPage from "./page";

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
    cohort_size: 30,
    aggregate_readiness_score: 72.5,
  },
  featured_course: {
    code: "CS101",
    name: "Introduction to Programming",
    rationale: "SLO-002 is the area of greatest concern for the incoming CS101 cohort; recommend a mid-semester review.",
    slo_trends: [
      {
        slo_code: "CS101-SLO1",
        description: "Students will be able to write basic Python programs",
        semesters: [
          { semester: "2023-Fall", proficiency_rate: 0.688 },
          { semester: "2024-Spring", proficiency_rate: 0.714 },
          { semester: "2024-Fall", proficiency_rate: 0.733 },
        ],
      },
      {
        slo_code: "CS101-SLO2",
        description: "Students will be able to trace algorithm execution",
        semesters: [
          { semester: "2023-Fall", proficiency_rate: 0.563 },
          { semester: "2024-Spring", proficiency_rate: 0.607 },
          { semester: "2024-Fall", proficiency_rate: 0.600 },
        ],
      },
    ],
  },
  assessment_failure_rates: [
    {
      slo_code: "CS101-SLO1",
      description: "Students will be able to write basic Python programs",
      failure_rate: 0.267,
      rules_engine_result: "pass",
    },
    {
      slo_code: "CS101-SLO2",
      description: "Students will be able to trace algorithm execution",
      failure_rate: 0.400,
      rules_engine_result: "fail",
    },
  ],
  faculty_workload: [
    {
      id: "fac-001",
      name: "Dr. Ahmed Al-Rashidi",
      department: "Computer Science",
      current_credits: 15,
      max_credits: 12,
      overloaded: true,
      status: "urgent",
    },
    {
      id: "fac-002",
      name: "Dr. Sara Al-Enezi",
      department: "Computer Science",
      current_credits: 9,
      max_credits: 15,
      overloaded: false,
      status: "on_track",
    },
  ],
  workload_threshold_result: "fail",
  workload_rationale:
    "Dr. Ahmed Al-Rashidi exceeds their credit cap and should be reassigned a section before the registration deadline.",
};

function renderResolvedPage(data: unknown = MOCK_PROFILE) {
  const result = render(<TeachingReadinessPage />);
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
// Cycle 1 — tracer bullet: streamed base+done renders stage header with
// health badge, and the "AI refining…" badge clears once done
// ---------------------------------------------------------------------------

describe("TeachingReadinessPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the Teaching Readiness heading and health status", () => {
    renderResolvedPage();

    expect(screen.getByText("Teaching Readiness")).toBeInTheDocument();
    expect(screen.getByText("Needs Attention")).toBeInTheDocument();
  });

  it("shows fallback text for both rationale fields immediately on base, and clears both refining badges on done", () => {
    render(<TeachingReadinessPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    expect(screen.getByText(/SLO-002 is the area of greatest concern/i)).toBeInTheDocument();
    expect(screen.getByText(/exceeds their credit cap/i)).toBeInTheDocument();
    expect(screen.getAllByText(/AI refining/i)).toHaveLength(2);

    act(() => {
      es.emit("done", {});
    });

    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
  });

  it("updates a rationale field independently as its field event arrives", () => {
    render(<TeachingReadinessPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    act(() => {
      es.emit("field", {
        path: "workload_rationale",
        value: "Live agent: reassign one section.",
      });
    });

    expect(screen.getByText("Live agent: reassign one section.")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — stage summary shows aggregate readiness score
  // -------------------------------------------------------------------------

  it("shows the aggregate readiness score", () => {
    renderResolvedPage();

    expect(screen.getByText(/72\.5/)).toBeInTheDocument();
  });

  it("shows the cohort size", () => {
    renderResolvedPage();

    expect(screen.getByText("30")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — SLO trend table shows CS101 and 3 semester columns
  // -------------------------------------------------------------------------

  it("shows the featured course code CS101", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/CS101/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows the three semester column headers", () => {
    renderResolvedPage();

    expect(screen.getByText("2023-Fall")).toBeInTheDocument();
    expect(screen.getByText("2024-Spring")).toBeInTheDocument();
    expect(screen.getByText("2024-Fall")).toBeInTheDocument();
  });

  it("shows SLO codes in the trend table", () => {
    renderResolvedPage();

    expect(screen.getAllByText("CS101-SLO1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("CS101-SLO2").length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — assessment failure rates per SLO shown
  // -------------------------------------------------------------------------

  it("shows assessment failure rates section", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/failure rate/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows failure rates for each SLO", () => {
    renderResolvedPage();

    expect(screen.getByText(/26\.7%|0\.267/)).toBeInTheDocument();
    expect(screen.getByText(/40\.0%|0\.400/)).toBeInTheDocument();
  });

  it("shows rules engine pass/fail results on failure rates", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/^pass$/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/^fail$/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — faculty workload table shows Dr. Ahmed as overloaded
  // -------------------------------------------------------------------------

  it("shows faculty workload section", () => {
    renderResolvedPage();

    expect(screen.getByText(/faculty workload/i)).toBeInTheDocument();
  });

  it("shows Dr. Ahmed Al-Rashidi in the workload table", () => {
    renderResolvedPage();

    expect(screen.getByText("Dr. Ahmed Al-Rashidi")).toBeInTheDocument();
  });

  it("flags Dr. Ahmed Al-Rashidi as overloaded with Urgent status", () => {
    renderResolvedPage();

    expect(screen.getByText("Urgent")).toBeInTheDocument();
  });

  it("shows workload threshold as fail", () => {
    renderResolvedPage();

    expect(screen.getByText(/workload threshold/i)).toBeInTheDocument();
    expect(screen.getAllByText(/^fail$/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — "Prepare Cohort Brief" button is present
  // -------------------------------------------------------------------------

  it("renders the Prepare Cohort Brief button", () => {
    renderResolvedPage();

    expect(
      screen.getByRole("button", { name: /prepare cohort brief/i })
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — clicking button opens approval modal
  // -------------------------------------------------------------------------

  it("clicking Prepare Cohort Brief opens an approval modal", () => {
    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /prepare cohort brief/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 8 — confirming fires one POST with department_chair owner_role
  // -------------------------------------------------------------------------

  it("confirming approval fires one workflow POST to /api/workflows", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK_PROFILE });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) });

    fireEvent.click(screen.getByRole("button", { name: /prepare cohort brief/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
    });
  });

  it("the POST targets /api/workflows with owner_role department_chair", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK_PROFILE });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) });

    fireEvent.click(screen.getByRole("button", { name: /prepare cohort brief/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
      const [url, opts] = postCalls[0];
      expect(url).toMatch(/\/api\/workflows/);
      const body = JSON.parse(opts.body as string);
      expect(body.owner_role).toBe("department_chair");
      expect(body.stage).toBe("teaching_readiness");
    });
  });

  // -------------------------------------------------------------------------
  // Cycle 9 — no "confidence" text anywhere on the page
  // -------------------------------------------------------------------------

  it("does not show confidence labels anywhere on the page", () => {
    renderResolvedPage();

    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 10 — no individual student name/ID (cohort-only view)
  // -------------------------------------------------------------------------

  it("does not show an individual student name or ID", () => {
    renderResolvedPage();

    expect(screen.queryByText(/stu-\d{3}/i)).not.toBeInTheDocument();
  });
});
