import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import TopBar from "./TopBar";

vi.mock("./SignOutButton", () => ({ default: () => null }));

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

  it("shows default subtitle", () => {
    render(<TopBar />);
    expect(screen.getByText("Student Journey Intelligence Layer")).toBeInTheDocument();
  });

  it("shows subtitle from NEXT_PUBLIC_UNIVERSITY_SUBTITLE", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE;
    process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE = "Intelligent Student Services";
    render(<TopBar />);
    expect(screen.getByText("Intelligent Student Services")).toBeInTheDocument();
    process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE = orig;
  });

  it("shows logo image when NEXT_PUBLIC_UNIVERSITY_LOGO_URL is set", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = "https://example.com/logo.png";
    render(<TopBar />);
    expect(screen.getByRole("img", { name: /university logo/i })).toHaveAttribute(
      "src",
      "https://example.com/logo.png"
    );
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = orig;
  });

  it("logo img has explicit width and height to prevent layout shift", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = "https://example.com/logo.png";
    render(<TopBar />);
    const img = screen.getByRole("img", { name: /university logo/i });
    expect(img).toHaveAttribute("width", "36");
    expect(img).toHaveAttribute("height", "36");
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = orig;
  });

  it("shows text fallback when NEXT_PUBLIC_UNIVERSITY_LOGO_URL is not set", () => {
    delete process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
    render(<TopBar />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByTestId("logo-fallback")).toBeInTheDocument();
  });
});
