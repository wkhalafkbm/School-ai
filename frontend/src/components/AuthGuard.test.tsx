import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import AuthGuard from "./AuthGuard";

vi.mock("./LoginForm", () => ({
  default: () => <div data-testid="login-form">Login</div>,
}));

beforeEach(() => {
  sessionStorage.clear();
});

describe("AuthGuard", () => {
  it("renders children when sessionStorage authenticated is true", () => {
    sessionStorage.setItem("authenticated", "true");
    render(<AuthGuard><p>protected content</p></AuthGuard>);
    expect(screen.getByText("protected content")).toBeInTheDocument();
    expect(screen.queryByTestId("login-form")).not.toBeInTheDocument();
  });

  it("renders LoginForm when not authenticated", () => {
    render(<AuthGuard><p>protected content</p></AuthGuard>);
    expect(screen.getByTestId("login-form")).toBeInTheDocument();
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });
});
