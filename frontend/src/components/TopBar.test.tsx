import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import TopBar from "./TopBar";

describe("TopBar", () => {
  it("shows the default university name when env var is absent", () => {
    render(<TopBar />);
    expect(screen.getByText("University AI Operating Center")).toBeInTheDocument();
  });

  it("shows the university name from NEXT_PUBLIC_UNIVERSITY_NAME", () => {
    const original = process.env.NEXT_PUBLIC_UNIVERSITY_NAME;
    process.env.NEXT_PUBLIC_UNIVERSITY_NAME = "King Salman University";
    render(<TopBar />);
    expect(screen.getByText("King Salman University")).toBeInTheDocument();
    process.env.NEXT_PUBLIC_UNIVERSITY_NAME = original;
  });
});
