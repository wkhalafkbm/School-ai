import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ApplicantCard from "./ApplicantCard";

const APPLICANT = {
  id: "stu-001",
  name: "Waleed Khalaf",
  nationality: "Kuwaiti",
  admission_term: "2024-Fall",
  program_name: "Computer Science",
  program_interest: "Computer Science",
  degree_level: "Bachelor",
  sponsorship_status: "KFAS eligible",
  financial_readiness: "eligible",
};

describe("ApplicantCard", () => {
  it("displays the applicant name", () => {
    render(<ApplicantCard applicant={APPLICANT} />);
    expect(screen.getByText("Waleed Khalaf")).toBeInTheDocument();
  });

  it("displays the program name", () => {
    render(<ApplicantCard applicant={APPLICANT} />);
    expect(screen.getByText("Computer Science")).toBeInTheDocument();
  });

  it("displays the admission term", () => {
    render(<ApplicantCard applicant={APPLICANT} />);
    expect(screen.getByText("2024-Fall")).toBeInTheDocument();
  });

  it("displays sponsorship status", () => {
    render(<ApplicantCard applicant={APPLICANT} />);
    expect(screen.getByText("KFAS eligible")).toBeInTheDocument();
  });

  it("displays financial readiness", () => {
    render(<ApplicantCard applicant={APPLICANT} />);
    expect(screen.getByText("eligible")).toBeInTheDocument();
  });

  it("displays nationality", () => {
    render(<ApplicantCard applicant={APPLICANT} />);
    expect(screen.getByText("Kuwaiti")).toBeInTheDocument();
  });

  it("does not show any financial impact estimate", () => {
    const { container } = render(<ApplicantCard applicant={APPLICANT} />);
    expect(container.textContent).not.toMatch(/financial.impact/i);
    expect(container.textContent).not.toMatch(/tuition.revenue/i);
    expect(container.textContent).not.toMatch(/cost.estimate/i);
  });
});
