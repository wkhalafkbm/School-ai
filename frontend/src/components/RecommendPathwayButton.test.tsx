import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import RecommendPathwayButton from "./RecommendPathwayButton";

describe("RecommendPathwayButton", () => {
  it("renders the Recommend Pathway button", () => {
    render(<RecommendPathwayButton onApprove={vi.fn()} />);
    expect(screen.getByRole("button", { name: /recommend pathway/i })).toBeInTheDocument();
  });

  it("modal is not shown by default", () => {
    render(<RecommendPathwayButton onApprove={vi.fn()} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens a confirmation modal on button click", () => {
    render(<RecommendPathwayButton onApprove={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /recommend pathway/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("modal contains a Confirm action", () => {
    render(<RecommendPathwayButton onApprove={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /recommend pathway/i }));
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
  });

  it("modal contains a Cancel action", () => {
    render(<RecommendPathwayButton onApprove={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /recommend pathway/i }));
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("cancel closes the modal without calling onApprove", () => {
    const onApprove = vi.fn();
    render(<RecommendPathwayButton onApprove={onApprove} />);
    fireEvent.click(screen.getByRole("button", { name: /recommend pathway/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(onApprove).not.toHaveBeenCalled();
  });

  it("confirming calls onApprove and closes the modal", () => {
    const onApprove = vi.fn();
    render(<RecommendPathwayButton onApprove={onApprove} />);
    fireEvent.click(screen.getByRole("button", { name: /recommend pathway/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
    expect(onApprove).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
