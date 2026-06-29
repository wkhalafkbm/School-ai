import { describe, it, expect } from "vitest";
import { STATUS_CLASSES, WORKFLOW_STATUS_MAP, StatusCode, WorkflowStatus } from "./status";

const ALL_CODES: StatusCode[] = ["on_track", "watch", "needs_attention", "urgent", "opportunity"];

const ALL_WORKFLOW_STATUSES: WorkflowStatus[] = [
  "pending",
  "in_review",
  "in_progress",
  "completed",
  "overdue",
  "blocked",
];

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

// ---------------------------------------------------------------------------
// WORKFLOW_STATUS_MAP — exhaustive mapping, no silent fallback
// ---------------------------------------------------------------------------

describe("WORKFLOW_STATUS_MAP", () => {
  it("covers every WorkflowStatus value", () => {
    for (const status of ALL_WORKFLOW_STATUSES) {
      expect(WORKFLOW_STATUS_MAP[status]).toBeTruthy();
    }
  });

  it("maps every WorkflowStatus to a valid StatusCode with a label", () => {
    for (const status of ALL_WORKFLOW_STATUSES) {
      const code = WORKFLOW_STATUS_MAP[status];
      expect(STATUS_CLASSES[code].label).toBeTruthy();
    }
  });

  it("has no extra keys beyond the declared WorkflowStatus union", () => {
    const keys = Object.keys(WORKFLOW_STATUS_MAP);
    expect(keys).toHaveLength(ALL_WORKFLOW_STATUSES.length);
    for (const key of keys) {
      expect(ALL_WORKFLOW_STATUSES).toContain(key);
    }
  });
});
