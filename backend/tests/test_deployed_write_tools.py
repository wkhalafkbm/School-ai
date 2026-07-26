"""
What Orchestrate actually serves to agents — issue #79.

tests/test_stage_vocabulary.py checks the spec file in this repo. Agents never
read that file: they read the copy registered inside Orchestrate, which is
whatever was last imported. The two drift the moment the spec changes without a
re-import, and the symptom is invisible from the repo — an agent sends a stage
the gateway now rejects with 422 and the workflow item is simply never created.

Marked e2e: needs the `orchestrate` CLI and a live token
(`orchestrate env activate school-ai --api-key "$WXO_API_KEY"`), so it is
excluded from the default `-m "not e2e"` run.

    make import-write-tools && pytest -m e2e tests/test_deployed_write_tools.py
"""

import json
import os
import shutil
import subprocess

import httpx
import pytest

from app.stages import LEGACY_STAGES, LEGACY_STATUSES, STAGES, WORKFLOW_STATUSES

pytestmark = pytest.mark.e2e

CLI_TIMEOUT_SECONDS = 120

# The tool spec points agents at the tunnel, not at localhost, so the tunnel is
# the surface that has to be serving the validating build.
TOOL_SERVER_URL = os.getenv(
    "TOOL_SERVER_URL", "https://mushily-twistable-simply.ngrok-free.dev"
)


def _deployed_tools() -> list[dict]:
    """Every tool registered in the active environment, as the CLI reports it."""
    if shutil.which("orchestrate") is None:
        pytest.skip("orchestrate CLI not installed")

    result = subprocess.run(
        ["orchestrate", "tools", "list", "--verbose"],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        pytest.skip(f"orchestrate CLI unavailable: {result.stderr.strip()[:200]}")

    # The CLI prints log lines before the JSON array.
    start = result.stdout.find("[")
    if start == -1:
        pytest.skip("orchestrate tools list returned no JSON")
    return json.loads(result.stdout[start:])


@pytest.fixture(scope="module")
def deployed() -> dict[str, dict]:
    return {tool["name"]: tool for tool in _deployed_tools()}


def request_body(tool: dict) -> dict:
    """The body schema Orchestrate hands the agent, unwrapped."""
    return tool["input_schema"]["properties"]["__requestBody__"]["properties"]


def test_both_write_tools_are_deployed(deployed):
    assert {"create_workflow_item", "update_workflow_item"} <= deployed.keys()


def test_the_deployed_create_tool_constrains_stage_to_the_vocabulary(deployed):
    """Without the enum, nothing stops an agent inventing a stage no page reads."""
    stage = request_body(deployed["create_workflow_item"])["stage"]
    assert set(stage.get("enum", [])) == STAGES


def test_the_deployed_create_tool_constrains_status_to_the_vocabulary(deployed):
    status = request_body(deployed["create_workflow_item"])["status"]
    assert set(status.get("enum", [])) == WORKFLOW_STATUSES


def test_the_deployed_update_tool_constrains_status_to_the_vocabulary(deployed):
    status = request_body(deployed["update_workflow_item"])["status"]
    assert set(status.get("enum", [])) == WORKFLOW_STATUSES


@pytest.mark.parametrize("retired", sorted(LEGACY_STATUSES))
def test_no_deployed_description_offers_a_retired_status(deployed, retired):
    """
    An agent follows prose as readily as schema, and `complete` is the value the
    gateway now rejects with 422.
    """
    for name in ("create_workflow_item", "update_workflow_item"):
        blob = json.dumps(deployed[name])
        assert f'"{retired}"' not in blob and f" {retired}." not in blob, (
            f"{name} still offers the retired status {retired!r}"
        )


def _post_workflow_item(stage: str) -> httpx.Response:
    try:
        return httpx.post(
            f"{TOOL_SERVER_URL}/api/workflows",
            json={
                "stage": stage,
                "trigger": f"#79 deployment check — {stage}",
                "owner_name": "Noura Al-Hamdan",
                "owner_role": "academic advisor",
                "status": "pending",
                "description": "Deployment check for the deployed stage vocabulary.",
                "student_id": "stu-003",
            },
            timeout=30,
        )
    except httpx.HTTPError as exc:
        pytest.skip(f"tool server unreachable at {TOOL_SERVER_URL}: {exc}")


def test_the_server_agents_call_rejects_a_retired_stage():
    """
    The enum stops a well-behaved agent; this is the backstop for one that
    ignores it. Exercised through the tunnel the tool spec actually names.

    Only the rejected path is checked here: a 201 would leave a probe row in the
    demo database this runs against, and the accepted path is already covered
    against a throwaway database in test_workflows.py.
    """
    response = _post_workflow_item("academic_progress")
    assert response.status_code == 422, response.text
    assert "academic_risk" in response.text


@pytest.mark.parametrize("retired", sorted(LEGACY_STAGES))
def test_the_deployed_stage_description_names_no_retired_stage(deployed, retired):
    description = request_body(deployed["create_workflow_item"])["stage"]["description"]
    words = description.replace(",", " ").replace(".", " ").split()
    assert retired not in words, (
        f"the deployed stage description still names {retired!r}"
    )
