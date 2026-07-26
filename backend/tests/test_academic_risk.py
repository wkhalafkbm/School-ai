"""Tests for the Academic Risk page API (issue #15)."""

import asyncio
import json
import os
import time
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.gateway.iam as iam_module
import app.gateway.orchestrate as orchestrate_module
from app.main import app
from app.database import get_db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

WXO_BASE = "https://wxo.example.com"
RUNS_URL = f"{WXO_BASE}/v1/orchestrate/runs"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
AGENT_ENGAGEMENT = "agent-academic-risk-engagement-001"
AGENT_INTERVENTION = "agent-academic-risk-intervention-001"
AGENT_SUPPORT = "agent-academic-risk-support-001"


@pytest.fixture(autouse=True)
def reset_iam_token():
    iam_module._token = None
    iam_module._expires_at = 0.0
    yield


@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(autouse=True, scope="module")
def seeded_db(engine):
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import text

    cfg = Config("/Users/waleedkhalaf/workspace/KBM/School-ai/backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    cfg.set_main_option(
        "script_location",
        "/Users/waleedkhalaf/workspace/KBM/School-ai/backend/alembic",
    )

    def drop_enum():
        with engine.connect() as conn:
            conn.execute(text("DROP TYPE IF EXISTS datasource CASCADE"))
            conn.commit()

    command.downgrade(cfg, "base")
    drop_enum()
    command.upgrade(cfg, "head")

    from app.seed import seed
    seed(TEST_DATABASE_URL, FIXTURES_DIR)

    yield

    command.downgrade(cfg, "base")
    drop_enum()


@pytest.fixture(scope="module")
def client(engine):
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Cycle 1 — tracer bullet: GET /api/academic-risk/profile returns 200
# ---------------------------------------------------------------------------

def test_academic_risk_profile_returns_200(client):
    response = client.get("/api/academic-risk/profile")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — stage summary has health and risk-level counts
# ---------------------------------------------------------------------------

def test_stage_summary_has_health(client):
    summary = client.get("/api/academic-risk/profile").json()["stage_summary"]
    assert "health" in summary
    assert summary["health"] in {"on_track", "watch", "needs_attention", "urgent"}


def test_stage_summary_has_risk_level_counts(client):
    summary = client.get("/api/academic-risk/profile").json()["stage_summary"]
    for field in ("watch_count", "needs_attention_count", "urgent_count"):
        assert field in summary, f"Missing field: {field}"
        assert isinstance(summary[field], int)


def test_stage_summary_counts_are_non_negative(client):
    summary = client.get("/api/academic-risk/profile").json()["stage_summary"]
    assert summary["watch_count"] >= 0
    assert summary["needs_attention_count"] >= 0
    assert summary["urgent_count"] >= 0


def test_stage_summary_urgent_count_is_at_least_one(client):
    # Fahad (stu-003) has 3 "high" LMS risk flags — must appear in urgent
    summary = client.get("/api/academic-risk/profile").json()["stage_summary"]
    assert summary["urgent_count"] >= 1


# ---------------------------------------------------------------------------
# Cycle 3 — student is Fahad Al-Ajmi with two separate risk indicators
# ---------------------------------------------------------------------------

def test_student_is_fahad_alajmi(client):
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert student["name"] == "Fahad Al-Ajmi"
    assert student["id"] == "stu-003"


def test_student_has_program_and_gpa(client):
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert student["program_name"]
    assert isinstance(student["year_level"], int)
    assert isinstance(student["gpa"], float)
    assert student["gpa"] == pytest.approx(1.9)


def test_student_has_academic_failure_risk(client):
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert "academic_failure_risk" in student
    assert student["academic_failure_risk"] in {"watch", "needs_attention", "urgent"}


def test_student_has_attrition_risk(client):
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert "attrition_risk" in student
    assert student["attrition_risk"] in {"watch", "needs_attention", "urgent"}


def test_student_risk_indicators_are_separate_fields(client):
    # Both fields must be present and distinguishable
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert "academic_failure_risk" in student
    assert "attrition_risk" in student
    # Verify they are independent fields (not collapsed into one)
    assert student["academic_failure_risk"] != student.get("risk")


# ---------------------------------------------------------------------------
# Cycle 4 — risk classification uses supportive language only
# ---------------------------------------------------------------------------

SUPPORTIVE_LEVELS = {"watch", "needs_attention", "urgent"}


def test_academic_failure_risk_uses_supportive_label(client):
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert student["academic_failure_risk"] in SUPPORTIVE_LEVELS, (
        f"Non-supportive label: {student['academic_failure_risk']}"
    )


def test_attrition_risk_uses_supportive_label(client):
    student = client.get("/api/academic-risk/profile").json()["student"]
    assert student["attrition_risk"] in SUPPORTIVE_LEVELS, (
        f"Non-supportive label: {student['attrition_risk']}"
    )


def test_stage_health_uses_supportive_label(client):
    summary = client.get("/api/academic-risk/profile").json()["stage_summary"]
    assert summary["health"] in {"on_track", "watch", "needs_attention", "urgent"}


# ---------------------------------------------------------------------------
# Cycle 5 — cohort SLO pattern shows peers underperforming same SLOs
# ---------------------------------------------------------------------------

def test_cohort_slo_pattern_present(client):
    data = client.get("/api/academic-risk/profile").json()
    assert "cohort_slo_pattern" in data
    assert isinstance(data["cohort_slo_pattern"], list)


def test_cohort_slo_pattern_non_empty(client):
    pattern = client.get("/api/academic-risk/profile").json()["cohort_slo_pattern"]
    assert len(pattern) >= 1, "Expected at least one SLO in cohort pattern"


def test_cohort_slo_pattern_has_required_fields(client):
    pattern = client.get("/api/academic-risk/profile").json()["cohort_slo_pattern"]
    for item in pattern:
        assert "slo_code" in item, f"Missing slo_code: {item}"
        assert "description" in item, f"Missing description: {item}"
        assert "student_score" in item, f"Missing student_score: {item}"
        assert "proficient" in item, f"Missing proficient: {item}"
        assert "peers_underperforming" in item, f"Missing peers_underperforming: {item}"
        assert "cohort_size" in item, f"Missing cohort_size: {item}"


def test_cohort_slo_pattern_fahad_not_proficient(client):
    pattern = client.get("/api/academic-risk/profile").json()["cohort_slo_pattern"]
    for item in pattern:
        assert item["proficient"] is False, (
            f"Expected proficient=false for {item['slo_code']}, got {item['proficient']}"
        )


def test_cohort_slo_pattern_peers_count_positive(client):
    pattern = client.get("/api/academic-risk/profile").json()["cohort_slo_pattern"]
    for item in pattern:
        assert item["peers_underperforming"] >= 1, (
            f"Expected peers_underperforming >= 1 for {item['slo_code']}"
        )


# ---------------------------------------------------------------------------
# Cycle 6 — AI-generated intervention plan with confidence and rationale
# ---------------------------------------------------------------------------

def test_intervention_plan_present(client):
    data = client.get("/api/academic-risk/profile").json()
    assert "intervention_plan" in data


def test_intervention_plan_has_confidence(client):
    plan = client.get("/api/academic-risk/profile").json()["intervention_plan"]
    assert "confidence" in plan
    assert plan["confidence"] in {"High", "Medium", "Low"}


def test_intervention_plan_has_rationale(client):
    plan = client.get("/api/academic-risk/profile").json()["intervention_plan"]
    assert "rationale" in plan
    assert len(plan["rationale"]) > 20


def test_intervention_plan_has_actions(client):
    plan = client.get("/api/academic-risk/profile").json()["intervention_plan"]
    assert "actions" in plan
    assert isinstance(plan["actions"], list)
    assert len(plan["actions"]) >= 1


def test_intervention_plan_actions_have_type_and_description(client):
    actions = client.get("/api/academic-risk/profile").json()["intervention_plan"]["actions"]
    for action in actions:
        assert action.get("type"), f"Action missing type: {action}"
        assert action.get("description"), f"Action missing description: {action}"


# ---------------------------------------------------------------------------
# Cycle 7 — sponsor escalation item present (auto-triggered, seeded)
# ---------------------------------------------------------------------------

def test_sponsor_escalation_present(client):
    data = client.get("/api/academic-risk/profile").json()
    assert "sponsor_escalation" in data
    assert data["sponsor_escalation"] is not None


def test_sponsor_escalation_is_auto_triggered(client):
    escalation = client.get("/api/academic-risk/profile").json()["sponsor_escalation"]
    assert "trigger" in escalation
    assert escalation["trigger"], "Escalation trigger should not be empty"


def test_sponsor_escalation_has_owner_info(client):
    escalation = client.get("/api/academic-risk/profile").json()["sponsor_escalation"]
    assert escalation.get("owner_name")
    assert escalation.get("owner_role")


def test_sponsor_escalation_status_is_pending(client):
    escalation = client.get("/api/academic-risk/profile").json()["sponsor_escalation"]
    assert escalation["status"] == "pending"


# ---------------------------------------------------------------------------
# Cycle 8 — approve intervention creates workflow item for student affairs
# ---------------------------------------------------------------------------

APPROVE_PAYLOAD = {
    "stage": "academic_risk",
    "trigger": "Intervention approved — routing to student affairs",
    "owner_name": "Student Affairs Officer",
    "owner_role": "student affairs officer",
    "status": "pending",
    "description": "Follow up with Fahad Al-Ajmi on approved intervention plan",
    "student_id": "stu-003",
}


def test_approve_intervention_creates_workflow_item(client):
    res = client.post("/api/workflows", json=APPROVE_PAYLOAD)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    assert res.json().get("id"), "Created item must have an id"


def test_approved_item_routed_to_student_affairs(client):
    res = client.post("/api/workflows", json=APPROVE_PAYLOAD)
    assert res.status_code == 201
    item = res.json()
    assert item["owner_role"] == "student affairs officer"
    assert item["stage"] == "academic_risk"


def test_approved_item_appears_in_workflow_list(client):
    created = client.post("/api/workflows", json=APPROVE_PAYLOAD)
    assert created.status_code == 201
    created_id = created.json()["id"]

    all_items = client.get("/api/workflows").json()
    all_ids = {item["id"] for item in all_items}
    assert created_id in all_ids, f"Created item {created_id} not found in workflow list"


# ---------------------------------------------------------------------------
# Issue #29 — live watsonx Orchestrate agent rationales, with scripted fallback
# ---------------------------------------------------------------------------

# Cycle 9 — tracer bullet: engagement_assessment and support_assessment exist
# with computed rationale text, even before any live wiring.

def test_engagement_assessment_has_computed_rationale(client):
    data = client.get("/api/academic-risk/profile").json()
    assert "engagement_assessment" in data
    rationale = data["engagement_assessment"]["rationale"]
    assert len(rationale) > 20


def test_support_assessment_has_computed_rationale(client):
    data = client.get("/api/academic-risk/profile").json()
    assert "support_assessment" in data
    rationale = data["support_assessment"]["rationale"]
    assert len(rationale) > 20


def _completed_run_response(run_id: str, text: str) -> dict:
    return {
        "id": run_id,
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


# ---------------------------------------------------------------------------
# Cycle 10 — intervention agent: live success overrides intervention_plan.rationale
# ---------------------------------------------------------------------------

def test_intervention_rationale_uses_live_agent_result_when_run_completes(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", raising=False)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-intervention"}))
        router.get(f"{RUNS_URL}/run-intervention").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-intervention", "Live agent: schedule tutoring now.")
            )
        )

        plan = client.get("/api/academic-risk/profile").json()["intervention_plan"]

    assert plan["rationale"] == "Live agent: schedule tutoring now."


def test_intervention_rationale_falls_back_when_run_fails(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", raising=False)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-intervention-fail"}))
        router.get(f"{RUNS_URL}/run-intervention-fail").mock(
            return_value=httpx.Response(200, json={"id": "run-intervention-fail", "status": "failed"})
        )

        plan = client.get("/api/academic-risk/profile").json()["intervention_plan"]

    assert len(plan["rationale"]) > 20
    assert plan["rationale"] != "Live agent: schedule tutoring now."


# ---------------------------------------------------------------------------
# Issue #52 — intervention agent payload must be a plain sentence carrying the
# student's cohort_id (program_id), not a bare student_id the agent must guess from
# ---------------------------------------------------------------------------

def test_intervention_agent_payload_is_plain_sentence_with_student_and_cohort_ids(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", raising=False)

    captured_contents = []

    def capture_run_request(request):
        body = json.loads(request.content)
        captured_contents.append(body["message"]["content"])
        return httpx.Response(200, json={"run_id": "run-intervention-payload"})

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL, json__agent_id=AGENT_INTERVENTION).mock(side_effect=capture_run_request)
        router.get(f"{RUNS_URL}/run-intervention-payload").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-intervention-payload", "Live agent: schedule tutoring now.")
            )
        )

        client.get("/api/academic-risk/profile")

    assert len(captured_contents) == 1
    content = captured_contents[0]
    assert not content.strip().startswith("{"), (
        "content sent to the intervention agent should be a plain sentence, not a raw JSON blob"
    )
    assert "stu-003" in content
    assert "prog-001" in content


# ---------------------------------------------------------------------------
# Cycle 11 — engagement agent: live success / live failure falls back
# ---------------------------------------------------------------------------

def test_engagement_rationale_uses_live_agent_result_when_run_completes(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", raising=False)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-engagement"}))
        router.get(f"{RUNS_URL}/run-engagement").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-engagement", "Live agent: urgent outreach needed.")
            )
        )

        data = client.get("/api/academic-risk/profile").json()

    assert data["engagement_assessment"]["rationale"] == "Live agent: urgent outreach needed."


def test_engagement_rationale_falls_back_when_run_fails(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", raising=False)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-engagement-fail"}))
        router.get(f"{RUNS_URL}/run-engagement-fail").mock(
            return_value=httpx.Response(200, json={"id": "run-engagement-fail", "status": "failed"})
        )

        data = client.get("/api/academic-risk/profile").json()

    assert "Fahad averages" in data["engagement_assessment"]["rationale"]


# ---------------------------------------------------------------------------
# Cycle 12 — support agent: live success / live failure falls back
# ---------------------------------------------------------------------------

def test_support_rationale_uses_live_agent_result_when_run_completes(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", raising=False)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-support"}))
        router.get(f"{RUNS_URL}/run-support").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-support", "Live agent: initiate welfare check.")
            )
        )

        data = client.get("/api/academic-risk/profile").json()

    assert data["support_assessment"]["rationale"] == "Live agent: initiate welfare check."


def test_support_rationale_falls_back_when_run_fails(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", raising=False)
    monkeypatch.delenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", raising=False)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-support-fail"}))
        router.get(f"{RUNS_URL}/run-support-fail").mock(
            return_value=httpx.Response(200, json={"id": "run-support-fail", "status": "failed"})
        )

        data = client.get("/api/academic-risk/profile").json()

    assert "GPA of" in data["support_assessment"]["rationale"]


# ---------------------------------------------------------------------------
# Cycle 13 — one agent failing does not blank the other two live results
# ---------------------------------------------------------------------------

def test_one_agent_failing_does_not_blank_the_others_live_result(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL, json__agent_id=AGENT_INTERVENTION).mock(
            return_value=httpx.Response(200, json={"run_id": "run-intervention-fail-2"})
        )
        router.get(f"{RUNS_URL}/run-intervention-fail-2").mock(
            return_value=httpx.Response(200, json={"id": "run-intervention-fail-2", "status": "failed"})
        )
        router.post(RUNS_URL, json__agent_id=AGENT_ENGAGEMENT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-engagement-ok"})
        )
        router.get(f"{RUNS_URL}/run-engagement-ok").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-engagement-ok", "Live agent: urgent outreach needed.")
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_SUPPORT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-support-ok"})
        )
        router.get(f"{RUNS_URL}/run-support-ok").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-support-ok", "Live agent: initiate welfare check.")
            )
        )

        data = client.get("/api/academic-risk/profile").json()

    assert len(data["intervention_plan"]["rationale"]) > 20
    assert data["intervention_plan"]["rationale"] != "Live agent: schedule tutoring now."
    assert data["engagement_assessment"]["rationale"] == "Live agent: urgent outreach needed."
    assert data["support_assessment"]["rationale"] == "Live agent: initiate welfare check."


# ---------------------------------------------------------------------------
# Cycle 14 — scripted mode never contacts Orchestrate
# ---------------------------------------------------------------------------

def test_scripted_mode_never_contacts_orchestrate_for_academic_risk(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "scripted")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        iam_route = router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        data = client.get("/api/academic-risk/profile").json()

    assert not iam_route.called, "scripted mode must not contact IAM/Orchestrate"
    assert len(data["intervention_plan"]["rationale"]) > 20
    assert "Fahad averages" in data["engagement_assessment"]["rationale"]
    assert "GPA of" in data["support_assessment"]["rationale"]


# ---------------------------------------------------------------------------
# Issue #42 — GET /api/academic-risk/profile/stream (SSE)
# ---------------------------------------------------------------------------

def _parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    events = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        event = next(line[len("event: "):] for line in lines if line.startswith("event: "))
        data = next(line[len("data: "):] for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


def test_academic_risk_profile_stream_returns_event_stream_content_type(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "scripted")

    with client.stream("GET", "/api/academic-risk/profile/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


def test_academic_risk_profile_stream_scripted_mode_yields_base_three_fields_done_without_contacting_orchestrate(
    client, monkeypatch
):
    monkeypatch.setenv("AI_MODE", "scripted")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        iam_route = router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        with client.stream("GET", "/api/academic-risk/profile/stream") as response:
            raw = response.read().decode()

    assert not iam_route.called, "scripted mode must not contact IAM/Orchestrate"

    events = _parse_sse_events(raw)
    assert [event for event, _ in events] == ["base", "field", "field", "field", "done"]

    base_event = events[0]
    field_events = events[1:4]
    done_event = events[4]

    base_data = base_event[1]
    assert len(base_data["intervention_plan"]["rationale"]) > 20
    assert "Fahad averages" in base_data["engagement_assessment"]["rationale"]
    assert "GPA of" in base_data["support_assessment"]["rationale"]

    field_paths = {event_data["path"] for _, event_data in field_events}
    assert field_paths == {
        "intervention_plan.rationale",
        "engagement_assessment.rationale",
        "support_assessment.rationale",
    }

    field_values_by_path = {event_data["path"]: event_data["value"] for _, event_data in field_events}
    assert field_values_by_path["intervention_plan.rationale"] == base_data["intervention_plan"]["rationale"]
    assert field_values_by_path["engagement_assessment.rationale"] == base_data["engagement_assessment"]["rationale"]
    assert field_values_by_path["support_assessment.rationale"] == base_data["support_assessment"]["rationale"]

    assert done_event[1] == {}


def test_academic_risk_profile_stream_live_mode_field_events_carry_live_rationale(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL, json__agent_id=AGENT_INTERVENTION).mock(
            return_value=httpx.Response(200, json={"run_id": "run-intervention-stream"})
        )
        router.get(f"{RUNS_URL}/run-intervention-stream").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-intervention-stream", "Live agent: schedule tutoring now.")
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_ENGAGEMENT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-engagement-stream"})
        )
        router.get(f"{RUNS_URL}/run-engagement-stream").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-engagement-stream", "Live agent: urgent outreach needed.")
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_SUPPORT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-support-stream"})
        )
        router.get(f"{RUNS_URL}/run-support-stream").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-support-stream", "Live agent: initiate welfare check.")
            )
        )

        with client.stream("GET", "/api/academic-risk/profile/stream") as response:
            raw = response.read().decode()

    events = _parse_sse_events(raw)
    assert [event for event, _ in events] == ["base", "field", "field", "field", "done"]

    field_values_by_path = {
        event_data["path"]: event_data["value"] for _, event_data in events[1:4]
    }
    assert field_values_by_path == {
        "intervention_plan.rationale": "Live agent: schedule tutoring now.",
        "engagement_assessment.rationale": "Live agent: urgent outreach needed.",
        "support_assessment.rationale": "Live agent: initiate welfare check.",
    }


def test_academic_risk_profile_stream_field_events_arrive_in_completion_order(client, monkeypatch):
    # Declared first (intervention) is the slowest and must still complete last;
    # declared last (support) is the fastest and must still complete first.
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)

    async def delayed_completed_run(delay, run_id, text):
        await asyncio.sleep(delay)
        return httpx.Response(200, json=_completed_run_response(run_id, text))

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL, json__agent_id=AGENT_INTERVENTION).mock(
            return_value=httpx.Response(200, json={"run_id": "run-intervention-order"})
        )
        router.get(f"{RUNS_URL}/run-intervention-order").mock(
            side_effect=lambda request: delayed_completed_run(
                0.4, "run-intervention-order", "Live agent: schedule tutoring now."
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_ENGAGEMENT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-engagement-order"})
        )
        router.get(f"{RUNS_URL}/run-engagement-order").mock(
            side_effect=lambda request: delayed_completed_run(
                0.15, "run-engagement-order", "Live agent: urgent outreach needed."
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_SUPPORT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-support-order"})
        )
        router.get(f"{RUNS_URL}/run-support-order").mock(
            side_effect=lambda request: delayed_completed_run(
                0.0, "run-support-order", "Live agent: initiate welfare check."
            )
        )

        with client.stream("GET", "/api/academic-risk/profile/stream") as response:
            raw = response.read().decode()

    events = _parse_sse_events(raw)
    field_paths_in_order = [event_data["path"] for event, event_data in events if event == "field"]

    assert field_paths_in_order == [
        "support_assessment.rationale",
        "engagement_assessment.rationale",
        "intervention_plan.rationale",
    ], "field events must arrive in completion order, not declaration order"


# ---------------------------------------------------------------------------
# Cycle — /profile computes the 3 gateway calls concurrently, not sequentially
# ---------------------------------------------------------------------------

CALL_DELAY = 0.3


def test_profile_resolves_the_three_gateway_calls_concurrently(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_INTERVENTION", AGENT_INTERVENTION)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_ENGAGEMENT", AGENT_ENGAGEMENT)
    monkeypatch.setenv("AGENT_ID_ACADEMIC_RISK_SUPPORT", AGENT_SUPPORT)

    async def slow_completed_run(request, run_id, text):
        await asyncio.sleep(CALL_DELAY)
        return httpx.Response(200, json=_completed_run_response(run_id, text))

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL, json__agent_id=AGENT_INTERVENTION).mock(
            return_value=httpx.Response(200, json={"run_id": "run-intervention-timing"})
        )
        router.get(f"{RUNS_URL}/run-intervention-timing").mock(
            side_effect=lambda request: slow_completed_run(
                request, "run-intervention-timing", "Live agent: schedule tutoring now."
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_ENGAGEMENT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-engagement-timing"})
        )
        router.get(f"{RUNS_URL}/run-engagement-timing").mock(
            side_effect=lambda request: slow_completed_run(
                request, "run-engagement-timing", "Live agent: urgent outreach needed."
            )
        )
        router.post(RUNS_URL, json__agent_id=AGENT_SUPPORT).mock(
            return_value=httpx.Response(200, json={"run_id": "run-support-timing"})
        )
        router.get(f"{RUNS_URL}/run-support-timing").mock(
            side_effect=lambda request: slow_completed_run(
                request, "run-support-timing", "Live agent: initiate welfare check."
            )
        )

        start = time.perf_counter()
        response = client.get("/api/academic-risk/profile")
        elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 2 * CALL_DELAY, (
        f"Expected concurrent gateway calls (~{CALL_DELAY}s), took {elapsed:.2f}s — "
        "looks sequential (~3x call duration)"
    )


# ---------------------------------------------------------------------------
# Issue #65 — gpa_trend section on the profile payload
# ---------------------------------------------------------------------------

# Cycle 1 — tracer bullet: the payload carries a gpa_trend section at all.

def test_profile_has_gpa_trend_section(client):
    data = client.get("/api/academic-risk/profile").json()
    assert "gpa_trend" in data


# Cycle 2 — the series is the student's whole history, chronologically ordered.

def test_gpa_trend_series_is_chronological_with_term_and_cumulative_gpa(client):
    series = client.get("/api/academic-risk/profile").json()["gpa_trend"]["series"]
    assert series == [
        {"term": "2023-Fall", "term_gpa": 2.4, "cumulative_gpa": 2.4},
        {"term": "2024-Spring", "term_gpa": 1.9, "cumulative_gpa": 2.15},
        {"term": "2024-Fall", "term_gpa": 1.4, "cumulative_gpa": 1.9},
    ]


# Cycle 3 — the computed verdict: status, reason, and the rules that fired.

def test_gpa_trend_status_is_urgent_for_the_profiled_student(client):
    trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
    assert trend["status"] == "urgent"


def test_gpa_trend_reason_names_the_rule_and_the_numbers(client):
    trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
    assert "sharp drop" in trend["reason"]
    assert "1.90" in trend["reason"] and "1.40" in trend["reason"]


def test_gpa_trend_reports_which_rules_fired(client):
    trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
    assert trend["rules_fired"] == ["sharp_drop", "sustained_decline"]


# Cycle 4 — the workflow item opened for this trend, if one exists.

def test_gpa_trend_carries_the_linked_workflow_item(client):
    item = client.get("/api/academic-risk/profile").json()["gpa_trend"]["workflow_item"]
    assert item is not None
    assert item["id"] == "wft-stu-003-2024-Fall"
    assert item["status"] == "pending"
    assert item["created_date"]


# Cycle 5 — risk status and intervention status are two different facts:
# completing the item must not clear the trend.

def test_completing_the_workflow_item_does_not_clear_the_trend_status(client, engine):
    from sqlalchemy import text as sql

    def set_status(status: str) -> None:
        with engine.connect() as conn:
            conn.execute(
                sql("UPDATE workflow_items SET status = :st WHERE id = :id"),
                {"st": status, "id": "wft-stu-003-2024-Fall"},
            )
            conn.commit()

    set_status("completed")
    try:
        trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
        assert trend["status"] == "urgent"
        assert trend["workflow_item"]["status"] == "completed"
    finally:
        set_status("pending")


# Cycle 6 — a student whose rule never fires: a null status and a reason that
# says so, never a blank section.

def test_gpa_trend_status_is_null_when_no_rule_fires(client, monkeypatch):
    import app.routers.academic_risk as academic_risk_router

    # stu-002 has a single term of history — too little to compare.
    monkeypatch.setattr(academic_risk_router, "STUDENT_ID", "stu-002")

    trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
    assert trend["status"] is None
    assert trend["rules_fired"] == []
    assert trend["workflow_item"] is None
    assert len(trend["series"]) == 1
    assert trend["reason"]


def test_gpa_trend_reason_explains_a_steady_series_rather_than_missing_history(
    client, monkeypatch
):
    import app.routers.academic_risk as academic_risk_router

    # stu-005 has five terms hovering around 3.5 — enough history, no decline.
    monkeypatch.setattr(academic_risk_router, "STUDENT_ID", "stu-005")

    trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
    assert trend["status"] is None
    assert "No declining trend" in trend["reason"]


# Cycle 7 — a term whose GPA is not recorded yet withholds the verdict, and the
# reason must say that rather than blaming missing history.

def test_gpa_trend_reason_names_the_unrecorded_term_when_history_is_incomplete(
    client, engine, monkeypatch
):
    from sqlalchemy import text as sql

    import app.routers.academic_risk as academic_risk_router

    monkeypatch.setattr(academic_risk_router, "STUDENT_ID", "stu-002")

    with engine.connect() as conn:
        conn.execute(
            sql("""
                INSERT INTO student_term_gpa
                    (id, student_id, term, term_index, term_gpa, cumulative_gpa,
                     data_source)
                VALUES ('stg-test-incomplete', 'stu-002', '2025-Spring', 2,
                        NULL, NULL, 'SIS')
            """)
        )
        conn.commit()
    try:
        trend = client.get("/api/academic-risk/profile").json()["gpa_trend"]
        assert trend["status"] is None
        assert len(trend["series"]) == 2
        assert "2025-Spring" in trend["reason"]
        assert "Fewer than 2 terms" not in trend["reason"]
    finally:
        with engine.connect() as conn:
            conn.execute(
                sql("DELETE FROM student_term_gpa WHERE id = 'stg-test-incomplete'")
            )
            conn.commit()
