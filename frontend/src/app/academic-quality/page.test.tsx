import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { act } from "react";
import AcademicQualityPage from "./page";

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

/** The CS101 marking variance the demo turns on (#98). */
const CS101_FLAG = {
  course_id: "crs-001",
  course_code: "CS101",
  course_name: "Introduction to Computer Science",
  slo_id: "slo-001",
  slo_code: "CS101-SLO1",
  slo_description:
    "Students will be able to write basic Python programs using variables, loops, and conditionals",
  semester: "2024-Fall",
  sections: [
    {
      section_id: "sec-001",
      section_code: "CS101-01",
      instructor_id: "fac-001",
      instructor_name: "Dr. Ahmed Al-Rashidi",
      proficiency_rate: 0.913,
      assessed_students: 23,
      proficient_count: 21,
    },
    {
      section_id: "sec-001b",
      section_code: "CS101-02",
      instructor_id: "fac-010",
      instructor_name: "Dr. Noura Al-Azemi",
      proficiency_rate: 0.542,
      assessed_students: 24,
      proficient_count: 13,
    },
  ],
  gap_points: 37.1,
  threshold_points: 20,
  trigger: "Marking variance flagged — CS101 CS101-SLO1 (2024-Fall)",
  moderation_owner_name: "Programme Quality Lead",
  moderation_owner_role: "programme quality lead",
  routed_item: null,
};

/** The Computer Science SLO → CLO → PLO chain (#97), trimmed to two PLOs. */
const MOCK_ATTAINMENT = {
  program_id: "prog-001",
  program_name: "Computer Science",
  attainment_target: 0.7,
  latest_semester: "2024-Fall",
  plos_below_target: 1,
  plos: [
    {
      code: "PLO1",
      title: "Program and build software",
      description: "Graduates write correct, well-structured programs.",
      attainment: 0.661,
      on_target: false,
      slo_count: 2,
      assessed_slo_count: 1,
      courses: [
        {
          course_id: "crs-001",
          course_code: "CS101",
          course_name: "Introduction to Computer Science",
          attainment: 0.733,
          on_target: true,
          slos: [
            {
              slo_id: "slo-001",
              slo_code: "CS101-SLO1",
              description:
                "Students will be able to write basic Python programs using variables, loops, and conditionals",
              proficiency_rate: 0.733,
              on_target: true,
              last_assessed_semester: "2024-Fall",
              assessed_students: 30,
              source: "assessment",
              history: [
                { semester: "2023-Fall", proficiency_rate: 0.688 },
                { semester: "2024-Spring", proficiency_rate: 0.714 },
                { semester: "2024-Fall", proficiency_rate: 0.733 },
              ],
            },
          ],
        },
        {
          course_id: "crs-006",
          course_code: "CS401",
          course_name: "Software Engineering",
          attainment: null,
          on_target: null,
          slos: [
            {
              slo_id: "slo-012",
              slo_code: "CS401-SLO1",
              description: "Students will produce software requirements specifications",
              proficiency_rate: null,
              on_target: null,
              last_assessed_semester: null,
              assessed_students: null,
              source: null,
              history: [],
            },
          ],
        },
      ],
    },
    {
      code: "PLO4",
      title: "Apply data-driven and intelligent methods",
      description: "Graduates build, train and evaluate data-driven solutions.",
      attainment: 0.74,
      on_target: true,
      slo_count: 1,
      assessed_slo_count: 1,
      courses: [
        {
          course_id: "crs-007",
          course_code: "CS450",
          course_name: "Machine Learning",
          attainment: 0.8,
          on_target: true,
          slos: [
            {
              slo_id: "slo-013",
              slo_code: "CS450-SLO1",
              description: "Students will train and evaluate supervised learning models",
              proficiency_rate: 0.8,
              on_target: true,
              last_assessed_semester: "2024-Fall",
              assessed_students: 20,
              source: "assessment",
              history: [{ semester: "2024-Fall", proficiency_rate: 0.8 }],
            },
          ],
        },
      ],
    },
  ],
};

const MOCK_PROFILE = {
  stage_summary: {
    health: "needs_attention",
    open_flag_count: 1,
    routed_flag_count: 0,
    plo_count: 2,
    plos_below_target: 1,
    attainment_target: 0.7,
  },
  program_attainment: MOCK_ATTAINMENT,
  moderation_variance_flags: [CS101_FLAG],
  diagnosis:
    "CS101-SLO1 feeds PLO1, which sits at 66% against the 70% target. CS101-01 and CS101-02 disagree by 37 points; moderate CS101-SLO1 first.",
};

function renderResolvedPage(data: unknown = MOCK_PROFILE) {
  const result = render(<AcademicQualityPage />);
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
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => ({ id: "wfl-new" }) })
  );
});

afterEach(() => vi.restoreAllMocks());

// Issue #96 — /academic-quality is the home of Agent 10 (academic outcomes &
// quality intelligence).
describe("AcademicQualityPage", () => {
  it("renders the Academic Quality stage heading", () => {
    renderResolvedPage();
    expect(
      screen.getByRole("heading", { level: 1, name: "Moderation and Validation" })
    ).toBeInTheDocument();
  });

  it("renders inside a main landmark like the other stage pages", () => {
    renderResolvedPage();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("streams its profile from the academic quality endpoint", () => {
    renderResolvedPage();
    expect(StubEventSource.instances[0].url).toMatch(
      /\/api\/academic-quality\/profile\/stream$/
    );
  });

  // -------------------------------------------------------------------------
  // Issue #98, cycle 1 — the red moderation variance card names the course,
  // the SLO, both sections with their instructors and rates, and the gap.
  // -------------------------------------------------------------------------

  it("shows the moderation variance card with course, SLO, sections, instructors, rates and gap", () => {
    renderResolvedPage();

    const card = screen.getByRole("region", { name: /moderation variance/i });
    expect(card).toHaveClass("border-red-200");

    expect(
      within(card).getByText("CS101 — Introduction to Computer Science")
    ).toBeInTheDocument();
    expect(within(card).getByText(/CS101-SLO1/)).toBeInTheDocument();
    expect(within(card).getByText(/2024-Fall/)).toBeInTheDocument();

    expect(within(card).getByText("CS101-01")).toBeInTheDocument();
    expect(within(card).getByText("Dr. Ahmed Al-Rashidi")).toBeInTheDocument();
    expect(within(card).getByText("91%")).toBeInTheDocument();
    expect(within(card).getByText("CS101-02")).toBeInTheDocument();
    expect(within(card).getByText("Dr. Noura Al-Azemi")).toBeInTheDocument();
    expect(within(card).getByText("54%")).toBeInTheDocument();

    expect(within(card).getByText(/37 points/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Issue #98, cycle 2 — the six-step workflow strip mirrors the deck: Measure
// (AI), Diagnose (AI), Moderate (human/AI), Validate (human), Act (human),
// Re-measure (AI). An open flag lights the strip through Moderate.
// ---------------------------------------------------------------------------

const STEP_NAMES = ["Measure", "Diagnose", "Moderate", "Validate", "Act", "Re-measure"];

function stripSteps() {
  const strip = screen.getByRole("list", { name: /moderation workflow/i });
  return within(strip).getAllByRole("listitem");
}

function litStepNames() {
  return stripSteps()
    .filter((step) => step.getAttribute("data-lit") === "true")
    .map((step) => step.getAttribute("data-step"));
}

describe("moderation workflow strip", () => {
  it("lists the six deck steps in order with their actors", () => {
    renderResolvedPage();

    const steps = stripSteps();
    expect(steps.map((s) => s.getAttribute("data-step"))).toEqual(STEP_NAMES);
    expect(within(steps[0]).getByText("AI")).toBeInTheDocument();
    expect(within(steps[2]).getByText("Human / AI")).toBeInTheDocument();
    expect(within(steps[3]).getByText("Human")).toBeInTheDocument();
  });

  it("is lit through Moderate while a flag is open", () => {
    renderResolvedPage();

    expect(litStepNames()).toEqual(["Measure", "Diagnose", "Moderate"]);
    expect(screen.getByText("Moderate").closest("li")).toHaveAttribute("aria-current", "step");
  });
});

// ---------------------------------------------------------------------------
// Issue #98, cycle 3 — "Route for moderation" confirms, then files a pending
// workflow item for the Programme Quality Lead under academic_quality. The
// strip then lights Validate.
// ---------------------------------------------------------------------------

describe("Route for moderation", () => {
  function routeButton() {
    return screen.getByRole("button", { name: /route for moderation/i });
  }

  it("opens a confirm dialog from the variance card", () => {
    renderResolvedPage();

    const card = screen.getByRole("region", { name: /moderation variance/i });
    fireEvent.click(within(card).getByRole("button", { name: /route for moderation/i }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/Programme Quality Lead/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("cancelling closes the dialog without filing anything", () => {
    renderResolvedPage();

    fireEvent.click(routeButton());
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
    expect(litStepNames()).toEqual(["Measure", "Diagnose", "Moderate"]);
  });

  it("confirming files one pending academic_quality item for the Programme Quality Lead", async () => {
    renderResolvedPage();

    fireEvent.click(routeButton());
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      const postCalls = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.filter(
        ([, opts]: any[]) => opts?.method === "POST"
      );
      expect(postCalls).toHaveLength(1);
      expect(postCalls[0][0]).toMatch(/\/api\/workflows$/);
      const body = JSON.parse(postCalls[0][1].body as string);
      expect(body).toMatchObject({
        stage: "academic_quality",
        owner_name: "Programme Quality Lead",
        status: "pending",
        trigger: CS101_FLAG.trigger,
      });
      expect(body.description).toMatch(/CS101-SLO1/);
    });
  });

  it("lights Validate and marks the card routed once the item is filed", async () => {
    renderResolvedPage();

    fireEvent.click(routeButton());
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      expect(litStepNames()).toEqual(["Measure", "Diagnose", "Moderate", "Validate"]);
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /route for moderation/i })).not.toBeInTheDocument();
    const card = screen.getByRole("region", { name: /moderation variance/i });
    expect(within(card).getByText(/routed for moderation/i)).toBeInTheDocument();
    expect(screen.getByText(/open flags/i)).toHaveTextContent("Open flags: 0");
    expect(screen.getByText(/^routed:/i)).toHaveTextContent("Routed: 1");
  });

  it("shows a flag the backend already reports as routed at Validate, with no button", () => {
    renderResolvedPage({
      ...MOCK_PROFILE,
      stage_summary: { ...MOCK_PROFILE.stage_summary, health: "watch", open_flag_count: 0, routed_flag_count: 1 },
      moderation_variance_flags: [
        {
          ...CS101_FLAG,
          routed_item: {
            id: "wfl-123",
            owner_name: "Programme Quality Lead",
            owner_role: "programme quality lead",
            status: "pending",
            created_date: "2026-09-26",
          },
        },
      ],
    });

    expect(litStepNames()).toEqual(["Measure", "Diagnose", "Moderate", "Validate"]);
    expect(screen.queryByRole("button", { name: /route for moderation/i })).not.toBeInTheDocument();
    expect(screen.getByText(/routed for moderation/i)).toBeInTheDocument();
  });

  it("lights only Measure and Diagnose when nothing is flagged", () => {
    renderResolvedPage({
      ...MOCK_PROFILE,
      stage_summary: { ...MOCK_PROFILE.stage_summary, health: "on_track", open_flag_count: 0, routed_flag_count: 0 },
      moderation_variance_flags: [],
    });

    expect(litStepNames()).toEqual(["Measure", "Diagnose"]);
    expect(screen.getByText(/no marking variance detected/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Issue #97 — the SLO → CLO → PLO attainment chain. Each Computer Science PLO
// is a bar against the 70% target; a PLO expands to the courses feeding it
// (the CLO level) and, under each course, its SLOs with their rates and the
// semester they were last assessed. The header badge follows the PLOs.
// ---------------------------------------------------------------------------

describe("PLO attainment chain", () => {
  function chain() {
    return screen.getByRole("region", { name: /program learning outcomes/i });
  }

  function ploRow(code: string) {
    return within(chain()).getByRole("group", { name: new RegExp(`^${code}\\b`) });
  }

  it("draws one bar per PLO against the 70% target and says which side of it each sits", () => {
    renderResolvedPage();

    expect(within(chain()).getByText(/Computer Science/)).toBeInTheDocument();
    const bars = within(chain()).getAllByRole("progressbar");
    expect(bars).toHaveLength(2);

    const plo1 = ploRow("PLO1");
    expect(within(plo1).getByText("Program and build software")).toBeInTheDocument();
    const bar = within(plo1).getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "66");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
    expect(within(plo1).getByText("66%")).toBeInTheDocument();
    expect(within(plo1).getByLabelText(/70% target/i)).toBeInTheDocument();
    expect(within(plo1).getByText(/below target/i)).toBeInTheDocument();

    const plo4 = ploRow("PLO4");
    expect(within(plo4).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "74");
    expect(within(plo4).getByText(/on target/i)).toBeInTheDocument();
  });

  it("expands a PLO to the courses feeding it and their SLOs with rate and last assessed semester", () => {
    renderResolvedPage();

    const toggle = within(ploRow("PLO1")).getByRole("button", { name: /PLO1/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(chain()).queryByText("CS101-SLO1")).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const cs101 = within(ploRow("PLO1")).getByRole("group", { name: /^CS101 — Introduction to Computer Science/ });
    expect(within(cs101).getByText("73%", { selector: "[data-level='course']" })).toBeInTheDocument();
    const slo = within(cs101).getByRole("listitem", { name: "CS101-SLO1" });
    expect(within(slo).getByText("73%")).toBeInTheDocument();
    expect(within(slo).getByText(/last assessed 2024-Fall/i)).toBeInTheDocument();

    const cs401 = within(ploRow("PLO1")).getByRole("group", { name: /^CS401 — Software Engineering/ });
    expect(within(cs401).getAllByText(/not yet assessed/i).length).toBeGreaterThan(0);

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(chain()).queryByText("CS101-SLO1")).not.toBeInTheDocument();
  });

  it("carries the health badge in the header and counts the PLOs below target", () => {
    renderResolvedPage();

    const header = screen.getByRole("heading", { level: 1, name: "Moderation and Validation" }).closest("header")!;
    expect(within(header).getByText("Needs Attention")).toBeInTheDocument();
    expect(within(header).getByText(/PLOs below target/i)).toHaveTextContent("PLOs below target: 1 of 2");
  });
});

// ---------------------------------------------------------------------------
// Issue #99 — Agent 10 narrates the diagnosis. The numbers and the red card
// render at once from the base event; the Diagnosis paragraph shows the canned
// text under an "AI refining…" badge until the agent's field event lands.
// ---------------------------------------------------------------------------

describe("Diagnosis", () => {
  function diagnosis() {
    return screen.getByRole("region", { name: /^diagnosis$/i });
  }

  it("shows the canned diagnosis under a refining badge as soon as the base profile renders", () => {
    render(<AcademicQualityPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });

    expect(within(diagnosis()).getByRole("heading", { name: "Diagnosis" })).toBeInTheDocument();
    expect(within(diagnosis()).getByText(/moderate CS101-SLO1 first/)).toBeInTheDocument();
    expect(within(diagnosis()).getByText(/AI refining/i)).toBeInTheDocument();
    // The numbers never wait on the agent.
    expect(screen.getByRole("region", { name: /moderation variance/i })).toBeInTheDocument();
  });

  it("swaps in the agent's paragraph when its field event arrives and clears the badge on done", () => {
    render(<AcademicQualityPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", MOCK_PROFILE);
    });
    act(() => {
      es.emit("field", {
        path: "diagnosis",
        value: "Live agent: the 37-point gap between CS101-01 and CS101-02 on CS101-SLO1 reads as marking inconsistency.",
      });
    });

    expect(within(diagnosis()).getByText(/reads as marking inconsistency/)).toBeInTheDocument();
    expect(within(diagnosis()).queryByText(/moderate CS101-SLO1 first/)).not.toBeInTheDocument();
    expect(within(diagnosis()).getByText(/AI refining/i)).toBeInTheDocument();

    act(() => {
      es.emit("done", {});
    });

    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
    expect(within(diagnosis()).getByText(/reads as marking inconsistency/)).toBeInTheDocument();
  });
});
