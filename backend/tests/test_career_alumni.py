"""Tests for the Career & Alumni page API (issue #20)."""

import os
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
AGENT_CAREER = "agent-career-001"


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
# Cycle 1 — tracer bullet: endpoint returns 200
# ---------------------------------------------------------------------------

def test_career_alumni_profile_returns_200(client):
    response = client.get("/api/career-alumni/profile")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — response has all top-level sections
# ---------------------------------------------------------------------------

def test_career_alumni_profile_has_all_sections(client):
    data = client.get("/api/career-alumni/profile").json()
    required = {
        "stage_summary",
        "student",
        "skill_gaps",
        "recommendations",
        "alumni_mentor_match",
        "outcomes_feedback_loop",
        "career_pathway_recommendation",
        "career_advisor_item",
    }
    assert required <= data.keys()


# ---------------------------------------------------------------------------
# Cycle 3 — stage_summary has valid fields and non-negative numbers
# ---------------------------------------------------------------------------

def test_stage_summary_has_required_fields(client):
    data = client.get("/api/career-alumni/profile").json()
    summary = data["stage_summary"]
    assert "health" in summary
    assert "placement_rate" in summary
    assert "employed_count" in summary
    assert "total_graduates" in summary


def test_stage_summary_placement_rate_is_valid(client):
    data = client.get("/api/career-alumni/profile").json()
    rate = data["stage_summary"]["placement_rate"]
    assert 0.0 <= rate <= 1.0, f"placement_rate={rate!r} is not in [0, 1]"


def test_stage_summary_counts_are_non_negative(client):
    data = client.get("/api/career-alumni/profile").json()
    summary = data["stage_summary"]
    assert summary["employed_count"] >= 0
    assert summary["total_graduates"] >= 0


# ---------------------------------------------------------------------------
# Cycle 4 — student section matches seeded stu-005 data
# ---------------------------------------------------------------------------

def test_student_section_has_required_fields(client):
    data = client.get("/api/career-alumni/profile").json()
    student = data["student"]
    for field in ("id", "name", "program_name", "year_level", "gpa"):
        assert field in student, f"student missing field: {field!r}"


def test_student_is_seeded_stu_005(client):
    data = client.get("/api/career-alumni/profile").json()
    assert data["student"]["id"] == "stu-005"


def test_student_gpa_is_positive(client):
    data = client.get("/api/career-alumni/profile").json()
    assert data["student"]["gpa"] > 0.0


# ---------------------------------------------------------------------------
# Cycle 5 — skill_gaps is a non-empty list with required fields
# ---------------------------------------------------------------------------

def test_skill_gaps_is_non_empty_list(client):
    data = client.get("/api/career-alumni/profile").json()
    assert isinstance(data["skill_gaps"], list)
    assert len(data["skill_gaps"]) > 0


def test_skill_gaps_items_have_required_fields(client):
    data = client.get("/api/career-alumni/profile").json()
    for gap in data["skill_gaps"]:
        assert "skill" in gap
        assert "gap" in gap
        assert isinstance(gap["gap"], bool)


# ---------------------------------------------------------------------------
# Cycle 6 — alumni mentor match references a seeded mentor
# ---------------------------------------------------------------------------

def test_alumni_mentor_match_is_present(client):
    data = client.get("/api/career-alumni/profile").json()
    assert data["alumni_mentor_match"] is not None


def test_alumni_mentor_match_has_required_fields(client):
    data = client.get("/api/career-alumni/profile").json()
    mentor = data["alumni_mentor_match"]
    for field in ("id", "name", "current_role", "industry", "graduation_year"):
        assert field in mentor, f"alumni_mentor_match missing field: {field!r}"


# ---------------------------------------------------------------------------
# Cycle 7 — career_pathway_recommendation has actions list
# ---------------------------------------------------------------------------

def test_career_pathway_recommendation_has_actions(client):
    data = client.get("/api/career-alumni/profile").json()
    rec = data["career_pathway_recommendation"]
    assert "actions" in rec
    assert isinstance(rec["actions"], list)
    assert len(rec["actions"]) > 0


def test_career_pathway_actions_have_type_and_priority(client):
    data = client.get("/api/career-alumni/profile").json()
    for action in data["career_pathway_recommendation"]["actions"]:
        assert "type" in action
        assert "priority" in action
        assert action["priority"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Cycle 8 — career_advisor_item references seeded workflow data
# ---------------------------------------------------------------------------

def test_career_advisor_item_is_present(client):
    data = client.get("/api/career-alumni/profile").json()
    assert data["career_advisor_item"] is not None


def test_career_advisor_item_has_id_and_status(client):
    data = client.get("/api/career-alumni/profile").json()
    item = data["career_advisor_item"]
    assert "id" in item
    assert "status" in item
    assert "owner_role" in item


# ---------------------------------------------------------------------------
# Issue #31 — live watsonx Orchestrate agent rationale, with scripted fallback
# ---------------------------------------------------------------------------

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


def test_career_pathway_recommendation_uses_live_agent_rationale_when_run_completes(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_CAREER", AGENT_CAREER)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-001"}))
        router.get(f"{RUNS_URL}/run-001").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-001", "Live agent: strong pathway fit.")
            )
        )

        rec = client.get("/api/career-alumni/profile").json()["career_pathway_recommendation"]

    assert rec["rationale"] == "Live agent: strong pathway fit."


def test_career_pathway_recommendation_falls_back_when_run_fails(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_CAREER", AGENT_CAREER)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-fail"}))
        router.get(f"{RUNS_URL}/run-fail").mock(
            return_value=httpx.Response(200, json={"id": "run-fail", "status": "failed"})
        )

        rec = client.get("/api/career-alumni/profile").json()["career_pathway_recommendation"]

    assert rec["rationale"]
    assert "Live agent" not in rec["rationale"]


def test_career_pathway_recommendation_falls_back_when_run_times_out(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_CAREER", AGENT_CAREER)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-timeout"}))
        router.get(f"{RUNS_URL}/run-timeout").mock(
            return_value=httpx.Response(200, json={"id": "run-timeout", "status": "running"})
        )

        rec = client.get("/api/career-alumni/profile").json()["career_pathway_recommendation"]

    assert rec["rationale"]


def test_scripted_mode_never_contacts_orchestrate(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "scripted")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_CAREER", AGENT_CAREER)

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        iam_route = router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        rec = client.get("/api/career-alumni/profile").json()["career_pathway_recommendation"]

    assert not iam_route.called, "scripted mode must not contact IAM/Orchestrate"
    assert rec["rationale"]


def test_career_pathway_recommendation_falls_back_when_ai_mode_live_but_orchestrate_unconfigured(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.delenv("WXO_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_ID_CAREER", raising=False)

    rec = client.get("/api/career-alumni/profile").json()["career_pathway_recommendation"]

    assert rec["rationale"]
