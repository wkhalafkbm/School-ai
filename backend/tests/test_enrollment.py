"""Tests for the Enrollment page API (issue #13)."""

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
AGENT_ENROLLMENT = "agent-enrollment-001"


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
# Cycle 1 — tracer bullet: GET /api/enrollment/profile returns 200
# ---------------------------------------------------------------------------

def test_enrollment_profile_returns_200(client):
    response = client.get("/api/enrollment/profile")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — stage_summary has health and registration status counts
# ---------------------------------------------------------------------------

def test_stage_summary_has_health(client):
    summary = client.get("/api/enrollment/profile").json()["stage_summary"]
    assert "health" in summary
    assert summary["health"] in {"on_track", "watch", "needs_attention", "urgent"}


def test_stage_summary_has_registration_counts(client):
    summary = client.get("/api/enrollment/profile").json()["stage_summary"]
    for field in ("registration_complete", "registration_pending", "registration_blocked"):
        assert field in summary, f"Missing field: {field}"
        assert isinstance(summary[field], int)


# ---------------------------------------------------------------------------
# Cycle 3 — student is Mariam Al-Kandari with onboarding tasks
# ---------------------------------------------------------------------------

def test_student_is_mariam_alkandari(client):
    student = client.get("/api/enrollment/profile").json()["student"]
    assert student["name"] == "Mariam Al-Kandari"
    assert student["id"] == "stu-002"


def test_student_has_program_info(client):
    student = client.get("/api/enrollment/profile").json()["student"]
    assert student["program_name"]
    assert isinstance(student["year_level"], int)
    assert isinstance(student["gpa"], float)


def test_onboarding_tasks_present(client):
    student = client.get("/api/enrollment/profile").json()["student"]
    tasks = student["onboarding_tasks"]
    assert isinstance(tasks, list)
    assert len(tasks) >= 7  # seeded: ont-001 through ont-007


def test_onboarding_tasks_have_completion_status(client):
    tasks = client.get("/api/enrollment/profile").json()["student"]["onboarding_tasks"]
    task_names = [t["task_name"] for t in tasks]
    completed = {t["task_name"]: t["completed"] for t in tasks}
    assert "Submit Photo ID Copy" in task_names
    assert completed["Submit Photo ID Copy"] is True
    assert "Complete Medical Form" in task_names
    assert completed["Complete Medical Form"] is False


# ---------------------------------------------------------------------------
# Cycle 4 — all 6 registration blocker types present
# ---------------------------------------------------------------------------

EXPECTED_BLOCKER_TYPES = {
    "financial_aid_hold",
    "prerequisite",
    "credit_limit",
    "conflict",
    "admin_hold",
    "missing_document",
}


def test_registration_blockers_present(client):
    data = client.get("/api/enrollment/profile").json()
    assert "registration_blockers" in data
    assert isinstance(data["registration_blockers"], list)


def test_all_six_blocker_types_listed(client):
    blockers = client.get("/api/enrollment/profile").json()["registration_blockers"]
    found_types = {b["type"] for b in blockers}
    assert found_types == EXPECTED_BLOCKER_TYPES, (
        f"Missing: {EXPECTED_BLOCKER_TYPES - found_types}, "
        f"Extra: {found_types - EXPECTED_BLOCKER_TYPES}"
    )


def test_blockers_have_description(client):
    blockers = client.get("/api/enrollment/profile").json()["registration_blockers"]
    for b in blockers:
        assert b.get("description"), f"Blocker {b['type']} missing description"


# ---------------------------------------------------------------------------
# Cycle 5 — rules_engine_result is pass/fail/exception, no confidence field
# ---------------------------------------------------------------------------

def test_blockers_have_rules_engine_result(client):
    blockers = client.get("/api/enrollment/profile").json()["registration_blockers"]
    valid = {"pass", "fail", "exception"}
    for b in blockers:
        assert "rules_engine_result" in b, f"Missing rules_engine_result on {b['type']}"
        assert b["rules_engine_result"] in valid, (
            f"Invalid result {b['rules_engine_result']!r} on {b['type']}"
        )


def test_blockers_have_no_confidence_field(client):
    import json
    raw = json.dumps(client.get("/api/enrollment/profile").json()["registration_blockers"])
    assert "confidence" not in raw, "Forbidden 'confidence' field found in blockers"


# ---------------------------------------------------------------------------
# Cycle 6 — suggested_schedule is present with sections and a note
# ---------------------------------------------------------------------------

def test_suggested_schedule_present(client):
    data = client.get("/api/enrollment/profile").json()
    assert "suggested_schedule" in data


def test_suggested_schedule_has_sections_and_note(client):
    sched = client.get("/api/enrollment/profile").json()["suggested_schedule"]
    assert isinstance(sched.get("sections"), list)
    assert len(sched["sections"]) >= 1
    assert sched.get("note"), "suggested_schedule missing note"


def test_suggested_schedule_sections_have_required_fields(client):
    sections = client.get("/api/enrollment/profile").json()["suggested_schedule"]["sections"]
    for s in sections:
        assert s.get("course"), f"Section missing course: {s}"
        assert s.get("section"), f"Section missing section code: {s}"
        assert s.get("days"), f"Section missing days: {s}"
        assert s.get("time"), f"Section missing time: {s}"


# ---------------------------------------------------------------------------
# Cycle 7 — validate-schedule creates three enrollment workflow items
#           and all three appear in GET /api/workflows
# ---------------------------------------------------------------------------

VALIDATE_PAYLOADS = [
    {
        "stage": "enrollment",
        "trigger": "Schedule validated — registrar approval required",
        "owner_name": "Khalid Al-Fadli",
        "owner_role": "registrar specialist",
        "status": "pending",
        "description": "Validate schedule and clear registration holds for Mariam Al-Kandari",
        "student_id": "stu-002",
    },
    {
        "stage": "enrollment",
        "trigger": "Schedule validated — financial aid clearance required",
        "owner_name": "Finance Officer",
        "owner_role": "financial aid officer",
        "status": "pending",
        "description": "Clear financial hold for Mariam Al-Kandari",
        "student_id": "stu-002",
    },
    {
        "stage": "enrollment",
        "trigger": "Schedule validated — document verification required",
        "owner_name": "Document Verification Officer",
        "owner_role": "student affairs officer",
        "status": "pending",
        "description": "Verify missing documents for Mariam Al-Kandari",
        "student_id": "stu-002",
    },
]


def test_validate_schedule_creates_three_workflow_items(client):
    created_ids = []
    for payload in VALIDATE_PAYLOADS:
        res = client.post("/api/workflows", json=payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        created_ids.append(res.json()["id"])
    assert len(created_ids) == 3


def test_all_three_workflow_items_appear_in_workflow_list(client):
    # Create fresh items to verify they land in the list
    created_ids = set()
    for payload in VALIDATE_PAYLOADS:
        res = client.post("/api/workflows", json=payload)
        assert res.status_code == 201
        created_ids.add(res.json()["id"])

    all_items = client.get("/api/workflows").json()
    all_ids = {item["id"] for item in all_items}
    assert created_ids.issubset(all_ids), (
        f"Missing from workflow list: {created_ids - all_ids}"
    )


def test_workflow_items_have_enrollment_stage(client):
    all_items = client.get("/api/workflows").json()
    enrollment_items = [i for i in all_items if i["stage"] == "enrollment"]
    assert len(enrollment_items) >= 3


# ---------------------------------------------------------------------------
# Issue #27 — live watsonx Orchestrate agent rationale, with scripted fallback
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


def test_suggested_schedule_uses_live_agent_note_when_run_completes(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ENROLLMENT", AGENT_ENROLLMENT)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-001"}))
        router.get(f"{RUNS_URL}/run-001").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-001", "Live agent: switch MATH101 to section 02.")
            )
        )

        sched = client.get("/api/enrollment/profile").json()["suggested_schedule"]

    assert sched["note"] == "Live agent: switch MATH101 to section 02."


def test_suggested_schedule_falls_back_to_computed_note_when_run_fails(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ENROLLMENT", AGENT_ENROLLMENT)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-fail"}))
        router.get(f"{RUNS_URL}/run-fail").mock(
            return_value=httpx.Response(200, json={"id": "run-fail", "status": "failed"})
        )

        sched = client.get("/api/enrollment/profile").json()["suggested_schedule"]

    assert "Switch MATH101 from section 01" in sched["note"]


def test_suggested_schedule_falls_back_to_computed_note_when_run_times_out(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ENROLLMENT", AGENT_ENROLLMENT)
    monkeypatch.setattr(orchestrate_module, "POLL_INTERVAL", 0)

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-timeout"}))
        router.get(f"{RUNS_URL}/run-timeout").mock(
            return_value=httpx.Response(200, json={"id": "run-timeout", "status": "running"})
        )

        sched = client.get("/api/enrollment/profile").json()["suggested_schedule"]

    assert "Switch MATH101 from section 01" in sched["note"]


def test_scripted_mode_never_contacts_orchestrate(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "scripted")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ENROLLMENT", AGENT_ENROLLMENT)

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        iam_route = router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        sched = client.get("/api/enrollment/profile").json()["suggested_schedule"]

    assert not iam_route.called, "scripted mode must not contact IAM/Orchestrate"
    assert "Switch MATH101 from section 01" in sched["note"]


def test_suggested_schedule_falls_back_when_ai_mode_live_but_orchestrate_unconfigured(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.delenv("WXO_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_ID_ENROLLMENT", raising=False)

    sched = client.get("/api/enrollment/profile").json()["suggested_schedule"]

    assert "Switch MATH101 from section 01" in sched["note"]
