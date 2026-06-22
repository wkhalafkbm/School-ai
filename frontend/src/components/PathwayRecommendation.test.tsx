import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PathwayRecommendation from "./PathwayRecommendation";

const RECOMMENDATION = {
  action: "Recommend standard admission pathway",
  confidence: "Medium" as const,
  rationale:
    "Applicant profile aligns with program benchmarks. Sponsorship eligibility confirmed through KFAS.",
};

describe("PathwayRecommendation", () => {
  it("displays the confidence label", () => {
    render(<PathwayRecommendation recommendation={RECOMMENDATION} />);
    expect(screen.getByTestId("confidence-label")).toHaveTextContent("Medium");
  });

  it("displays the rationale text", () => {
    render(<PathwayRecommendation recommendation={RECOMMENDATION} />);
    expect(screen.getByTestId("rationale")).toHaveTextContent(
      "Applicant profile aligns with program benchmarks"
    );
  });

  it("displays the recommended action", () => {
    render(<PathwayRecommendation recommendation={RECOMMENDATION} />);
    expect(screen.getByTestId("recommendation-action")).toHaveTextContent(
      "Recommend standard admission pathway"
    );
  });

  it("uses the confidence level as an accent, not a page fill", () => {
    const { container } = render(
      <PathwayRecommendation recommendation={{ ...RECOMMENDATION, confidence: "Low" }} />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper?.className).not.toMatch(/bg-red/);
  });
});
