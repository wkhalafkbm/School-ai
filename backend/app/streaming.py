import asyncio
import json
import os
from typing import AsyncGenerator, Awaitable, Callable

ResolverFn = Callable[[], Awaitable[str]]


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def resolve_or_fallback(fallback: str, live_call: Callable[[], Awaitable[str | None]]) -> str:
    if os.getenv("AI_MODE", "live") == "scripted":
        return fallback
    result = await live_call()
    return result if result is not None else fallback


def set_nested(target: dict, path: str, value) -> None:
    *parents, leaf = path.split(".")
    node = target
    for key in parents:
        node = node[key]
    node[leaf] = value


async def _resolve_field(path: str, resolver: ResolverFn) -> tuple[str, str]:
    value = await resolver()
    return path, value


async def stream_profile(base: dict, resolvers: dict[str, ResolverFn]) -> AsyncGenerator[str, None]:
    yield sse_event("base", base)

    pending = [_resolve_field(path, resolver) for path, resolver in resolvers.items()]
    for coro in asyncio.as_completed(pending):
        path, value = await coro
        yield sse_event("field", {"path": path, "value": value})

    yield sse_event("done", {})
