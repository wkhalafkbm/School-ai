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
