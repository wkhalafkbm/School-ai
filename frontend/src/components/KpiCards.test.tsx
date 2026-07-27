import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import KpiCards, { MetricDetail } from "./KpiCards";

const METRICS = {
  students_needing_attention: 3,
  at_risk_detected_early: 3,
  registration_issues_resolved: 0,
  graduation_delays_prevented: 1,
  faculty_overload_alerts: 1,
};

const ATTENTION_DETAIL: MetricDetail = {
  metric_key: "students_needing_attention",
  definition: "Students carrying at least one open LMS risk flag.",
  destination: { label: "Academic Risk", href: "/academic-risk" },
  empty_message: "No student is carrying an LMS risk flag right now.",
  total: 14,
  rows: [
    { id: "stu-003", name: "Fahad Al-Ajmi", context: "Computer Science", status: "urgent", detail: "Risk flag: high" },
    { id: "stu-011", name: "Yousef Al-Otaibi", context: "Nursing", status: "urgent", detail: "Risk flag: high" },
    { id: "stu-019", name: "Khalid Al-Mansouri", context: "Business Admin", status: "needs_attention", detail: "Risk flag: medium" },
    { id: "stu-004", name: "Noor Al-Hamad", context: "Computer Science", status: "needs_attention", detail: "Risk flag: medium" },
    { id: "stu-022", name: "Dana Al-Rashid", context: "Mechanical Eng.", status: "watch", detail: "Risk flag: low" },
    { id: "stu-030", name: "Omar Al-Sabah", context: "Nursing", status: "watch", detail: "Risk flag: low" },
  ],
};

const EARLY_DETAIL: MetricDetail = {
  metric_key: "at_risk_detected_early",
  definition: "Students whose GPA is trending downward.",
  destination: { label: "Academic Risk", href: "/academic-risk" },
  empty_message: "No student shows a downward GPA trend right now.",
  total: 3,
  rows: [
    { id: "stu-003", name: "Fahad Al-Ajmi", context: "Computer Science", status: "urgent", detail: "GPA declined 1.90 → 1.40 in 2024-Fall (sharp drop)" },
    { id: "stu-015", name: "Hamad Al-Dashti", context: "Business Admin", status: "needs_attention", detail: "GPA declined 3.00 → 2.40 in 2024-Fall (sharp drop)" },
    { id: "stu-013", name: "Turki Al-Azemi", context: "Information Systems", status: "watch", detail: "GPA declined 2.90 → 2.65 → 2.40 across 2023-Fall–2024-Fall (sustained decline)" },
  ],
};

// Genuinely zero on the seeded demo data — the panel must explain, not go blank.
const REGISTRATION_DETAIL: MetricDetail = {
  metric_key: "registration_issues_resolved",
  definition: "Registration-resolution items approved this term.",
  destination: { label: "Workflow Activity", href: "/workflow-activity" },
  empty_message: "No registration issue has been resolved yet this term.",
  total: 0,
  rows: [],
};

// An achievement metric — every row is uniformly positive, by design.
const GRADUATION_DETAIL: MetricDetail = {
  metric_key: "graduation_delays_prevented",
  definition: "Interventions completed this term.",
  destination: { label: "Progression", href: "/progression" },
  empty_message: "No intervention has been completed yet this term.",
  total: 1,
  rows: [
    { id: "int-004", name: "Khalid Al-Mansouri", context: "Computer Science", status: "on_track", detail: "Advisor meeting" },
  ],
};

// Faculty rows — context carries department, not programme.
const FACULTY_DETAIL: MetricDetail = {
  metric_key: "faculty_overload_alerts",
  definition: "Faculty at or above their credit ceiling this semester.",
  destination: { label: "Teaching Readiness", href: "/teaching-readiness" },
  empty_message: "No faculty member is at or over their credit ceiling.",
  total: 1,
  rows: [
    { id: "fac-001", name: "Dr. Ahmed Al-Rashidi", context: "Computer Science", status: "urgent", detail: "15 of 12 credits" },
  ],
};

const ALL_DETAILS = {
  students_needing_attention: ATTENTION_DETAIL,
  at_risk_detected_early: EARLY_DETAIL,
  registration_issues_resolved: REGISTRATION_DETAIL,
  graduation_delays_prevented: GRADUATION_DETAIL,
  faculty_overload_alerts: FACULTY_DETAIL,
};

const ATTENTION_LABEL = "Students Needing Attention";

describe("KpiCards", () => {
  it("renders five cards", () => {
    const { container } = render(<KpiCards metrics={METRICS} />);
    const cards = container.querySelectorAll("[data-testid='kpi-card']");
    expect(cards).toHaveLength(5);
  });

  it("displays the numeric value for each metric", () => {
    render(<KpiCards metrics={METRICS} />);
    expect(screen.getByTestId("kpi-students_needing_attention")).toHaveTextContent("3");
    expect(screen.getByTestId("kpi-at_risk_detected_early")).toHaveTextContent("3");
    expect(screen.getByTestId("kpi-registration_issues_resolved")).toHaveTextContent("0");
    expect(screen.getByTestId("kpi-graduation_delays_prevented")).toHaveTextContent("1");
    expect(screen.getByTestId("kpi-faculty_overload_alerts")).toHaveTextContent("1");
  });

  it("displays a human-readable label for each card", () => {
    render(<KpiCards metrics={METRICS} />);
    expect(screen.getByText("Students Needing Attention")).toBeTruthy();
    expect(screen.getByText("At-Risk Detected Early")).toBeTruthy();
    expect(screen.getByText("Registration Issues Resolved")).toBeTruthy();
    expect(screen.getByText("Graduation Delays Prevented")).toBeTruthy();
    expect(screen.getByText("Faculty Overload Alerts")).toBeTruthy();
  });
});

describe("KpiCards drill-down panel", () => {
  const renderCards = () =>
    render(
      <KpiCards
        metrics={METRICS}
        details={{ students_needing_attention: ATTENTION_DETAIL }}
      />
    );

  it("shows no panel until a card is clicked", () => {
    renderCards();
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();
  });

  it("opens a panel naming the students behind the number", async () => {
    const user = userEvent.setup();
    renderCards();

    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));

    const panel = screen.getByTestId("kpi-drilldown");
    const rows = within(panel).getAllByTestId("drilldown-row");
    expect(rows).toHaveLength(6);

    const fahad = rows.find((row) => row.textContent?.includes("Fahad Al-Ajmi"))!;
    expect(fahad).toBeDefined();
    expect(within(fahad).getByText("Computer Science")).toBeInTheDocument();
    expect(within(fahad).getByText("Risk flag: high")).toBeInTheDocument();
    expect(within(fahad).getByText("Urgent")).toBeInTheDocument();
  });

  it("closes again when the open card is clicked a second time", async () => {
    const user = userEvent.setup();
    renderCards();
    const card = screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") });

    await user.click(card);
    expect(screen.getByTestId("kpi-drilldown")).toBeInTheDocument();

    await user.click(card);
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    renderCards();

    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));
    expect(screen.getByTestId("kpi-drilldown")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();
  });

  it("closes from the panel's own close control", async () => {
    const user = userEvent.setup();
    renderCards();
    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));

    const panel = screen.getByTestId("kpi-drilldown");
    await user.click(within(panel).getByRole("button", { name: /close/i }));

    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();
  });

  it("states how many of the total are shown, and offers one plain exit to the stage page", async () => {
    const user = userEvent.setup();
    renderCards();
    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));

    const footer = screen.getByTestId("drilldown-footer");
    expect(footer).toHaveTextContent("Showing 6 of 14");

    // Worded as plain navigation — the stage page is not filtered to these six.
    const link = within(footer).getByRole("link", { name: /view all in academic risk/i });
    expect(link).toHaveAttribute("href", "/academic-risk");

    // That footer link is the panel's only link.
    expect(within(screen.getByTestId("kpi-drilldown")).getAllByRole("link")).toHaveLength(1);
  });

  it("carries a definition line saying what the number actually counts", async () => {
    const user = userEvent.setup();
    renderCards();
    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));

    expect(screen.getByTestId("drilldown-definition")).toHaveTextContent(
      "Students carrying at least one open LMS risk flag."
    );
  });

  it("points its caret at whichever card opened it", async () => {
    const user = userEvent.setup();
    render(
      <KpiCards
        metrics={METRICS}
        details={{
          students_needing_attention: ATTENTION_DETAIL,
          at_risk_detected_early: EARLY_DETAIL,
        }}
      />
    );

    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));
    const overFirstCard = screen.getByTestId("drilldown-caret").style.left;

    await user.click(screen.getByRole("button", { name: /At-Risk Detected Early/i }));
    const overSecondCard = screen.getByTestId("drilldown-caret").style.left;

    expect(overFirstCard).toBeTruthy();
    expect(overSecondCard).toBeTruthy();
    expect(overSecondCard).not.toBe(overFirstCard);
    // Card 1 of 5 is centred at 10% of the row, card 2 at 30%.
    expect(overFirstCard).toContain("10%");
    expect(overSecondCard).toContain("30%");
  });

  it("tells screen readers whether the card it belongs to is expanded", async () => {
    const user = userEvent.setup();
    renderCards();
    const card = screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") });

    expect(card).toHaveAttribute("aria-expanded", "false");
    await user.click(card);
    expect(card).toHaveAttribute("aria-expanded", "true");
  });

  it("opens and closes by keyboard alone", async () => {
    const user = userEvent.setup();
    renderCards();

    await user.tab();
    const card = screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") });
    expect(card).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(screen.getByTestId("kpi-drilldown")).toBeInTheDocument();

    await user.keyboard(" ");
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();
  });

  it("leaves cards without a drill-down inert rather than dead buttons", () => {
    renderCards();
    // Only the one card with detail is a button; the other four stay plain.
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(screen.getAllByTestId("kpi-card")).toHaveLength(5);
  });

  it("swaps the panel rather than stacking a second one when another card is clicked", async () => {
    const user = userEvent.setup();
    render(
      <KpiCards
        metrics={METRICS}
        details={{
          students_needing_attention: ATTENTION_DETAIL,
          at_risk_detected_early: EARLY_DETAIL,
        }}
      />
    );

    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));
    await user.click(screen.getByRole("button", { name: /At-Risk Detected Early/i }));

    const panels = screen.getAllByTestId("kpi-drilldown");
    expect(panels).toHaveLength(1);
    // Identify the surviving panel by its definition, which every metric writes
    // for itself and no two share. Naming a student here instead would tie this
    // test to which rows the fixtures happen to hold: the same student can
    // legitimately appear under two metrics — carrying an LMS risk flag and a
    // declining GPA trend at once — and that would silently stop proving a swap.
    expect(within(panels[0]).getByTestId("drilldown-definition")).toHaveTextContent(
      EARLY_DETAIL.definition
    );
  });

  it("keeps the five-column grid to five cards, so opening a panel cannot reflow it", async () => {
    const user = userEvent.setup();
    const { container } = renderCards();
    const grid = container.querySelector(".grid")!;
    const before = grid.children.length;

    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));

    expect(grid.children).toHaveLength(before);
    expect(grid.children).toHaveLength(5);
    // The panel is a sibling of the grid, not a child of it.
    expect(grid.contains(screen.getByTestId("kpi-drilldown"))).toBe(false);
  });

  it("expands every one of the five cards, each with its own definition and destination", async () => {
    const user = userEvent.setup();
    render(<KpiCards metrics={METRICS} details={ALL_DETAILS} />);

    // Identical affordance across the row: all five are real expandable buttons.
    const cards = screen.getAllByTestId("kpi-card");
    expect(cards).toHaveLength(5);
    for (const card of cards) {
      expect(card.tagName).toBe("BUTTON");
      expect(card).toHaveAttribute("aria-expanded", "false");
    }

    const cardLabels: Record<keyof typeof ALL_DETAILS, string> = {
      students_needing_attention: "Students Needing Attention",
      at_risk_detected_early: "At-Risk Detected Early",
      registration_issues_resolved: "Registration Issues Resolved",
      graduation_delays_prevented: "Graduation Delays Prevented",
      faculty_overload_alerts: "Faculty Overload Alerts",
    };

    for (const [key, detail] of Object.entries(ALL_DETAILS)) {
      const label = cardLabels[key as keyof typeof ALL_DETAILS];
      await user.click(screen.getByRole("button", { name: new RegExp(label, "i") }));

      expect(screen.getByTestId("drilldown-definition")).toHaveTextContent(detail.definition);
      const footer = screen.getByTestId("drilldown-footer");
      const link = within(footer).getByRole("link");
      expect(link).toHaveAttribute("href", detail.destination.href);
      expect(link).toHaveTextContent(detail.destination.label);
    }
  });

  it("shows department in the context column for faculty rows", async () => {
    const user = userEvent.setup();
    render(<KpiCards metrics={METRICS} details={ALL_DETAILS} />);

    await user.click(screen.getByRole("button", { name: /Faculty Overload Alerts/i }));

    const row = screen.getByTestId("drilldown-row");
    expect(within(row).getByText("Dr. Ahmed Al-Rashidi")).toBeInTheDocument();
    expect(within(row).getByText("Computer Science")).toBeInTheDocument();
    expect(within(row).getByText("15 of 12 credits")).toBeInTheDocument();
    expect(within(row).getByText("Urgent")).toBeInTheDocument();
  });

  it("renders achievement metrics with uniformly positive statuses", async () => {
    const user = userEvent.setup();
    render(<KpiCards metrics={METRICS} details={ALL_DETAILS} />);

    await user.click(screen.getByRole("button", { name: /Graduation Delays Prevented/i }));

    const row = screen.getByTestId("drilldown-row");
    expect(within(row).getByText("Khalid Al-Mansouri")).toBeInTheDocument();
    expect(within(row).getByText("On Track")).toBeInTheDocument();
    expect(within(row).getByText("Advisor meeting")).toBeInTheDocument();
  });

  it("renders rows as plain text with no link and no clickable affordance", async () => {
    const user = userEvent.setup();
    renderCards();
    await user.click(screen.getByRole("button", { name: new RegExp(ATTENTION_LABEL, "i") }));

    // Rows are deliberately not clickable: the stage pages ignore query params,
    // so a clickable row would land the user on an unfiltered page.
    for (const row of screen.getAllByTestId("drilldown-row")) {
      expect(row.querySelector("a")).toBeNull();
      expect(row.querySelector("button")).toBeNull();
      expect(row.className).not.toContain("cursor-pointer");
      expect(row.className).not.toContain("hover:");
    }
  });
});

describe("KpiCards zero-count empty state", () => {
  const renderAll = () => render(<KpiCards metrics={METRICS} details={ALL_DETAILS} />);
  const ZERO_CARD = /Registration Issues Resolved/i;

  it("a card reading zero still expands to the full panel chrome", async () => {
    const user = userEvent.setup();
    renderAll();

    const card = screen.getByRole("button", { name: ZERO_CARD });
    expect(card).toHaveAttribute("aria-expanded", "false");
    await user.click(card);

    expect(card).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByTestId("kpi-drilldown")).toBeInTheDocument();
    expect(screen.getByTestId("drilldown-definition")).toHaveTextContent(
      REGISTRATION_DETAIL.definition
    );
  });

  it("a term with nobody declining still expands and says so in trend terms", async () => {
    // #69: zero is a real answer for the trend KPI, not a failed load. Asserted
    // on this metric specifically because its empty message is the one place a
    // reader learns the headline number means a trajectory, not a low GPA.
    const user = userEvent.setup();
    render(
      <KpiCards
        metrics={{ ...METRICS, at_risk_detected_early: 0 }}
        details={{
          ...ALL_DETAILS,
          at_risk_detected_early: { ...EARLY_DETAIL, total: 0, rows: [] },
        }}
      />
    );

    const card = screen.getByRole("button", { name: /At-Risk Detected Early/i });
    await user.click(card);

    expect(card).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByTestId("kpi-drilldown")).toBeInTheDocument();
    expect(screen.queryAllByTestId("drilldown-row")).toHaveLength(0);
    expect(screen.getByTestId("drilldown-empty")).toHaveTextContent(
      "No student shows a downward GPA trend right now."
    );
  });

  it("explains the zero in the metric's own terms instead of a blank panel", async () => {
    const user = userEvent.setup();
    renderAll();
    await user.click(screen.getByRole("button", { name: ZERO_CARD }));

    expect(screen.queryAllByTestId("drilldown-row")).toHaveLength(0);
    expect(screen.getByTestId("drilldown-empty")).toHaveTextContent(
      "No registration issue has been resolved yet this term."
    );
  });

  it("still offers the footer link out, but drops the meaningless 'Showing 0 of 0'", async () => {
    const user = userEvent.setup();
    renderAll();
    await user.click(screen.getByRole("button", { name: ZERO_CARD }));

    const footer = screen.getByTestId("drilldown-footer");
    expect(footer).not.toHaveTextContent(/Showing/i);
    const link = within(footer).getByRole("link", { name: /view all in workflow activity/i });
    expect(link).toHaveAttribute("href", "/workflow-activity");
  });

  it("shows no empty message when the metric has rows", async () => {
    const user = userEvent.setup();
    renderAll();
    await user.click(screen.getByRole("button", { name: /Students Needing Attention/i }));

    expect(screen.queryByTestId("drilldown-empty")).toBeNull();
    expect(screen.getByTestId("drilldown-footer")).toHaveTextContent("Showing 6 of 14");
  });

  it("closes a zero-count panel the same three ways as any other", async () => {
    const user = userEvent.setup();
    renderAll();
    const card = screen.getByRole("button", { name: ZERO_CARD });

    await user.click(card);
    await user.click(card); // second click on the card
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();

    await user.click(card);
    await user.keyboard("{Escape}"); // Esc
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();

    await user.click(card);
    await user.click(screen.getByRole("button", { name: /close/i })); // explicit control
    expect(screen.queryByTestId("kpi-drilldown")).toBeNull();
  });
});
