import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useStreamedProfile } from "./useStreamedProfile";

class StubEventSource {
  static instances: StubEventSource[] = [];
  listeners: Record<string, ((event: { data: string }) => void)[]> = {};
  closed = false;
  onerror: ((event: unknown) => void) | null = null;

  constructor(public url: string) {
    StubEventSource.instances.push(this);
  }

  addEventListener(type: string, cb: (event: { data: string }) => void) {
    (this.listeners[type] ??= []).push(cb);
  }

  close() {
    this.closed = true;
  }

  emit(type: string, data: unknown) {
    for (const cb of this.listeners[type] ?? []) {
      cb({ data: JSON.stringify(data) });
    }
  }
}

beforeEach(() => {
  StubEventSource.instances = [];
  vi.stubGlobal("EventSource", StubEventSource);
});

// ---------------------------------------------------------------------------
// Cycle 1 — tracer bullet: the "base" event populates data and marks connected
// ---------------------------------------------------------------------------

describe("useStreamedProfile", () => {
  it("sets data and connected=true on the base event", () => {
    const { result } = renderHook(() => useStreamedProfile("/api/stream"));
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", { recommendation: { rationale: "fallback" } });
    });

    expect(result.current.data).toEqual({ recommendation: { rationale: "fallback" } });
    expect(result.current.connected).toBe(true);
  });

  // -------------------------------------------------------------------------
  // Cycle 2 — the "field" event patches the dotted path into existing data
  // -------------------------------------------------------------------------

  it("patches data at the dotted path on a field event, leaving other fields intact", () => {
    const { result } = renderHook(() => useStreamedProfile("/api/stream"));
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("base", {
        recommendation: { rationale: "fallback", action: "keep me" },
      });
    });
    act(() => {
      es.emit("field", { path: "recommendation.rationale", value: "live text" });
    });

    expect(result.current.data).toEqual({
      recommendation: { rationale: "live text", action: "keep me" },
    });
  });

  // -------------------------------------------------------------------------
  // Cycle 3 — the "done" event sets done=true and closes the connection
  // -------------------------------------------------------------------------

  it("sets done=true and closes the EventSource on the done event", () => {
    const { result } = renderHook(() => useStreamedProfile("/api/stream"));
    const es = StubEventSource.instances[0];

    act(() => {
      es.emit("done", {});
    });

    expect(result.current.done).toBe(true);
    expect(es.closed).toBe(true);
  });

  // -------------------------------------------------------------------------
  // Cycle 4 — onerror sets error and closes the connection early
  // -------------------------------------------------------------------------

  it("sets error and closes the EventSource on early onerror", () => {
    const { result } = renderHook(() => useStreamedProfile("/api/stream"));
    const es = StubEventSource.instances[0];

    act(() => {
      es.onerror?.(new Event("error"));
    });

    expect(result.current.error).not.toBeNull();
    expect(es.closed).toBe(true);
  });

  // -------------------------------------------------------------------------
  // Cycle 5 — unmounting the hook closes the EventSource
  // -------------------------------------------------------------------------

  it("closes the EventSource on unmount", () => {
    const { unmount } = renderHook(() => useStreamedProfile("/api/stream"));
    const es = StubEventSource.instances[0];

    unmount();

    expect(es.closed).toBe(true);
  });
});
