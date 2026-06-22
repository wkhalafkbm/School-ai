import time

import httpx
import pytest

import app.gateway.iam as iam_module
import app.gateway.orchestrate as orchestrate_module
from app.main import app

WXO_BASE = "https://wxo.example.com"
AGENT_ADMISSIONS = "agent-admissions-001"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"


@pytest.fixture(autouse=True)
def reset_iam():
    iam_module._token = None
    iam_module._expires_at = 0.0
    yield


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _mock_iam_and_run(router, run_id: str, final_status: str) -> None:
    router.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
    )
    router.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": run_id})
    )
    router.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/{run_id}").mock(
        return_value=httpx.Response(200, json={"status": final_status, "output": {}})
    )


# ---------------------------------------------------------------------------
# Tracer bullet: success path
# ---------------------------------------------------------------------------

async def test_admissions_success_returns_live_result(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)

    respx_mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
    )
    respx_mock.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": "run-001"})
    )
    respx_mock.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/run-001").mock(
        return_value=httpx.Response(
            200,
            json={"status": "completed", "output": {"result": "Strong pathway fit for Computer Science."}},
        )
    )

    response = await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "admissions"
    assert body["source"] == "live"
    assert body["result"] == "Strong pathway fit for Computer Science."


# ---------------------------------------------------------------------------
# Cycles 2 & 3: fallback on failed / expired run
# ---------------------------------------------------------------------------

async def test_fallback_when_run_fails(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)
    _mock_iam_and_run(respx_mock, "run-fail", "failed")

    response = await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert response.json()["stage"] == "admissions", "failed run must return admissions stage"


async def test_fallback_when_run_expires(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)
    _mock_iam_and_run(respx_mock, "run-exp", "expired")

    response = await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert response.json()["stage"] == "admissions"


# ---------------------------------------------------------------------------
# Cycle 4: IAM token is fetched before the run call
# ---------------------------------------------------------------------------

async def test_iam_token_fetched_exactly_once_per_request(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)

    iam_route = respx_mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
    )
    respx_mock.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": "run-iam"})
    )
    respx_mock.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/run-iam").mock(
        return_value=httpx.Response(
            200, json={"status": "completed", "output": {"result": "Fit confirmed."}}
        )
    )

    await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert iam_route.called, "IAM token endpoint must be called"
    assert iam_route.call_count == 1


# ---------------------------------------------------------------------------
# Cycle 5: stale token (within 5-min buffer) is refreshed
# ---------------------------------------------------------------------------

async def test_iam_token_refreshed_when_near_expiry(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)

    iam_module._token = "stale-token"
    iam_module._expires_at = time.time() + 200

    iam_route = respx_mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "fresh-token", "expires_in": 3600})
    )
    respx_mock.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": "run-refresh"})
    )
    respx_mock.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/run-refresh").mock(
        return_value=httpx.Response(
            200, json={"status": "completed", "output": {"result": "Refreshed."}}
        )
    )

    await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert iam_route.called, "IAM must be called to refresh a near-expiry token"


# ---------------------------------------------------------------------------
# Cycle 5b: valid token (well within expiry) is reused — no IAM call
# ---------------------------------------------------------------------------

async def test_valid_token_is_reused_without_iam_call(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)

    iam_module._token = "cached-token"
    iam_module._expires_at = time.time() + 1800

    iam_route = respx_mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "new-token", "expires_in": 3600})
    )
    respx_mock.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": "run-cached"})
    )
    respx_mock.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/run-cached").mock(
        return_value=httpx.Response(
            200, json={"status": "completed", "output": {"result": "Cached token used."}}
        )
    )

    await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert not iam_route.called, "IAM must NOT be called when token is still valid"


# ---------------------------------------------------------------------------
# Cycle 6: unknown stage returns 422
# ---------------------------------------------------------------------------

async def test_unknown_stage_returns_422(client):
    response = await client.post(
        "/api/recommendations/nonexistent_stage",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "anything"},
    )
    assert response.status_code == 422
    assert "nonexistent_stage" in response.json()["detail"]


# ---------------------------------------------------------------------------
# AC3: gateway polls until terminal status (in_progress → completed)
# ---------------------------------------------------------------------------

async def test_gateway_polls_until_completed(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    respx_mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
    )
    respx_mock.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": "run-poll"})
    )

    _poll_count = 0

    def poll_side_effect(request):
        nonlocal _poll_count
        _poll_count += 1
        if _poll_count < 3:
            return httpx.Response(200, json={"status": "in_progress", "output": {}})
        return httpx.Response(
            200, json={"status": "completed", "output": {"result": "Polling complete."}}
        )

    respx_mock.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/run-poll").mock(
        side_effect=poll_side_effect
    )

    response = await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "live"
    assert _poll_count == 3, f"Expected 3 polls (2 in_progress + 1 completed), got {_poll_count}"


# ---------------------------------------------------------------------------
# AC7: no IBM / Orchestrate branding in the response sent to the frontend
# ---------------------------------------------------------------------------

_BRANDED_TERMS = {"run_id", "agent_id", "orchestrate", "ibm", "watson", "wxo", "instance_id"}


async def test_live_response_contains_no_ibm_branding(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)

    respx_mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
    )
    respx_mock.post(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs").mock(
        return_value=httpx.Response(200, json={"run_id": "run-brand"})
    )
    respx_mock.get(f"{WXO_BASE}/agents/{AGENT_ADMISSIONS}/runs/run-brand").mock(
        return_value=httpx.Response(
            200, json={"status": "completed", "output": {"result": "Good fit."}}
        )
    )

    response = await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    body = response.json()
    leaked = {k for k in body if k.lower() in _BRANDED_TERMS}
    assert not leaked, f"Branded field(s) leaked into response: {leaked}"


async def test_fallback_response_contains_no_ibm_branding(monkeypatch, client, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ADMISSIONS", AGENT_ADMISSIONS)
    _mock_iam_and_run(respx_mock, "run-brand-fb", "failed")

    response = await client.post(
        "/api/recommendations/admissions",
        json={"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"},
    )

    body = response.json()
    leaked = {k for k in body if k.lower() in _BRANDED_TERMS}
    assert not leaked, f"Branded field(s) leaked into fallback response: {leaked}"
