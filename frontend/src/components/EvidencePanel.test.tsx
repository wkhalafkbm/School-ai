import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import EvidencePanel from "./EvidencePanel";

const EVIDENCE = {
  graduate_outcomes: [
    { profile: "Kuwaiti applicants — Computer Science", outcome: "82% on track for on-time graduation", cohort_size: 14 },
  ],
  signal_strength: "medium" as const,
  data_completeness: "partial" as const,
};

describe("EvidencePanel", () => {
  it("renders an expand trigger", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    expect(screen.getByRole("button", { name: /evidence/i })).toBeInTheDocument();
  });

  it("graduate outcomes are hidden by default", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    expect(screen.queryByTestId("graduate-outcomes")).toBeNull();
  });

  it("shows graduate outcomes after expanding", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    fireEvent.click(screen.getByRole("button", { name: /evidence/i }));
    expect(screen.getByTestId("graduate-outcomes")).toBeInTheDocument();
  });

  it("shows profile, outcome, and cohort size when expanded", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    fireEvent.click(screen.getByRole("button", { name: /evidence/i }));
    expect(screen.getByText("Kuwaiti applicants — Computer Science")).toBeInTheDocument();
    expect(screen.getByText("82% on track for on-time graduation")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });

  it("shows signal strength when expanded", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    fireEvent.click(screen.getByRole("button", { name: /evidence/i }));
    expect(screen.getByTestId("signal-strength")).toHaveTextContent("medium");
  });

  it("shows data completeness when expanded", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    fireEvent.click(screen.getByRole("button", { name: /evidence/i }));
    expect(screen.getByTestId("data-completeness")).toHaveTextContent("partial");
  });

  it("collapses again on second click", () => {
    render(<EvidencePanel evidence={EVIDENCE} />);
    const btn = screen.getByRole("button", { name: /evidence/i });
    fireEvent.click(btn);
    fireEvent.click(btn);
    expect(screen.queryByTestId("graduate-outcomes")).toBeNull();
  });
});
