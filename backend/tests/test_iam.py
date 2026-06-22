import time

import httpx
import pytest
import respx

import app.gateway.iam as iam_module

IAM_URL = "https://iam.cloud.ibm.com/identity/token"


@pytest.fixture(autouse=True)
def reset_token_cache():
    iam_module._token = None
    iam_module._expires_at = 0.0
    yield
    iam_module._token = None
    iam_module._expires_at = 0.0


# ---------------------------------------------------------------------------
# Cycle 1: initial fetch — first call hits IAM and returns the token
# ---------------------------------------------------------------------------

@respx.mock
async def test_initial_fetch_calls_iam_and_returns_token(monkeypatch):
    monkeypatch.setenv("WXO_API_KEY", "test-key")

    respx.post(IAM_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "tok-initial", "expires_in": 3600},
        )
    )

    token = await iam_module.get_token()

    assert token == "tok-initial"
    assert respx.calls.call_count == 1


# ---------------------------------------------------------------------------
# Cycle 2: cache hit — second call returns same token, no new HTTP request
# ---------------------------------------------------------------------------

@respx.mock
async def test_second_call_returns_cached_token_without_http_request(monkeypatch):
    monkeypatch.setenv("WXO_API_KEY", "test-key")

    iam_route = respx.post(IAM_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "tok-cached", "expires_in": 3600},
        )
    )

    first = await iam_module.get_token()
    second = await iam_module.get_token()

    assert first == second == "tok-cached"
    assert iam_route.call_count == 1, "IAM must only be called once when token is still valid"


# ---------------------------------------------------------------------------
# Cycle 3: refresh trigger — token within 5-min buffer is replaced
# ---------------------------------------------------------------------------

@respx.mock
async def test_token_near_expiry_is_refreshed(monkeypatch):
    monkeypatch.setenv("WXO_API_KEY", "test-key")

    # Seed a stale token — expires in 200 s (inside the 300 s refresh window)
    iam_module._token = "stale-tok"
    iam_module._expires_at = time.time() + 200

    iam_route = respx.post(IAM_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "fresh-tok", "expires_in": 3600},
        )
    )

    token = await iam_module.get_token()

    assert token == "fresh-tok", "should return freshly fetched token, not stale one"
    assert iam_route.call_count == 1, "IAM must be called to refresh a near-expiry token"


@respx.mock
async def test_token_well_within_expiry_is_not_refreshed(monkeypatch):
    monkeypatch.setenv("WXO_API_KEY", "test-key")

    # Seed a valid token — 30 minutes remaining (outside the 300 s buffer)
    iam_module._token = "valid-tok"
    iam_module._expires_at = time.time() + 1800

    iam_route = respx.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "new-tok", "expires_in": 3600})
    )

    token = await iam_module.get_token()

    assert token == "valid-tok"
    assert iam_route.call_count == 0, "IAM must NOT be called when token has >5 min remaining"
