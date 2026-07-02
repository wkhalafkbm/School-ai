import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StreamedField from "./StreamedField";

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: badge visible while unresolved
// ---------------------------------------------------------------------------

describe("StreamedField", () => {
  it("shows the refining badge and renders children when resolved=false", () => {
    render(
      <StreamedField resolved={false}>
        <p>fallback text</p>
      </StreamedField>
    );

    expect(screen.getByText("fallback text")).toBeInTheDocument();
    expect(screen.getByText(/AI refining/i)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — badge hidden once resolved
  // -------------------------------------------------------------------------

  it("hides the refining badge when resolved=true", () => {
    render(
      <StreamedField resolved={true}>
        <p>live text</p>
      </StreamedField>
    );

    expect(screen.getByText("live text")).toBeInTheDocument();
    expect(screen.queryByText(/AI refining/i)).not.toBeInTheDocument();
  });
});
