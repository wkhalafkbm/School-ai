"""Tests for the generic SSE streaming helper (issue #41)."""

import asyncio
import json

import pytest

from app.streaming import resolve_or_fallback, set_nested, sse_event, stream_profile


# ---------------------------------------------------------------------------
# Cycle 1 — tracer bullet: set_nested sets a flat (top-level) key
# ---------------------------------------------------------------------------

def test_set_nested_sets_flat_key():
    target = {"a": 1}
    set_nested(target, "a", 2)
    assert target == {"a": 2}


# ---------------------------------------------------------------------------
# Cycle 2 — set_nested sets a dotted path into an existing nested dict
# ---------------------------------------------------------------------------

def test_set_nested_sets_dotted_path():
    target = {"recommendation": {"action": "x", "rationale": "old"}}
    set_nested(target, "recommendation.rationale", "new")
    assert target == {"recommendation": {"action": "x", "rationale": "new"}}


# ---------------------------------------------------------------------------
# Cycle 3 — tracer bullet: resolve_or_fallback skips the live call in
# scripted mode and returns the fallback text
# ---------------------------------------------------------------------------

async def test_resolve_or_fallback_skips_live_call_when_scripted(monkeypatch):
    monkeypatch.setenv("AI_MODE", "scripted")

    async def live_call():
        raise AssertionError("live_call must not be invoked in scripted mode")

    result = await resolve_or_fallback("fallback text", live_call)

    assert result == "fallback text"


# ---------------------------------------------------------------------------
# Cycle 4b — tracer bullet: sse_event formats an SSE frame with a JSON body
# ---------------------------------------------------------------------------

def test_sse_event_formats_event_and_json_data():
    frame = sse_event("base", {"a": 1})

    assert frame == f"event: base\ndata: {json.dumps({'a': 1})}\n\n"


# ---------------------------------------------------------------------------
# Cycle 4 — resolve_or_fallback returns the live result when the call
# succeeds, and falls back to the fallback text when it returns None
# ---------------------------------------------------------------------------

async def test_resolve_or_fallback_returns_live_result_when_present(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")

    async def live_call():
        return "live text"

    result = await resolve_or_fallback("fallback text", live_call)

    assert result == "live text"


async def test_resolve_or_fallback_falls_back_when_live_call_returns_none(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")

    async def live_call():
        return None

    result = await resolve_or_fallback("fallback text", live_call)

    assert result == "fallback text"


# ---------------------------------------------------------------------------
# Cycle 5 — tracer bullet: stream_profile yields a base event immediately,
# then a field event once the (single) resolver completes, then done
# ---------------------------------------------------------------------------

async def test_stream_profile_yields_base_then_field_then_done():
    base = {"recommendation": {"rationale": "fallback"}}

    async def resolver():
        return "live rationale"

    resolvers = {"recommendation.rationale": resolver}

    events = [event async for event in stream_profile(base, resolvers)]

    assert events == [
        sse_event("base", base),
        sse_event("field", {"path": "recommendation.rationale", "value": "live rationale"}),
        sse_event("done", {}),
    ]


# ---------------------------------------------------------------------------
# Cycle 6 — field events arrive in completion order, not declaration order
# ---------------------------------------------------------------------------

async def test_stream_profile_field_events_in_completion_order():
    base = {"a": "fallback-a", "b": "fallback-b"}

    async def slow_resolver():
        await asyncio.sleep(0.02)
        return "value-a"

    async def fast_resolver():
        return "value-b"

    # Declared with the slow resolver first; it must still complete second.
    resolvers = {"a": slow_resolver, "b": fast_resolver}

    events = [event async for event in stream_profile(base, resolvers)]

    assert events == [
        sse_event("base", base),
        sse_event("field", {"path": "b", "value": "value-b"}),
        sse_event("field", {"path": "a", "value": "value-a"}),
        sse_event("done", {}),
    ]
