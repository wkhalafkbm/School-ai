import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach } from "vitest";
import SignOutButton from "./SignOutButton";

beforeEach(() => {
  sessionStorage.clear();
  Object.defineProperty(window, "location", {
    value: { href: "" },
    writable: true,
    configurable: true,
  });
});

describe("SignOutButton", () => {
  it("renders a sign out button", () => {
    render(<SignOutButton />);
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });

  it("clears sessionStorage.authenticated on click", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("authenticated", "true");
    render(<SignOutButton />);
    await user.click(screen.getByRole("button", { name: /sign out/i }));
    expect(sessionStorage.getItem("authenticated")).toBeNull();
  });

  it("navigates to / on click", async () => {
    const user = userEvent.setup();
    render(<SignOutButton />);
    await user.click(screen.getByRole("button", { name: /sign out/i }));
    expect(window.location.href).toBe("/");
  });
});
