import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import LoginForm from "./LoginForm";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockPush = vi.fn();

beforeEach(() => {
  mockPush.mockClear();
  sessionStorage.clear();
});

describe("LoginForm — branding", () => {
  it("renders default university name", () => {
    render(<LoginForm />);
    expect(screen.getByText("University AI Operating Center")).toBeInTheDocument();
  });

  it("renders university name from NEXT_PUBLIC_UNIVERSITY_NAME", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_NAME;
    process.env.NEXT_PUBLIC_UNIVERSITY_NAME = "King Salman University";
    render(<LoginForm />);
    expect(screen.getByText("King Salman University")).toBeInTheDocument();
    process.env.NEXT_PUBLIC_UNIVERSITY_NAME = orig;
  });

  it("renders default subtitle", () => {
    render(<LoginForm />);
    expect(screen.getByText("Student Journey Intelligence Layer")).toBeInTheDocument();
  });

  it("renders subtitle from NEXT_PUBLIC_UNIVERSITY_SUBTITLE", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE;
    process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE = "Intelligent Student Services";
    render(<LoginForm />);
    expect(screen.getByText("Intelligent Student Services")).toBeInTheDocument();
    process.env.NEXT_PUBLIC_UNIVERSITY_SUBTITLE = orig;
  });

  it("shows logo image when NEXT_PUBLIC_UNIVERSITY_LOGO_URL is set", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = "https://example.com/logo.png";
    render(<LoginForm />);
    expect(screen.getByRole("img", { name: /university logo/i })).toHaveAttribute(
      "src",
      "https://example.com/logo.png"
    );
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = orig;
  });

  it("logo img has explicit width and height to prevent layout shift", () => {
    const orig = process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = "https://example.com/logo.png";
    render(<LoginForm />);
    const img = screen.getByRole("img", { name: /university logo/i });
    expect(img).toHaveAttribute("width", "56");
    expect(img).toHaveAttribute("height", "56");
    process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL = orig;
  });

  it("shows text fallback when NEXT_PUBLIC_UNIVERSITY_LOGO_URL is not set", () => {
    delete process.env.NEXT_PUBLIC_UNIVERSITY_LOGO_URL;
    render(<LoginForm />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByTestId("logo-fallback")).toBeInTheDocument();
  });
});

describe("LoginForm — form fields", () => {
  it("has a username field, password field, and submit button", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });
});

describe("LoginForm — submit behavior", () => {
  it("navigates to / when non-empty credentials are submitted", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.type(screen.getByLabelText(/username/i), "admin");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("does not navigate when username is empty", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("does not navigate when password is empty", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.type(screen.getByLabelText(/username/i), "admin");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(mockPush).not.toHaveBeenCalled();
  });
});
