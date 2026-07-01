"""Tests for app.gateway.orchestrate against the real watsonx Orchestrate REST
contract (issue #25): POST/GET {WXO_BASE_URL}/v1/orchestrate/runs, with agent_id
in the request body rather than the URL path, confirmed by observing the actual
HTTP traffic the ibm-watsonx-orchestrate ADK CLI makes against a live instance.
"""

import json

import httpx
import pytest

import app.gateway.orchestrate as orchestrate_module

WXO_BASE = "https://wxo.example.com"
RUNS_URL = f"{WXO_BASE}/v1/orchestrate/runs"


# ---------------------------------------------------------------------------
# Cycle 1: start_run posts to the real endpoint shape and returns run_id
# ---------------------------------------------------------------------------

async def test_start_run_posts_to_runs_endpoint_with_agent_id_in_body(monkeypatch, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)

    route = respx_mock.post(RUNS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "thread_id": "thread-001",
                "run_id": "run-001",
                "task_id": "task-001",
                "message_id": "msg-001",
            },
        )
    )

    run_id = await orchestrate_module.start_run(
        "agent-admissions-001", "tok-abc", {"entity_id": "stu-001", "entity_type": "student", "action": "pathway_fit"}
    )

    assert run_id == "run-001"
    assert route.called
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["agent_id"] == "agent-admissions-001"
    assert sent_body["message"]["role"] == "user"
    assert "stu-001" in sent_body["message"]["content"]
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok-abc"


# ---------------------------------------------------------------------------
# Cycle 2: poll_run extracts the assistant's answer text once completed
# ---------------------------------------------------------------------------

def _completed_run_response(text: str) -> dict:
    return {
        "id": "run-002",
        "status": "completed",
        "result": {
            "data": {
                "message": {
                    "role": "assistant",
                    "content": [{"id": "1", "response_type": "text", "text": text}],
                }
            }
        },
    }


async def test_poll_run_returns_completed_status_with_extracted_result_text(monkeypatch, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    respx_mock.get(f"{RUNS_URL}/run-002").mock(
        return_value=httpx.Response(200, json=_completed_run_response("Strong pathway fit for Computer Science."))
    )

    result = await orchestrate_module.poll_run("agent-admissions-001", "run-002", "tok-abc")

    assert result["status"] == "completed"
    assert result["output"]["result"] == "Strong pathway fit for Computer Science."


# ---------------------------------------------------------------------------
# Cycle 3: poll_run reports failure for both failed and cancelled runs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("real_status", ["failed", "cancelled"])
async def test_poll_run_reports_failed_for_failed_or_cancelled_status(monkeypatch, respx_mock, real_status):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    respx_mock.get(f"{RUNS_URL}/run-003").mock(
        return_value=httpx.Response(200, json={"id": "run-003", "status": real_status})
    )

    result = await orchestrate_module.poll_run("agent-admissions-001", "run-003", "tok-abc")

    assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Cycle 4: poll_run keeps polling on pending/running, times out to "expired"
# ---------------------------------------------------------------------------

async def test_poll_run_polls_through_pending_and_running_to_completion(monkeypatch, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    responses = iter([
        httpx.Response(200, json={"id": "run-004", "status": "pending"}),
        httpx.Response(200, json={"id": "run-004", "status": "running"}),
        httpx.Response(200, json=_completed_run_response("Done after polling.")),
    ])
    respx_mock.get(f"{RUNS_URL}/run-004").mock(side_effect=lambda request: next(responses))

    result = await orchestrate_module.poll_run("agent-admissions-001", "run-004", "tok-abc")

    assert result["status"] == "completed"
    assert result["output"]["result"] == "Done after polling."


async def test_poll_run_times_out_to_expired_if_never_terminal(monkeypatch, respx_mock):
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    respx_mock.get(f"{RUNS_URL}/run-005").mock(
        return_value=httpx.Response(200, json={"id": "run-005", "status": "running"})
    )

    result = await orchestrate_module.poll_run("agent-admissions-001", "run-005", "tok-abc", timeout=0)

    assert result["status"] == "expired"
