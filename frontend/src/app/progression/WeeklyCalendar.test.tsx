import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import WeeklyCalendar from "./WeeklyCalendar";

/** A plan shaped like /api/progression/graduation-plan serves it. */
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
          course_code: "CS301",
          course_name: "Algorithms",
          section_code: "CS301-01",
          days: ["Mon", "Wed"],
          start_time: "09:00",
          end_time: "10:15",
          room: "B105",
          credits: 3,
        },
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

/** Resolve the fetch this render kicks off with `plan`, then settle the DOM. */
function stubFetch(plan: unknown = MOCK_PLAN) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => plan,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function renderLoaded(plan: unknown = MOCK_PLAN) {
  stubFetch(plan);
  const result = render(<WeeklyCalendar />);
  await screen.findByRole("table", { name: /weekly class schedule/i });
  return result;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("WeeklyCalendar", () => {
  // -------------------------------------------------------------------------
  // Cycle 3 — tracer bullet: the calendar fetches its own plan and renders a
  // Sunday–Thursday week
  // -------------------------------------------------------------------------

  it("fetches the plan from the graduation-plan endpoint", async () => {
    const fetchMock = stubFetch();
    render(<WeeklyCalendar />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toContain("/api/progression/graduation-plan");
  });

  it("shows a loading state until the plan arrives", async () => {
    stubFetch();
    render(<WeeklyCalendar />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await screen.findByRole("table", { name: /weekly class schedule/i });
    expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
  });

  it("renders a column for each day of the Sunday–Thursday academic week", async () => {
    await renderLoaded();

    const dayHeaders = screen.getAllByRole("columnheader");
    // The first column is the time axis; the rest are the teaching days.
    expect(dayHeaders.slice(1).map((h) => h.textContent)).toEqual([
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
    ]);
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — each class renders as a block on every day it meets, carrying
  // its course, time and room; the term is labelled as the current one
  // -------------------------------------------------------------------------

  it("places each class in every day column it meets in", async () => {
    await renderLoaded();

    const codesOn = (day: string) =>
      within(screen.getByTestId(`day-column-${day}`))
        .queryAllByTestId(/^class-block-/)
        .map((block) => within(block).getByTestId("class-code").textContent);

    expect(codesOn("Sun")).toEqual(["CS302"]);
    expect(codesOn("Mon")).toEqual(["CS301"]);
    expect(codesOn("Tue")).toEqual(["CS302"]);
    expect(codesOn("Wed")).toEqual(["CS301"]);
    expect(codesOn("Thu")).toEqual([]);
  });

  it("shows each block's meeting time and room", async () => {
    await renderLoaded();

    const monday = within(screen.getByTestId("day-column-Mon"));
    const block = monday.getByTestId("class-block-CS301");

    expect(within(block).getByText("09:00–10:15")).toBeInTheDocument();
    expect(within(block).getByText("B105")).toBeInTheDocument();
  });

  it("labels the grid as the student's current term", async () => {
    await renderLoaded();

    expect(screen.getByText(/current term/i)).toBeInTheDocument();
    expect(screen.getByText(/2024-Fall/)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — geometry: a block sits at its start time and is as tall as it is
  // long, so a 50-minute class is visibly shorter than a 75-minute one
  //
  // These assert relationships the spec fixes (ratios, ordering), not the pixel
  // scale the component happens to pick — the scale is free to change.
  // -------------------------------------------------------------------------

  /** Two same-day classes with round durations: 50 minutes and 75 minutes. */
  const GEOMETRY_PLAN = {
    ...MOCK_PLAN,
    terms: [
      {
        ...MOCK_PLAN.terms[0],
        classes: [
          {
            course_code: "MATH101",
            course_name: "Calculus I",
            section_code: "MATH101-01",
            days: ["Sun"],
            start_time: "09:00",
            end_time: "09:50",
            room: "A201",
            credits: 3,
          },
          {
            course_code: "CS302",
            course_name: "Operating Systems",
            section_code: "CS302-01",
            days: ["Sun"],
            start_time: "11:00",
            end_time: "12:15",
            room: "B107",
            credits: 3,
          },
        ],
      },
    ],
  };

  const px = (value: string) => parseFloat(value.replace("px", ""));

  async function geometry() {
    await renderLoaded(GEOMETRY_PLAN);
    const sunday = within(screen.getByTestId("day-column-Sun"));
    const read = (code: string) => {
      const { style } = sunday.getByTestId(`class-block-${code}`);
      return { top: px(style.top), height: px(style.height) };
    };
    return { short: read("MATH101"), long: read("CS302") };
  }

  it("gives the later class a larger vertical offset", async () => {
    const { short, long } = await geometry();

    expect(long.top).toBeGreaterThan(short.top);
  });

  it("sizes block height in proportion to duration", async () => {
    const { short, long } = await geometry();

    // 75 minutes against 50 is exactly 1.5× as tall.
    expect(long.height / short.height).toBeCloseTo(75 / 50, 5);
  });

  it("offsets blocks on the same minutes-per-pixel scale it sizes them with", async () => {
    const { short, long } = await geometry();

    // 09:00 → 11:00 is 120 minutes; the 50-minute block fixes the scale.
    const perMinute = short.height / 50;
    expect(long.top - short.top).toBeCloseTo(120 * perMinute, 5);
  });

  // -------------------------------------------------------------------------
  // Cycle 6 — the calendar owns its failure: a dead endpoint shows a message
  // here and nowhere else on the page
  // -------------------------------------------------------------------------

  it("shows an error message when the plan request fails outright", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    render(<WeeklyCalendar />);

    expect(
      await screen.findByText(/couldn't load the class schedule/i)
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows an error message when the endpoint answers with an error status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: "boom" }),
      })
    );
    render(<WeeklyCalendar />);

    expect(
      await screen.findByText(/couldn't load the class schedule/i)
    ).toBeInTheDocument();
  });

  it("reports an empty schedule rather than an error when the plan has no current term", async () => {
    stubFetch({ ...MOCK_PLAN, terms: [] });
    render(<WeeklyCalendar />);

    expect(await screen.findByText(/no classes scheduled/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/couldn't load the class schedule/i)
    ).not.toBeInTheDocument();
  });
});
