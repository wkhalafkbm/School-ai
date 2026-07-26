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
  admissions: "watch",
  enrollment: "on_track",
  academic_risk: "urgent",
  progression: "urgent",
  career_alumni: "watch",
};

const QUEUE = [
  {
    student_id: "stu-003",
    student_name: "Fahad Al-Ajmi",
    stage: "academic_risk",
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
  empty_message: "No student is carrying an LMS risk flag right now.",
  total: 14,
  rows: [
    {
      id: "stu-003",
      name: "Fahad Al-Ajmi",
      context: "Computer Science",
      status: "urgent",
      detail: "Risk flag: high",
    },
    {
      id: "stu-019",
      name: "Khalid Al-Mansouri",
      context: "Business Admin",
      status: "needs_attention",
      detail: "Risk flag: medium",
    },
  ],
};

const ALL_METRIC_KEYS = [
  "students_needing_attention",
  "at_risk_detected_early",
  "registration_issues_resolved",
  "graduation_delays_prevented",
  "faculty_overload_alerts",
] as const;

const EMPTY_DETAIL = (metric_key: string) => ({
  metric_key,
  definition: `Definition for ${metric_key}.`,
  destination: { label: "Workflow Activity", href: "/workflow-activity" },
  empty_message: `Nothing counted yet for ${metric_key}.`,
  total: 0,
  rows: [],
});

const BODIES: Record<string, unknown> = {
  "/api/overview/metrics": METRICS,
  "/api/overview/journey-health": HEALTH,
  "/api/overview/priority-queue": QUEUE,
  "/api/overview/chart-data": CHART_DATA,
  "/api/overview/metrics/students_needing_attention/detail": DETAIL,
  ...Object.fromEntries(
    ALL_METRIC_KEYS.filter((k) => k !== "students_needing_attention").map((k) => [
      `/api/overview/metrics/${k}/detail`,
      EMPTY_DETAIL(k),
    ])
  ),
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

  it("fetches all five drill-downs alongside its existing reads, in one parallel batch", async () => {
    const fetchMock = stubFetch();
    const { default: Page } = await import("./page");
    render(await Page());

    const paths = fetchMock.mock.calls.map(([url]) => new URL(url as string).pathname);
    for (const key of ALL_METRIC_KEYS) {
      expect(paths).toContain(`/api/overview/metrics/${key}/detail`);
    }
    expect(paths).toHaveLength(9);
  });

  it("opens a zero-count card's empty state from server-supplied data, with no client fetch", async () => {
    const fetchMock = stubFetch();
    const { default: Page } = await import("./page");
    render(await Page());

    const callsBeforeClick = fetchMock.mock.calls.length;
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Registration Issues Resolved/i }));

    const panel = screen.getByTestId("kpi-drilldown");
    expect(panel).toHaveTextContent("Nothing counted yet for registration_issues_resolved.");
    expect(fetchMock.mock.calls).toHaveLength(callsBeforeClick);
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
