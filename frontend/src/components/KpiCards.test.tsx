import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import KpiCards, { MetricDetail } from "./KpiCards";

const METRICS = {
  students_needing_attention: 3,
  at_risk_detected_early: 1,
  registration_issues_resolved: 0,
  graduation_delays_prevented: 1,
  faculty_overload_alerts: 1,
};

const ATTENTION_DETAIL: MetricDetail = {
  metric_key: "students_needing_attention",
  definition: "Students carrying at least one open LMS risk flag.",
  destination: { label: "Academic Risk", href: "/academic-risk" },
  total: 14,
  rows: [
    { student_id: "stu-003", name: "Fahad Al-Ajmi", program_name: "Computer Science", status: "urgent", detail: "Risk flag: high" },
    { student_id: "stu-011", name: "Yousef Al-Otaibi", program_name: "Nursing", status: "urgent", detail: "Risk flag: high" },
    { student_id: "stu-019", name: "Khalid Al-Mansouri", program_name: "Business Admin", status: "needs_attention", detail: "Risk flag: medium" },
    { student_id: "stu-004", name: "Noor Al-Hamad", program_name: "Computer Science", status: "needs_attention", detail: "Risk flag: medium" },
    { student_id: "stu-022", name: "Dana Al-Rashid", program_name: "Mechanical Eng.", status: "watch", detail: "Risk flag: low" },
    { student_id: "stu-030", name: "Omar Al-Sabah", program_name: "Nursing", status: "watch", detail: "Risk flag: low" },
  ],
};

const EARLY_DETAIL: MetricDetail = {
  metric_key: "at_risk_detected_early",
  definition: "Low-GPA students with no open support case.",
  destination: { label: "Academic Risk", href: "/academic-risk" },
  total: 1,
  rows: [
    { student_id: "stu-007", name: "Layla Al-Mutairi", program_name: "Nursing", status: "watch", detail: "GPA 2.3, no open case" },
  ],
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
    expect(screen.getByTestId("kpi-at_risk_detected_early")).toHaveTextContent("1");
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
    expect(within(panels[0]).getByText("Layla Al-Mutairi")).toBeInTheDocument();
    expect(within(panels[0]).queryByText("Fahad Al-Ajmi")).toBeNull();
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
