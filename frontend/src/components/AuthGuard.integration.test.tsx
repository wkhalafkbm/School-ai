import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach } from "vitest";
import AuthGuard from "./AuthGuard";

beforeEach(() => {
  sessionStorage.clear();
});

describe("AuthGuard — real login flow", () => {
  it("renders children after submitting valid credentials in LoginForm", async () => {
    const user = userEvent.setup();
    render(
      <AuthGuard>
        <p>protected content</p>
      </AuthGuard>
    );

    expect(screen.queryByText("protected content")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/username/i), "admin");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("protected content")).toBeInTheDocument();
  });
});
