"""Tests for the Academic Risk page API (issue #15)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


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
