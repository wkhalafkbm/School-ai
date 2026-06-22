import httpx
import pytest
import respx as _respx
from respx.mocks import HTTPCoreMocker
from respx.patterns import parse_url


def _fixed_to_httpx_request(cls, **kwargs):
    """
    Drop-in replacement for HTTPCoreMocker.to_httpx_request that decodes the
    httpcore method bytes to str before constructing httpx.Request.

    httpx >= 0.27 stopped auto-converting bytes methods, so the default respx
    0.21 implementation passes b'POST' through unchanged, causing Method pattern
    matching to fail silently (b'POST' != 'POST').
    """
    request = kwargs["request"]
    raw_url = (
        request.url.scheme,
        request.url.host,
        request.url.port,
        request.url.target,
    )
    method = request.method
    if isinstance(method, bytes):
        method = method.decode("ascii").upper()
    return httpx.Request(
        method,
        parse_url(raw_url),
        headers=request.headers,
        stream=request.stream,
        extensions=request.extensions,
    )


@pytest.fixture(autouse=True, scope="session")
def fix_respx_httpcore_bytes():
    """Patch HTTPCoreMocker once per session to fix the bytes-method bug."""
    original = HTTPCoreMocker.__dict__["to_httpx_request"]
    HTTPCoreMocker.to_httpx_request = classmethod(_fixed_to_httpx_request)
    yield
    HTTPCoreMocker.to_httpx_request = original


@pytest.fixture
async def respx_mock():
    """Async version of the respx_mock fixture so the mock context lives inside
    each test's own event loop (needed for pytest-asyncio function-scope loops)."""
    async with _respx.MockRouter(assert_all_mocked=True, assert_all_called=False) as router:
        yield router
