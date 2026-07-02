import { render, screen } from "@testing-library/react";
import { act } from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import AdmissionsPage from "./page";

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

vi.mock("./AdmissionsActions", () => ({
  default: () => <div data-testid="admissions-actions" />,
}));

const PROFILE = {
  stage_summary: { health: "on_track", applicant_count: 12, pending_review_count: 1 },
  applicant: {
    id: "stu-001",
    name: "Waleed Khalaf",
    nationality: "Kuwaiti",
    admission_term: "2024-Fall",
    program_name: "Computer Science",
    program_interest: "Computer Science",
    degree_level: "Bachelor",
    sponsorship_status: "KFAS eligible",
    financial_readiness: "eligible",
  },
  recommendation: {
    action: "Recommend standard admission pathway",
    confidence: "Medium",
    rationale: "fallback rationale text",
  },
  evidence: {
    graduate_outcomes: [],
    signal_strength: "medium",
    data_completeness: "partial",
  },
};

beforeEach(() => {
  StubEventSource.instances = [];
  vi.stubGlobal("EventSource", StubEventSource);
});

describe("AdmissionsPage", () => {
  it("renders fallback text on base, updates on field, and hides the badge on done", () => {
    render(<AdmissionsPage />);
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", PROFILE);
    });

    expect(screen.getByText("fallback rationale text")).toBeInTheDocument();
    expect(screen.getByText(/AI refining/i)).toBeInTheDocument();

    act(() => {
      es.emit("field", { path: "recommendation.rationale", value: "live rationale text" });
    });

    expect(screen.getByText("live rationale text")).toBeInTheDocument();
    expect(screen.getByText(/AI refining/i)).toBeInTheDocument();

    act(() => {
      es.emit("done", {});
    });

    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
  });
});
