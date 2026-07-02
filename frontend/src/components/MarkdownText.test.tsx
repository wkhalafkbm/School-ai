import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import MarkdownText from "./MarkdownText";

describe("MarkdownText", () => {
  it("renders GFM markdown as real HTML elements, not raw syntax", () => {
    const markdown = [
      "**bold** and *italic* text",
      "",
      "- item one",
      "- item two",
      "",
      "| Col A | Col B |",
      "| --- | --- |",
      "| 1 | 2 |",
    ].join("\n");

    const { container } = render(<MarkdownText text={markdown} />);

    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelector("strong")).not.toBeNull();
    expect(container.querySelector("ul")).not.toBeNull();
    expect(container.textContent).not.toContain("**bold**");
    expect(container.textContent).not.toContain("| Col A | Col B |");
  });

  it("wraps rendered markdown in a prose container for typography styling", () => {
    const { container } = render(<MarkdownText text="hello world" />);
    const wrapper = container.firstElementChild;
    expect(wrapper).not.toBeNull();
    expect(wrapper!.className).toContain("prose");
  });

  it("renders embedded raw HTML like <br> as a real element", () => {
    const markdown = "| Col A |\n| --- |\n| line one<br>line two |";

    const { container } = render(<MarkdownText text={markdown} />);

    expect(container.querySelector("br")).not.toBeNull();
    expect(container.textContent).not.toContain("<br>");
  });

  it("strips dangerous embedded HTML like <script> and event handlers", () => {
    const markdown =
      'safe text<script>window.hacked = true;</script><img src="x" onerror="window.hacked = true;" />';

    const { container } = render(<MarkdownText text={markdown} />);

    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).not.toContain("hacked");
    const img = container.querySelector("img");
    expect(img === null || img.getAttribute("onerror")).not.toBe(
      "window.hacked = true;",
    );
  });
});
