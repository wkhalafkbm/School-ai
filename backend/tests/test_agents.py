"""Tests for issue #22 — Orchestrate agent definitions (all 9 agents).

Validates each agent YAML against the ADK spec format and project policy.
TDD vertical slices: one test → one implementation → repeat.
"""

from pathlib import Path

import pytest
import yaml

AGENTS_DIR = Path(__file__).parent.parent.parent / "orchestrate" / "agents"
TOOLS_DIR = Path(__file__).parent.parent.parent / "orchestrate" / "tools"

READ_TOOLS_PATHS = sorted((TOOLS_DIR / "read").glob("*.yaml"))
WRITE_TOOLS_PATH = TOOLS_DIR / "write_tools.yaml"

REQUIRED_ADK_FIELDS = {"spec_version", "kind", "name", "description", "instructions", "llm", "style", "tools"}

BANNED_TERMS = ["ibm", "watsonx", "watson", "demo-mode", "demo mode"]

NINE_AGENT_FILES = [
    "admissions_agent.yaml",
    "enrollment_agent.yaml",
    "teaching_readiness_cohort_agent.yaml",
    "academic_risk_engagement_agent.yaml",
    "workload_balancing_agent.yaml",
    "academic_mentorship_agent.yaml",
    "student_support_agent.yaml",
    "progression_agent.yaml",
    "career_alumni_agent.yaml",
]


def _load_valid_operationids() -> set[str]:
    """Return all operationIds from orchestrate/tools/read/*.yaml and write_tools.yaml.

    Orchestrate normalises double underscores to single when registering OpenAPI
    tools (FastAPI path params produce __param__ in operationIds). We store both
    the raw operationId and the normalised form so agent YAMLs can use either.
    """
    ids: set[str] = set()
    for spec_path in (*READ_TOOLS_PATHS, WRITE_TOOLS_PATH):
        spec = yaml.safe_load(spec_path.read_text())
        for _path, methods in spec.get("paths", {}).items():
            for _method, op in methods.items():
                if isinstance(op, dict) and "operationId" in op:
                    raw = op["operationId"]
                    ids.add(raw)
                    ids.add(raw.replace("__", "_"))
    return ids


# ---------------------------------------------------------------------------
# Cycle 1 — tracer bullet: admissions agent YAML exists
# ---------------------------------------------------------------------------


def test_agents_directory_exists():
    assert AGENTS_DIR.exists(), f"orchestrate/agents/ directory not found at {AGENTS_DIR}"


def test_admissions_agent_file_exists():
    assert (AGENTS_DIR / "admissions_agent.yaml").exists(), (
        "admissions_agent.yaml not found under orchestrate/agents/"
    )


# ---------------------------------------------------------------------------
# Cycle 2 — admissions agent has all required ADK fields
# ---------------------------------------------------------------------------


def test_admissions_agent_has_required_adk_fields():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    missing = REQUIRED_ADK_FIELDS - set(data.keys())
    assert not missing, f"admissions_agent.yaml missing required fields: {missing}"


def test_admissions_agent_spec_version_is_v1():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    assert data["spec_version"] == "v1", "spec_version must be 'v1'"


def test_admissions_agent_kind_is_native():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    assert data["kind"] == "native", "kind must be 'native'"


def test_admissions_agent_tools_is_nonempty_list():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    assert isinstance(data["tools"], list) and len(data["tools"]) > 0, (
        "tools must be a non-empty list"
    )


# ---------------------------------------------------------------------------
# Cycle 3 — admissions agent tool names are valid operationIds
# ---------------------------------------------------------------------------


def test_admissions_agent_tools_reference_valid_operationids():
    valid_ids = _load_valid_operationids()
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    invalid = [t for t in data["tools"] if t not in valid_ids]
    assert not invalid, (
        f"admissions_agent.yaml references unknown tool operationIds: {invalid}"
    )


# ---------------------------------------------------------------------------
# Cycle 4 — admissions agent instructions have no banned terms
# ---------------------------------------------------------------------------


def test_admissions_agent_instructions_have_no_banned_terms():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    instructions_lower = data["instructions"].lower()
    found = [term for term in BANNED_TERMS if term in instructions_lower]
    assert not found, (
        f"admissions_agent.yaml instructions contain banned terms: {found}"
    )


def test_admissions_agent_instructions_are_substantive():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    assert len(data["instructions"]) >= 200, (
        "admissions_agent.yaml instructions must be substantive (>= 200 chars)"
    )


# ---------------------------------------------------------------------------
# Cycle 5 — all 9 agent files exist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_file_exists(filename):
    assert (AGENTS_DIR / filename).exists(), (
        f"{filename} not found under orchestrate/agents/"
    )


# ---------------------------------------------------------------------------
# Cycle 6 — all 9 agents have required ADK structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_has_required_fields(filename):
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    missing = REQUIRED_ADK_FIELDS - set(data.keys())
    assert not missing, f"{filename} missing required fields: {missing}"


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_spec_version_and_kind(filename):
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    assert data.get("spec_version") == "v1", f"{filename}: spec_version must be 'v1'"
    assert data.get("kind") == "native", f"{filename}: kind must be 'native'"


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_name_matches_filename(filename):
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    expected_name = filename.replace(".yaml", "")
    assert data.get("name") == expected_name, (
        f"{filename}: agent name '{data.get('name')}' must match filename stem '{expected_name}'"
    )


# ---------------------------------------------------------------------------
# Cycle 7 — all 9 agents reference valid tool operationIds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_tools_reference_valid_operationids(filename):
    valid_ids = _load_valid_operationids()
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    invalid = [t for t in data.get("tools", []) if t not in valid_ids]
    assert not invalid, (
        f"{filename} references unknown tool operationIds: {invalid}"
    )


# ---------------------------------------------------------------------------
# Cycle 8 — all 9 agents' instructions use supportive language and no banned terms
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_instructions_have_no_banned_terms(filename):
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    instructions_lower = data["instructions"].lower()
    found = [term for term in BANNED_TERMS if term in instructions_lower]
    assert not found, f"{filename} instructions contain banned terms: {found}"


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_instructions_are_substantive(filename):
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    assert len(data["instructions"]) >= 200, (
        f"{filename} instructions must be substantive (>= 200 chars)"
    )


@pytest.mark.parametrize("filename", NINE_AGENT_FILES)
def test_agent_has_nonempty_tools_list(filename):
    data = yaml.safe_load((AGENTS_DIR / filename).read_text())
    tools = data.get("tools", [])
    assert isinstance(tools, list) and len(tools) > 0, (
        f"{filename}: tools must be a non-empty list"
    )


# ---------------------------------------------------------------------------
# Cycle 9 — admissions agent must call create_workflow_item, not narrate it
# (issue #50: live trace showed a "Workflow Items Created" table with
# fabricated ids while zero create_workflow_item calls were made)
# ---------------------------------------------------------------------------


def test_admissions_agent_instructions_name_workflow_tool_explicitly():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    assert "create_workflow_item" in data["instructions"], (
        "admissions_agent.yaml instructions must name the create_workflow_item "
        "tool explicitly rather than only describing the action in prose"
    )


def test_admissions_agent_instructions_forbid_claiming_uncalled_workflow_items():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    instructions_lower = data["instructions"].lower()
    assert "do not claim" in instructions_lower and "created" in instructions_lower, (
        "admissions_agent.yaml instructions must explicitly forbid claiming a "
        "workflow item was created, queued, or logged unless the tool was "
        "actually called"
    )


def test_admissions_agent_instructions_require_real_tool_returned_id():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    instructions_lower = data["instructions"].lower()
    assert "rather than inventing" in instructions_lower, (
        "admissions_agent.yaml instructions must require quoting the id "
        "returned by create_workflow_item rather than inventing one, to "
        "prevent fabricated ids like '(auto-generated)'"
    )


def test_admissions_agent_instructions_have_pre_response_self_check():
    data = yaml.safe_load((AGENTS_DIR / "admissions_agent.yaml").read_text())
    instructions_lower = data["instructions"].lower()
    assert "before you send your final response" in instructions_lower, (
        "admissions_agent.yaml instructions must include a pre-response "
        "self-check requiring create_workflow_item to have already been "
        "called and returned before mentioning any workflow item — live "
        "testing showed the model sometimes skips the tool call after a "
        "long chain of read-tool calls and narrates the action instead"
    )
