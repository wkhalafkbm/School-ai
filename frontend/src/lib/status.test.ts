import { describe, it, expect } from "vitest";
import { STATUS_CLASSES, StatusCode } from "./status";

const ALL_CODES: StatusCode[] = ["on_track", "watch", "needs_attention", "urgent", "opportunity"];

describe("STATUS_CLASSES", () => {
  it("returns non-empty classes for on_track", () => {
    expect(STATUS_CLASSES["on_track"]).toBeTruthy();
  });

  it("has non-empty label and classes for every status code", () => {
    for (const code of ALL_CODES) {
      expect(STATUS_CLASSES[code].label).toBeTruthy();
      expect(STATUS_CLASSES[code].classes).toBeTruthy();
    }
  });
});
