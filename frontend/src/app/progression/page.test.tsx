import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

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
    rationale: "Student profile is well-documented and evidence supports a confident recommendation.",
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

function mockFetch(data: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => data })
  );
}

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: page renders stage header with health badge
// ---------------------------------------------------------------------------

describe("ProgressionPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the Progression heading and health status", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText("Progression")).toBeInTheDocument();
    expect(screen.getAllByText(/needs attention/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — stage summary shows on-track and at-risk counts
  // -------------------------------------------------------------------------

  it("shows on-track and at-risk graduation counts", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/on.track/i)).toBeInTheDocument();
    expect(screen.getByText(/at.risk/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — Noor Al-Hamad student profile card
  // -------------------------------------------------------------------------

  it("shows Noor Al-Hamad's name and program", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText("Noor Al-Hamad")).toBeInTheDocument();
    expect(screen.getByText("Computer Science")).toBeInTheDocument();
  });

  it("shows GPA value", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText("2.80")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — credit map shows earned vs required with substitutions
  // -------------------------------------------------------------------------

  it("renders the credit map section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/credit.*map|credits.*requirement/i)).toBeInTheDocument();
  });

  it("shows total credits earned and required", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/72.*132|72 of 132/i)).toBeInTheDocument();
  });

  it("highlights substituted courses", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/CS201.*Data Structures|substitut/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — bottleneck course with section capacity (institutional framing)
  // -------------------------------------------------------------------------

  it("renders the bottleneck course section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/bottleneck.*course|institutional.*constraint/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows CS302 Operating Systems as bottleneck", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/CS302/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Operating Systems/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows section capacity data", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/27.*30|27 of 30/i)).toBeInTheDocument();
  });

  it("shows institutional constraint note", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/90%.*capacity|limited seat availability/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — cohort delay forecast
  // -------------------------------------------------------------------------

  it("renders the cohort delay forecast", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/cohort.*delay|delay.*forecast/i)).toBeInTheDocument();
  });

  it("shows number of students at graduation risk", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    // text is split across <strong> elements — check for individual values
    expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("7").length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — below-target SLO signal linked to bottleneck course
  // -------------------------------------------------------------------------

  it("renders the SLO signal section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/SLO.*achievement|curriculum.*signal|CS302-SLO1/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows below-target proficiency rate", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/41%|below.*target/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 8 — graduation risk summary with confidence and rationale
  // -------------------------------------------------------------------------

  it("renders the graduation risk summary section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/graduation.*risk.*summary|graduation.*plan/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows confidence label", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  });

  it("shows rationale text", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByText(/well-documented.*evidence.*confident|confident.*recommendation/i)
    ).toBeInTheDocument();
  });

  it("lists graduation plan actions", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/credit.*deficit|summer enrollment/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/internship/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 9 — plan update workflow item (seeded, auto-triggered)
  // -------------------------------------------------------------------------

  it("renders the plan update item section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/graduation plan.*update|plan.*update/i)).toBeInTheDocument();
  });

  it("shows the seeded workflow item trigger", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/credits deficit detected/i)).toBeInTheDocument();
  });

  it("shows the department chair owner", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/Dr. Bader Al-Otaibi/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 10 — "Update Graduation Plan" button opens approval modal
  // -------------------------------------------------------------------------

  it("renders the Update Graduation Plan button", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByRole("button", { name: /update graduation plan/i })
    ).toBeInTheDocument();
  });

  it("clicking Update Graduation Plan opens a modal", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    fireEvent.click(screen.getByRole("button", { name: /update graduation plan/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("confirming fires one workflow POST to academic advisor", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => MOCK_PROFILE });
    vi.stubGlobal("fetch", fetchMock);

    const { default: Page } = await import("./page");
    render(await Page());

    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) });

    fireEvent.click(screen.getByRole("button", { name: /update graduation plan/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: [string, RequestInit]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
      const body = JSON.parse(postCalls[0][1].body as string);
      expect(body.owner_role).toBe("academic advisor");
      expect(body.stage).toBe("progression");
    });
  });
});
