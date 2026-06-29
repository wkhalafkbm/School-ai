import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const MOCK_PROFILE = {
  stage_summary: {
    health: "opportunity",
    placement_rate: 0.87,
    median_time_to_placement: 3.2,
    employed_count: 142,
    total_graduates: 163,
  },
  student: {
    id: "stu-005",
    name: "Omar Al-Mutairi",
    program_name: "Business Administration",
    year_level: 4,
    gpa: 3.4,
    target_role: "Financial Analyst",
    target_industry: "Banking & Finance",
  },
  skill_gaps: [
    {
      skill: "Financial Modelling",
      current_level: "beginner",
      required_level: "intermediate",
      gap: true,
    },
    {
      skill: "Data Analysis (Excel/Python)",
      current_level: "none",
      required_level: "intermediate",
      gap: true,
    },
    {
      skill: "Business Communication",
      current_level: "intermediate",
      required_level: "intermediate",
      gap: false,
    },
  ],
  recommendations: {
    electives: [
      {
        course_code: "BA401",
        course_name: "Advanced Financial Modelling",
        rationale:
          "Directly addresses the identified gap in financial modelling skills required for target role",
      },
      {
        course_code: "DS201",
        course_name: "Data Analysis for Business",
        rationale:
          "Builds Python and Excel proficiency needed for analyst roles in banking",
      },
    ],
    internships: [
      {
        company: "National Bank of Kuwait",
        industry: "Banking & Finance",
        target_semester: "Spring 2025",
        rationale:
          "Aligns with target industry and provides hands-on financial analysis experience",
      },
    ],
  },
  alumni_mentor_match: {
    id: "alum-002",
    name: "Sara Al-Rashidi",
    current_role: "Senior Financial Analyst",
    current_company: "Kuwait Finance House",
    industry: "Banking & Finance",
    graduation_year: 2021,
    program_name: "Business Administration",
    match_basis:
      "Shared program, target industry, and graduation cohort alignment",
  },
  outcomes_feedback_loop: {
    description:
      "Career pathway recommendations are continuously refined using employment outcome data from 163 graduates. When alumni update their career status, the system recalibrates skill-gap weights and elective rankings for current students on the same pathway.",
    data_points: 163,
    last_updated: "2024-11-01",
  },
  career_pathway_recommendation: {
    actions: [
      {
        type: "skill_gap_elective",
        description:
          "Enrol in BA401 Advanced Financial Modelling next semester to close the primary skill gap",
        priority: "high",
      },
      {
        type: "internship_placement",
        description:
          "Apply for National Bank of Kuwait Spring 2025 internship before the December 15 deadline",
        priority: "high",
      },
      {
        type: "mentor_connection",
        description:
          "Connect with Sara Al-Rashidi for a career pathway conversation within the next two weeks",
        priority: "medium",
      },
    ],
    confidence: "High",
    rationale:
      "Omar's academic standing and program alignment strongly support the Financial Analyst pathway. Historical outcomes from 87% of similar graduates confirm placement within 3 months.",
  },
  career_advisor_item: null,
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

describe("CareerAlumniPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the Career & Alumni heading and health status", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/career.*alumni/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/opportunity/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — stage summary shows employment outcome metrics
  // -------------------------------------------------------------------------

  it("shows employment placement rate in stage summary", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/87%|placement.*rate/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows employed count and total graduates", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/142/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/163/).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — Omar Al-Mutairi student card
  // -------------------------------------------------------------------------

  it("shows Omar Al-Mutairi's name and program", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/Omar Al-Mutairi/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Business Administration/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows Omar's target role and industry", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/financial analyst/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/banking.*finance/i).length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — skill gaps relative to target career pathway
  // -------------------------------------------------------------------------

  it("renders the skill gap section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/skill gap/i).length).toBeGreaterThanOrEqual(1);
  });

  it("lists identified skill gaps", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/financial modelling/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/data analysis/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows current vs required skill level for gaps", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/beginner|intermediate/i).length).toBeGreaterThanOrEqual(2);
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — elective recommendations with rationale
  // -------------------------------------------------------------------------

  it("renders recommended electives section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/elective/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows elective course codes and names", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/BA401/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Advanced Financial Modelling/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/DS201/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows elective rationale", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByText(/directly addresses.*identified gap|financial modelling skills/i)
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — internship recommendations with rationale
  // -------------------------------------------------------------------------

  it("renders recommended internships section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/internship/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows internship company and target semester", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/National Bank of Kuwait/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Spring 2025/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows internship rationale", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByText(/aligns with target industry|hands-on financial analysis/i)
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — alumni mentor match with match basis
  // -------------------------------------------------------------------------

  it("renders alumni mentor match section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/alumni.*mentor|mentor.*match/i)).toBeInTheDocument();
  });

  it("shows mentor name and current role", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getAllByText(/Sara Al-Rashidi/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Senior Financial Analyst/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows match basis including shared program, industry, and graduation year", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByText(/shared program.*industry|graduation cohort/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/2021/)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 8 — outcomes feedback loop panel
  // -------------------------------------------------------------------------

  it("renders the outcomes feedback loop panel", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(screen.getByText(/outcomes.*feedback|feedback.*loop/i)).toBeInTheDocument();
  });

  it("explains how graduate employment data improves recommendations", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByText(/recalibrates.*skill-gap|employment outcome data/i)
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 9 — career pathway recommendation with confidence and rationale
  // -------------------------------------------------------------------------

  it("renders the career pathway recommendation section", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getAllByText(/career pathway recommendation/i).length
    ).toBeGreaterThanOrEqual(1);
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
      screen.getAllByText(/financial analyst pathway|historical outcomes.*87%/i).length
    ).toBeGreaterThanOrEqual(1);
  });

  it("lists career pathway actions with priority", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByText(/BA401.*Advanced Financial Modelling.*next semester|primary skill gap/i)
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 10 — "Recommend Career Path" button opens approval modal
  // -------------------------------------------------------------------------

  it("renders the Recommend Career Path button", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    expect(
      screen.getByRole("button", { name: /recommend career path/i })
    ).toBeInTheDocument();
  });

  it("clicking Recommend Career Path opens a modal", async () => {
    mockFetch(MOCK_PROFILE);
    const { default: Page } = await import("./page");
    render(await Page());

    fireEvent.click(screen.getByRole("button", { name: /recommend career path/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("confirming fires one workflow POST owned by career advisor", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => MOCK_PROFILE });
    vi.stubGlobal("fetch", fetchMock);

    const { default: Page } = await import("./page");
    render(await Page());

    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) });

    fireEvent.click(screen.getByRole("button", { name: /recommend career path/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: [string, RequestInit]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
      const body = JSON.parse(postCalls[0][1].body as string);
      expect(body.owner_role).toBe("career advisor");
      expect(body.stage).toBe("career_alumni");
      expect(body.student_id).toBe("stu-005");
    });
  });

  it("no student outreach POST fires without explicit approval", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => MOCK_PROFILE });
    vi.stubGlobal("fetch", fetchMock);

    const { default: Page } = await import("./page");
    render(await Page());

    fetchMock.mockClear();

    // Open modal but cancel — no POST should fire
    fireEvent.click(screen.getByRole("button", { name: /recommend career path/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: [string, RequestInit]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(0);
    });
  });
});
