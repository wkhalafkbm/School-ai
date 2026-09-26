import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AcademicQualityPage from "./page";

// Issue #96 — /academic-quality is the home of Agent 10 (academic outcomes &
// quality intelligence). A placeholder header is enough for this ticket.
describe("AcademicQualityPage", () => {
  it("renders the Academic Quality stage heading", () => {
    render(<AcademicQualityPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Academic Quality" })
    ).toBeInTheDocument();
  });

  it("renders inside a main landmark like the other stage pages", () => {
    render(<AcademicQualityPage />);
    expect(screen.getByRole("main")).toBeInTheDocument();
  });
});
