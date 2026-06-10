import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Shell from "./Shell";

const mockPathname = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));

describe("Sidebar active state", () => {
  it("marks the current route link as active", () => {
    mockPathname.mockReturnValue("/admissions");
    render(<Shell>page</Shell>);
    const admissionsLink = screen.getByRole("link", { name: "Admissions" });
    expect(admissionsLink).toHaveClass("nav-link--active");
    expect(admissionsLink).toHaveAttribute("aria-current", "page");
  });

  it("does not mark other links as active", () => {
    mockPathname.mockReturnValue("/admissions");
    render(<Shell>page</Shell>);
    const overviewLink = screen.getByRole("link", { name: "Overview" });
    expect(overviewLink).not.toHaveClass("nav-link--active");
  });
});
