import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { act } from "react";
import ProgressionPage from "./page";

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
    on_track_count: 2,
    at_risk_count: 5,
  },
  student: {
    id: "stu-004",
    name: "Noor Al-Hamad",
    program_name: "Computer Science",
    year_level: 3,
    gpa: 2.8,
  },
  credit_map: {
    total: { earned: 72, required: 132 },
    core: { earned: 33, required: 60 },
    math: { earned: 9, required: 12 },
    capstone: { completed: false, required: true },
    internship: { hours_completed: 0, hours_required: 240 },
    substitutions: [
      {
        substituted_course: "CS201 (Data Structures)",
        note: "Approved substitution — counted toward core elective requirement",
      },
    ],
  },
  bottleneck_course: {
    course_code: "CS302",
    course_name: "Operating Systems",
    section_capacity: 30,
    section_enrolled: 27,
    fill_rate: 0.9,
    constraint_type: "institutional",
    constraint_note: "Section at 90% capacity — limited seat availability delays graduation timeline",
  },
  cohort_delay_forecast: {
    students_at_risk: 5,
    total_cohort: 7,
  },
  bottleneck_slo_signal: {
    slo_code: "CS302-SLO1",
    description: "Students will explain process scheduling algorithms and memory management strategies",
    proficiency_rate: 0.41,
    cohort_size: 27,
    target_rate: 0.7,
    below_target: true,
  },
  graduation_risk_summary: {
    actions: [
      {
        type: "credit_deficit_plan",
        description: "Develop a revised four-year plan addressing the 12-credit deficit through summer enrollment or credit overload",
        priority: "high",
      },
      {
        type: "bottleneck_course_priority",
        description: "Prioritize CS302 Operating Systems enrollment next semester before section capacity reaches limit",
        priority: "high",
      },
      {
        type: "internship_planning",
        description: "Begin internship placement process to complete the 240-hour requirement ahead of projected graduation",
        priority: "medium",
      },
    ],
    confidence: "High",
    rationale: "Student profile is **well-documented** and evidence supports a confident recommendation.",
  },
  plan_update_item: {
    id: "wfl-004",
    trigger: "Credits deficit detected",
    owner_name: "Dr. Bader Al-Otaibi",
    owner_role: "department chair",
    status: "in_review",
    created_date: "2024-10-22",
  },
};

function renderResolvedPage(data: unknown = MOCK_PROFILE) {
  const result = render(<ProgressionPage />);
  const es = StubEventSource.instances[StubEventSource.instances.length - 1];

  act(() => {
    es.emit("base", data);
  });
  act(() => {
    es.emit("done", {});
  });

  return result;
}

/** The plan the weekly calendar fetches for itself (#84). */
const MOCK_PLAN = {
  student_id: "stu-004",
  student_name: "Noor Al-Hamad",
  terms: [
    {
      term: "2024-Fall",
      is_current: true,
      source: "enrollment",
      classes: [
        {
          course_code: "CS302",
          course_name: "Operating Systems",
          section_code: "CS302-01",
          days: ["Sun", "Tue"],
          start_time: "11:00",
          end_time: "12:15",
          room: "B107",
          credits: 3,
        },
      ],
    },
  ],
};

beforeEach(() => {
  StubEventSource.instances = [];
  vi.stubGlobal("EventSource", StubEventSource);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => MOCK_PLAN })
  );
});

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: streamed base+done renders stage header with
// health badge, and the "AI refining…" badge clears once done
// ---------------------------------------------------------------------------

describe("ProgressionPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the Progression heading and health status", () => {
    renderResolvedPage();

    expect(screen.getByText("Progression")).toBeInTheDocument();
    expect(screen.getAllByText(/needs attention/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows fallback rationale immediately on base, and clears the refining badge on done", () => {
    render(<ProgressionPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    expect(screen.getByText(/well-documented/i)).toBeInTheDocument();
    expect(screen.getAllByText(/AI refining/i)).toHaveLength(1);

    act(() => {
      es.emit("done", {});
    });

    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
  });

  it("updates the rationale independently as its field event arrives", () => {
    render(<ProgressionPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    act(() => {
      es.emit("field", {
        path: "graduation_risk_summary.rationale",
        value: "Live agent: graduation on track with plan update.",
      });
    });

    expect(
      screen.getByText("Live agent: graduation on track with plan update.")
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — stage summary shows on-track and at-risk counts
  // -------------------------------------------------------------------------

  it("shows on-track and at-risk graduation counts", () => {
    renderResolvedPage();

    expect(screen.getByText(/on.track/i)).toBeInTheDocument();
    expect(screen.getByText(/at.risk/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — Noor Al-Hamad student profile card
  // -------------------------------------------------------------------------

  it("shows Noor Al-Hamad's name and program", () => {
    renderResolvedPage();

    expect(screen.getByText("Noor Al-Hamad")).toBeInTheDocument();
    expect(screen.getByText("Computer Science")).toBeInTheDocument();
  });

  it("shows GPA value", () => {
    renderResolvedPage();

    expect(screen.getByText("2.80")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — credit map shows earned vs required with substitutions
  // -------------------------------------------------------------------------

  it("renders the credit map section", () => {
    renderResolvedPage();

    expect(screen.getByText(/credit.*map|credits.*requirement/i)).toBeInTheDocument();
  });

  it("shows total credits earned and required", () => {
    renderResolvedPage();

    expect(screen.getByText(/72.*132|72 of 132/i)).toBeInTheDocument();
  });

  it("highlights substituted courses", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/CS201.*Data Structures|substitut/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — bottleneck course with section capacity (institutional framing)
  // -------------------------------------------------------------------------

  it("renders the bottleneck course section", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/bottleneck.*course|institutional.*constraint/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows CS302 Operating Systems as bottleneck", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/CS302/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Operating Systems/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows section capacity data", () => {
    renderResolvedPage();

    expect(screen.getByText(/27.*30|27 of 30/i)).toBeInTheDocument();
  });

  it("shows institutional constraint note", () => {
    renderResolvedPage();

    expect(screen.getByText(/90%.*capacity|limited seat availability/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — cohort delay forecast
  // -------------------------------------------------------------------------

  it("renders the cohort delay forecast", () => {
    renderResolvedPage();

    expect(screen.getByText(/cohort.*delay|delay.*forecast/i)).toBeInTheDocument();
  });

  it("shows number of students at graduation risk", () => {
    renderResolvedPage();

    // text is split across <strong> elements — check for individual values
    expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("7").length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — below-target SLO signal linked to bottleneck course
  // -------------------------------------------------------------------------

  it("renders the SLO signal section", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/SLO.*achievement|curriculum.*signal|CS302-SLO1/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows below-target proficiency rate", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/41%|below.*target/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 8 — graduation risk summary with confidence and rationale
  // -------------------------------------------------------------------------

  it("renders the graduation risk summary section", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/graduation.*risk.*summary|graduation.*plan/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows confidence label", () => {
    renderResolvedPage();

    expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  });

  it("shows rationale text", () => {
    const { container } = renderResolvedPage();

    expect(container.textContent).toMatch(
      /well-documented.*evidence.*confident|confident.*recommendation/i
    );
  });

  it("renders graduation risk summary rationale markdown as HTML, not raw syntax", () => {
    const { container } = renderResolvedPage();

    const strongEls = Array.from(container.querySelectorAll("strong")).filter(
      (el) => el.textContent === "well-documented"
    );
    expect(strongEls).toHaveLength(1);
    expect(container.textContent).not.toContain("**well-documented**");
  });

  it("lists graduation plan actions", () => {
    renderResolvedPage();

    expect(screen.getAllByText(/credit.*deficit|summer enrollment/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/internship/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 9 — plan update workflow item (seeded, auto-triggered)
  // -------------------------------------------------------------------------

  it("renders the plan update item section", () => {
    renderResolvedPage();

    expect(screen.getByText(/graduation plan.*update|plan.*update/i)).toBeInTheDocument();
  });

  it("shows the seeded workflow item trigger", () => {
    renderResolvedPage();

    expect(screen.getByText(/credits deficit detected/i)).toBeInTheDocument();
  });

  it("shows the department chair owner", () => {
    renderResolvedPage();

    expect(screen.getByText(/Dr. Bader Al-Otaibi/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 10 — "Update Graduation Plan" button opens approval modal
  // -------------------------------------------------------------------------

  it("renders the Update Graduation Plan button", () => {
    renderResolvedPage();

    expect(
      screen.getByRole("button", { name: /update graduation plan/i })
    ).toBeInTheDocument();
  });

  it("clicking Update Graduation Plan opens a modal", () => {
    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /update graduation plan/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("confirming fires one workflow POST to academic advisor", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /update graduation plan/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
      const body = JSON.parse(postCalls[0][1].body as string);
      expect(body.owner_role).toBe("academic advisor");
      expect(body.stage).toBe("progression");
    });
  });

  // -------------------------------------------------------------------------
  // Issue #84 — the weekly calendar sits between the Graduation Risk Summary
  // and the Graduation Plan Update panel, and fails on its own
  // -------------------------------------------------------------------------

  it("renders the weekly calendar below the risk summary and above the plan update", async () => {
    const { container } = renderResolvedPage();
    await screen.findByRole("table", { name: /weekly class schedule/i });

    const riskEl = container.querySelector("[data-testid='graduation-risk-summary']");
    const calendarEl = container.querySelector("[data-testid='weekly-calendar']");
    const planEl = container.querySelector("[data-testid='plan-update-item']");
    expect(riskEl).not.toBeNull();
    expect(calendarEl).not.toBeNull();
    expect(planEl).not.toBeNull();

    const all = Array.from(container.querySelectorAll("*"));
    expect(all.indexOf(riskEl!)).toBeLessThan(all.indexOf(calendarEl!));
    expect(all.indexOf(calendarEl!)).toBeLessThan(all.indexOf(planEl!));
  });

  it("keeps the rest of the page intact when the calendar's endpoint fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    renderResolvedPage();

    expect(
      await screen.findByText(/couldn't load the class schedule/i)
    ).toBeInTheDocument();
    expect(screen.getByText("Noor Al-Hamad")).toBeInTheDocument();
    expect(screen.getByText("Graduation Risk Summary")).toBeInTheDocument();
    expect(screen.getByText("Graduation Plan Update")).toBeInTheDocument();
  });
});
