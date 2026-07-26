import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const METRICS = {
  students_needing_attention: 14,
  at_risk_detected_early: 1,
  registration_issues_resolved: 0,
  graduation_delays_prevented: 1,
  faculty_overload_alerts: 1,
};

const HEALTH = {
  onboarding: "watch",
  registration: "on_track",
  academic_progress: "urgent",
  graduation_planning: "urgent",
  career: "watch",
};

const QUEUE = [
  {
    student_id: "stu-003",
    student_name: "Fahad Al-Ajmi",
    stage: "academic_progress",
    status: "urgent",
    reason: "LMS risk flag raised",
  },
];

const CHART_DATA = {
  enrollments_by_semester: [{ semester: "2024-Fall", count: 12 }],
  gpa_distribution: [{ bucket: "<2.0", count: 2 }],
  intervention_outcomes: [{ status: "completed", count: 1 }],
  lms_risk_by_semester: [{ semester: "2024-Fall", at_risk: 3, total: 10 }],
};

const DETAIL = {
  metric_key: "students_needing_attention",
  definition: "Students carrying at least one open LMS risk flag.",
  destination: { label: "Academic Risk", href: "/academic-risk" },
  total: 14,
  rows: [
    {
      student_id: "stu-003",
      name: "Fahad Al-Ajmi",
      program_name: "Computer Science",
      status: "urgent",
      detail: "Risk flag: high",
    },
    {
      student_id: "stu-019",
      name: "Khalid Al-Mansouri",
      program_name: "Business Admin",
      status: "needs_attention",
      detail: "Risk flag: medium",
    },
  ],
};

const BODIES: Record<string, unknown> = {
  "/api/overview/metrics": METRICS,
  "/api/overview/journey-health": HEALTH,
  "/api/overview/priority-queue": QUEUE,
  "/api/overview/chart-data": CHART_DATA,
  "/api/overview/metrics/students_needing_attention/detail": DETAIL,
};

function stubFetch() {
  const fetchMock = vi.fn(async (url: string) => {
    const path = Object.keys(BODIES).find((p) => url.endsWith(p));
    if (!path) throw new Error(`unstubbed fetch: ${url}`);
    return { ok: true, json: async () => BODIES[path] };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("OverviewPage drill-down data", () => {
  afterEach(() => vi.restoreAllMocks());

  it("fetches the drill-down alongside its existing reads, in one parallel batch", async () => {
    const fetchMock = stubFetch();
    const { default: Page } = await import("./page");
    render(await Page());

    const paths = fetchMock.mock.calls.map(([url]) => new URL(url as string).pathname);
    expect(paths).toContain("/api/overview/metrics/students_needing_attention/detail");
    expect(paths).toHaveLength(5);
  });

  it("opens the panel from server-supplied rows, with no client fetch and no loading state", async () => {
    const fetchMock = stubFetch();
    const { default: Page } = await import("./page");
    render(await Page());

    const callsBeforeClick = fetchMock.mock.calls.length;
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Students Needing Attention/i }));

    const panel = screen.getByTestId("kpi-drilldown");
    expect(panel).toHaveTextContent("Fahad Al-Ajmi");
    expect(panel).toHaveTextContent("Showing 2 of 14");
    expect(fetchMock.mock.calls).toHaveLength(callsBeforeClick);
  });
});
