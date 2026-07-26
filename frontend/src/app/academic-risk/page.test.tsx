import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { act } from "react";
import AcademicRiskPage from "./page";

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
    health: "urgent",
    watch_count: 0,
    needs_attention_count: 2,
    urgent_count: 1,
  },
  student: {
    id: "stu-003",
    name: "Fahad Al-Ajmi",
    program_name: "Computer Science",
    year_level: 2,
    gpa: 1.9,
    academic_failure_risk: "urgent",
    attrition_risk: "urgent",
  },
  gpa_trend: {
    series: [
      { term: "2023-Fall", term_gpa: 2.4, cumulative_gpa: 2.4 },
      { term: "2024-Spring", term_gpa: 1.9, cumulative_gpa: 2.15 },
      { term: "2024-Fall", term_gpa: 1.4, cumulative_gpa: 1.9 },
    ],
    status: "urgent",
    reason:
      "GPA declined 1.90 → 1.40 in 2024-Fall (sharp drop); GPA declined 2.40 → 1.90 → 1.40 across 2023-Fall–2024-Fall, a total of 1.00 over two terms (sustained decline)",
    rules_fired: ["sharp_drop", "sustained_decline"],
    workflow_item: {
      id: "wft-stu-003-2024-Fall",
      status: "pending",
      created_date: "2026-07-26",
    },
  },
  cohort_slo_pattern: [
    {
      slo_code: "CS201-SLO1",
      description: "Students will implement common data structures in code",
      student_score: 38.0,
      proficient: false,
      peers_underperforming: 12,
      cohort_size: 28,
    },
    {
      slo_code: "CS201-SLO2",
      description: "Students will analyze time and space complexity using Big-O notation",
      student_score: 32.0,
      proficient: false,
      peers_underperforming: 14,
      cohort_size: 28,
    },
    {
      slo_code: "CS201-SLO3",
      description: "Students will select appropriate data structures for given problem scenarios",
      student_score: 45.0,
      proficient: false,
      peers_underperforming: 10,
      cohort_size: 28,
    },
  ],
  intervention_plan: {
    actions: [
      {
        type: "tutoring_referral",
        description: "Refer Fahad to peer tutoring for CS201 data structures and algorithms",
        priority: "high",
      },
      {
        type: "advisor_meeting",
        description: "Schedule weekly faculty advisor check-in for the remainder of the semester",
        priority: "high",
      },
      {
        type: "lms_engagement_alert",
        description: "Enable LMS automated engagement alerts for Fahad's three active courses",
        priority: "medium",
      },
    ],
    confidence: "High",
    rationale:
      "Student engagement signals indicate an **academic support need**. Intervention is recommended based on strong corroborating evidence.",
  },
  sponsor_escalation: {
    id: "wfl-006",
    trigger: "LMS risk flag raised",
    owner_name: "Noura Al-Hamdan",
    owner_role: "faculty advisor",
    status: "pending",
    created_date: "2024-10-17",
  },
  engagement_assessment: {
    rationale:
      "Fahad shows **low LMS login frequency** and a below-average assignment submission rate over the last 30 days. Early outreach is recommended before engagement drops further.",
  },
  support_assessment: {
    rationale:
      "Fahad's current standing warrants **continued case oversight**. Coordinate with the assigned advisor to track progress toward recovery.",
  },
};

function renderResolvedPage(data: unknown = MOCK_PROFILE) {
  const result = render(<AcademicRiskPage />);
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

describe("AcademicRiskPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the Academic Risk heading and health status", () => {
    renderResolvedPage();

    expect(screen.getByText("Academic Risk")).toBeInTheDocument();
    expect(screen.getAllByText("Urgent").length).toBeGreaterThanOrEqual(1);
  });

  it("shows fallback text for all 3 rationale fields immediately on base, and clears all 3 refining badges on done", () => {
    render(<AcademicRiskPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    expect(
      screen.getByText(/Student engagement signals indicate an/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Fahad shows/i)).toBeInTheDocument();
    expect(screen.getByText(/Fahad's current standing warrants/i)).toBeInTheDocument();
    expect(screen.getAllByText(/AI refining/i)).toHaveLength(3);

    act(() => {
      es.emit("done", {});
    });

    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
  });

  it("updates a rationale field independently as its field event arrives", () => {
    render(<AcademicRiskPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    act(() => {
      es.emit("field", {
        path: "engagement_assessment.rationale",
        value: "Live agent: urgent outreach needed.",
      });
    });

    expect(screen.getByText("Live agent: urgent outreach needed.")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — stage summary shows risk-level counts
  // -------------------------------------------------------------------------

  it("shows watch, needs attention, and urgent counts", () => {
    renderResolvedPage();

    expect(screen.getByText(/watch:/i)).toBeInTheDocument();
    expect(screen.getByText(/needs attention:/i)).toBeInTheDocument();
    expect(screen.getByText(/urgent:/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — Fahad's card shows two separate risk indicators
  // -------------------------------------------------------------------------

  it("shows Fahad Al-Ajmi's name and program", () => {
    renderResolvedPage();

    expect(screen.getByText("Fahad Al-Ajmi")).toBeInTheDocument();
    expect(screen.getByText("Computer Science")).toBeInTheDocument();
  });

  it("shows GPA value", () => {
    renderResolvedPage();

    expect(screen.getByText("1.90")).toBeInTheDocument();
  });

  it("shows academic failure risk indicator", () => {
    renderResolvedPage();

    expect(screen.getByText(/academic failure risk/i)).toBeInTheDocument();
  });

  it("shows attrition risk indicator", () => {
    renderResolvedPage();

    expect(screen.getByText(/attrition risk/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — cohort SLO pattern panel shows peers underperforming
  // -------------------------------------------------------------------------

  it("renders the cohort SLO pattern panel", () => {
    renderResolvedPage();

    expect(screen.getByText(/cohort slo pattern/i)).toBeInTheDocument();
  });

  it("shows SLO codes from the pattern", () => {
    renderResolvedPage();

    expect(screen.getByText("CS201-SLO1")).toBeInTheDocument();
    expect(screen.getByText("CS201-SLO2")).toBeInTheDocument();
  });

  it("shows peers underperforming counts", () => {
    renderResolvedPage();

    expect(screen.getByText(/12.*28|12 of 28/i)).toBeInTheDocument();
    expect(screen.getByText(/14.*28|14 of 28/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 4b — engagement assessment rationale renders as markdown
  // -------------------------------------------------------------------------

  it("renders engagement assessment rationale markdown as HTML, not raw syntax", () => {
    const { container } = renderResolvedPage();

    const strongEls = Array.from(container.querySelectorAll("strong")).filter(
      (el) => el.textContent === "low LMS login frequency"
    );
    expect(strongEls).toHaveLength(1);
    expect(container.textContent).not.toContain("**low LMS login frequency**");
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — intervention plan shows confidence label and rationale
  // -------------------------------------------------------------------------

  it("renders the intervention plan section", () => {
    renderResolvedPage();

    expect(screen.getByText(/intervention plan/i)).toBeInTheDocument();
  });

  it("shows confidence label", () => {
    renderResolvedPage();

    expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  });

  it("shows rationale text", () => {
    const { container } = renderResolvedPage();

    expect(container.textContent).toMatch(
      /Student engagement signals indicate an academic support need/i
    );
  });

  it("renders intervention plan rationale markdown as HTML, not raw syntax", () => {
    const { container } = renderResolvedPage();

    const strongEls = Array.from(container.querySelectorAll("strong")).filter(
      (el) => el.textContent === "academic support need"
    );
    expect(strongEls).toHaveLength(1);
    expect(container.textContent).not.toContain("**academic support need**");
  });

  it("lists intervention actions", () => {
    renderResolvedPage();

    expect(screen.getByText(/peer tutoring/i)).toBeInTheDocument();
    expect(screen.getByText(/advisor check-in/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — sponsor escalation item is present (seeded, auto-triggered)
  // -------------------------------------------------------------------------

  it("renders the sponsor escalation section", () => {
    renderResolvedPage();

    expect(screen.getByText(/sponsor escalation/i)).toBeInTheDocument();
  });

  it("shows the escalation trigger text", () => {
    renderResolvedPage();

    expect(screen.getByText(/LMS risk flag raised/i)).toBeInTheDocument();
  });

  it("shows the escalation owner name", () => {
    renderResolvedPage();

    expect(screen.getByText(/Noura Al-Hamdan/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 6b — support assessment rationale renders as markdown
  // -------------------------------------------------------------------------

  it("renders support assessment rationale markdown as HTML, not raw syntax", () => {
    const { container } = renderResolvedPage();

    const strongEls = Array.from(container.querySelectorAll("strong")).filter(
      (el) => el.textContent === "continued case oversight"
    );
    expect(strongEls).toHaveLength(1);
    expect(container.textContent).not.toContain("**continued case oversight**");
  });

  // -------------------------------------------------------------------------
  // Cycle 7 — "Approve Intervention" button opens approval modal
  // -------------------------------------------------------------------------

  it("renders the Approve Intervention button", () => {
    renderResolvedPage();

    expect(
      screen.getByRole("button", { name: /approve intervention/i })
    ).toBeInTheDocument();
  });

  it("clicking Approve Intervention opens a modal", () => {
    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /approve intervention/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 8 — confirming approval fires POST /api/workflows to student affairs
  // -------------------------------------------------------------------------

  it("confirming approval fires one workflow POST request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /approve intervention/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
    });
  });

  // -------------------------------------------------------------------------
  // Issue #65, cycle 1 — the Snapshot | Trend toggle, defaulting to Snapshot
  // -------------------------------------------------------------------------

  it("renders a Snapshot | Trend toggle", () => {
    renderResolvedPage();

    expect(screen.getByRole("button", { name: "Snapshot" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trend" })).toBeInTheDocument();
  });

  it("defaults to Snapshot: the risk badges show and the GPA panel does not", () => {
    renderResolvedPage();

    expect(screen.getByRole("button", { name: "Snapshot" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByText(/academic failure risk/i)).toBeInTheDocument();
    expect(screen.getByText(/attrition risk/i)).toBeInTheDocument();
    expect(screen.queryByText(/gpa by semester/i)).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Issue #65, cycle 2 — Trend mode replaces the risk-badge column, and the
  // toggle switches back
  // -------------------------------------------------------------------------

  it("switching to Trend replaces the risk badges with the trend status and reason", () => {
    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: "Trend" }));

    expect(screen.queryByText(/academic failure risk/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/attrition risk/i)).not.toBeInTheDocument();
    expect(screen.getByText("GPA Trend")).toBeInTheDocument();
    expect(
      screen.getByText(/GPA declined 1\.90 → 1\.40 in 2024-Fall/)
    ).toBeInTheDocument();
  });

  it("switching back to Snapshot restores the risk badges and hides the GPA panel", () => {
    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: "Trend" }));
    fireEvent.click(screen.getByRole("button", { name: "Snapshot" }));

    expect(screen.getByText(/academic failure risk/i)).toBeInTheDocument();
    expect(screen.getByText(/attrition risk/i)).toBeInTheDocument();
    expect(screen.queryByText(/gpa by semester/i)).not.toBeInTheDocument();
  });

  it("keeps the surrounding context visible in both modes", () => {
    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: "Trend" }));

    expect(screen.getByText(/cohort slo pattern/i)).toBeInTheDocument();
    expect(screen.getByText(/intervention plan/i)).toBeInTheDocument();
    expect(screen.getByText(/sponsor escalation/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Issue #65, cycle 3 — the GPA by Semester panel
  // -------------------------------------------------------------------------

  function renderTrendMode(data: unknown = MOCK_PROFILE) {
    const result = renderResolvedPage(data);
    fireEvent.click(screen.getByRole("button", { name: "Trend" }));
    return result;
  }

  it("shows the GPA by Semester panel only in Trend mode", () => {
    renderTrendMode();

    expect(screen.getByText(/gpa by semester/i)).toBeInTheDocument();
  });

  it("lists every term in chronological order with both GPAs", () => {
    renderTrendMode();

    const rows = screen
      .getByRole("table", { name: /gpa by semester/i })
      .querySelectorAll("tbody tr");

    expect(Array.from(rows).map((row) => row.textContent)).toEqual([
      "2023-Fall2.402.40",
      "2024-Spring1.902.15",
      "2024-Fall1.401.90",
    ]);
  });

  it("plots one chart point per term, agreeing with the table", () => {
    const { container } = renderTrendMode();

    const points = container.querySelectorAll("[data-testid='gpa-chart-point']");
    expect(points).toHaveLength(3);
    expect(Array.from(points).map((p) => p.getAttribute("data-term-gpa"))).toEqual([
      "2.4",
      "1.9",
      "1.4",
    ]);
  });

  it("annotates which rules fired", () => {
    renderTrendMode();

    const chips = screen.getAllByTestId("trend-rule");
    expect(chips.map((chip) => chip.textContent)).toEqual([
      "Sharp drop",
      "Sustained decline",
    ]);
  });

  it("shows the linked workflow item with its live status", () => {
    renderTrendMode();

    // Scoped to the panel: the sponsor escalation is also "pending".
    const item = screen.getByText("wft-stu-003-2024-Fall").parentElement!;
    expect(item.textContent).toContain("pending");
    expect(item.textContent).toContain("2026-07-26");
  });

  // -------------------------------------------------------------------------
  // Issue #65, cycle 4 — a student with no fired rule gets the neutral state,
  // never a blank panel and never a misleading badge
  // -------------------------------------------------------------------------

  const NO_TREND_PROFILE = {
    ...MOCK_PROFILE,
    gpa_trend: {
      series: [
        { term: "2023-Fall", term_gpa: 3.5, cumulative_gpa: 3.5 },
        { term: "2024-Spring", term_gpa: 3.45, cumulative_gpa: 3.48 },
      ],
      status: null,
      reason:
        "No declining trend through 2024-Spring: latest term GPA 3.45 versus 3.50 prior",
      rules_fired: [],
      workflow_item: null,
    },
  };

  it("shows a neutral no-trend state instead of a status badge", () => {
    renderTrendMode(NO_TREND_PROFILE);

    expect(screen.getByText(/no downward trend detected/i)).toBeInTheDocument();
    expect(screen.queryAllByTestId("trend-rule")).toHaveLength(0);
    expect(screen.getByText(/no trend detected/i)).toBeInTheDocument();
  });

  it("still renders the full series for a student with no fired rule", () => {
    const { container } = renderTrendMode(NO_TREND_PROFILE);

    const rows = screen
      .getByRole("table", { name: /gpa by semester/i })
      .querySelectorAll("tbody tr");
    expect(rows).toHaveLength(2);
    expect(
      container.querySelectorAll("[data-testid='gpa-chart-point']")
    ).toHaveLength(2);
  });

  it("says so plainly when no workflow item is linked", () => {
    renderTrendMode(NO_TREND_PROFILE);

    expect(screen.getByText(/no workflow item opened/i)).toBeInTheDocument();
  });

  it("the POST call targets student affairs officer", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    renderResolvedPage();

    fireEvent.click(screen.getByRole("button", { name: /approve intervention/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = fetchMock.mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
      const body = JSON.parse(postCalls[0][1].body as string);
      expect(body.owner_role).toBe("student affairs officer");
      expect(body.stage).toBe("academic_risk");
    });
  });
});
