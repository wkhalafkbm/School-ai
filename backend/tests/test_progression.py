"""Tests for the Progression page API (issue #16)."""

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
# Cycle 1 — tracer bullet: GET /api/progression/profile returns 200
# ---------------------------------------------------------------------------

def test_progression_profile_returns_200(client):
    response = client.get("/api/progression/profile")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — stage summary: health and on_track / at_risk graduation counts
# ---------------------------------------------------------------------------

def test_stage_summary_has_health(client):
    summary = client.get("/api/progression/profile").json()["stage_summary"]
    assert "health" in summary
    assert summary["health"] in {"on_track", "watch", "needs_attention", "urgent"}


def test_stage_summary_has_on_track_and_at_risk_counts(client):
    summary = client.get("/api/progression/profile").json()["stage_summary"]
    assert "on_track_count" in summary
    assert "at_risk_count" in summary
    assert isinstance(summary["on_track_count"], int)
    assert isinstance(summary["at_risk_count"], int)


def test_stage_summary_counts_non_negative(client):
    summary = client.get("/api/progression/profile").json()["stage_summary"]
    assert summary["on_track_count"] >= 0
    assert summary["at_risk_count"] >= 0


def test_stage_summary_has_at_risk_students(client):
    # Noor (stu-004) is on_track=false → at least one at_risk student
    summary = client.get("/api/progression/profile").json()["stage_summary"]
    assert summary["at_risk_count"] >= 1


# ---------------------------------------------------------------------------
# Cycle 3 — Noor Al-Hamad student profile
# ---------------------------------------------------------------------------

def test_student_is_noor_al_hamad(client):
    student = client.get("/api/progression/profile").json()["student"]
    assert student["name"] == "Noor Al-Hamad"
    assert student["id"] == "stu-004"


def test_student_has_program_and_year_level(client):
    student = client.get("/api/progression/profile").json()["student"]
    assert student["program_name"]
    assert isinstance(student["year_level"], int)
    assert isinstance(student["gpa"], float)


# ---------------------------------------------------------------------------
# Cycle 4 — credit map shows earned vs required with substitutions
# ---------------------------------------------------------------------------

def test_credit_map_present(client):
    data = client.get("/api/progression/profile").json()
    assert "credit_map" in data


def test_credit_map_total_credits(client):
    credit_map = client.get("/api/progression/profile").json()["credit_map"]
    assert "total" in credit_map
    assert credit_map["total"]["earned"] == 72
    assert credit_map["total"]["required"] == 132


def test_credit_map_core_credits(client):
    credit_map = client.get("/api/progression/profile").json()["credit_map"]
    assert "core" in credit_map
    assert credit_map["core"]["earned"] == 33
    assert credit_map["core"]["required"] == 60


def test_credit_map_math_credits(client):
    credit_map = client.get("/api/progression/profile").json()["credit_map"]
    assert "math" in credit_map
    assert credit_map["math"]["earned"] == 9
    assert credit_map["math"]["required"] == 12


def test_credit_map_capstone_and_internship(client):
    credit_map = client.get("/api/progression/profile").json()["credit_map"]
    assert "capstone" in credit_map
    assert credit_map["capstone"]["completed"] is False
    assert "internship" in credit_map
    assert credit_map["internship"]["hours_completed"] == 0
    assert credit_map["internship"]["hours_required"] == 240


def test_credit_map_has_substitutions(client):
    credit_map = client.get("/api/progression/profile").json()["credit_map"]
    assert "substitutions" in credit_map
    assert isinstance(credit_map["substitutions"], list)
    assert len(credit_map["substitutions"]) >= 1


def test_credit_map_substitution_has_required_fields(client):
    substitutions = client.get("/api/progression/profile").json()["credit_map"]["substitutions"]
    for sub in substitutions:
        assert "substituted_course" in sub, f"Missing substituted_course: {sub}"
        assert "note" in sub, f"Missing note: {sub}"


# ---------------------------------------------------------------------------
# Cycle 5 — bottleneck course identified with section capacity
# ---------------------------------------------------------------------------

def test_bottleneck_course_present(client):
    data = client.get("/api/progression/profile").json()
    assert "bottleneck_course" in data
    assert data["bottleneck_course"] is not None


def test_bottleneck_course_has_capacity_data(client):
    course = client.get("/api/progression/profile").json()["bottleneck_course"]
    assert "course_code" in course
    assert "section_capacity" in course
    assert "section_enrolled" in course
    assert "fill_rate" in course
    assert isinstance(course["fill_rate"], float)
    assert 0.0 < course["fill_rate"] <= 1.0


def test_bottleneck_course_framed_as_institutional_constraint(client):
    course = client.get("/api/progression/profile").json()["bottleneck_course"]
    assert course.get("constraint_type") == "institutional"
    assert course.get("constraint_note"), "constraint_note should be a non-empty string"


def test_bottleneck_course_is_cs302(client):
    # CS302 Operating Systems (sec-005) has highest fill rate at 90%
    course = client.get("/api/progression/profile").json()["bottleneck_course"]
    assert course["course_code"] == "CS302"
    assert course["section_capacity"] == 30
    assert course["section_enrolled"] == 27


# ---------------------------------------------------------------------------
# Cycle 6 — cohort delay forecast
# ---------------------------------------------------------------------------

def test_cohort_delay_forecast_present(client):
    data = client.get("/api/progression/profile").json()
    assert "cohort_delay_forecast" in data


def test_cohort_delay_forecast_has_required_fields(client):
    forecast = client.get("/api/progression/profile").json()["cohort_delay_forecast"]
    assert "students_at_risk" in forecast
    assert "total_cohort" in forecast
    assert isinstance(forecast["students_at_risk"], int)
    assert isinstance(forecast["total_cohort"], int)


def test_cohort_delay_forecast_at_least_one_student(client):
    forecast = client.get("/api/progression/profile").json()["cohort_delay_forecast"]
    assert forecast["students_at_risk"] >= 1
    assert forecast["total_cohort"] >= forecast["students_at_risk"]


# ---------------------------------------------------------------------------
# Cycle 7 — below-target SLO signal linked to bottleneck course
# ---------------------------------------------------------------------------

def test_bottleneck_slo_signal_present(client):
    data = client.get("/api/progression/profile").json()
    assert "bottleneck_slo_signal" in data
    assert data["bottleneck_slo_signal"] is not None


def test_bottleneck_slo_signal_has_required_fields(client):
    signal = client.get("/api/progression/profile").json()["bottleneck_slo_signal"]
    assert "slo_code" in signal
    assert "description" in signal
    assert "proficiency_rate" in signal
    assert "below_target" in signal


def test_bottleneck_slo_is_below_target(client):
    signal = client.get("/api/progression/profile").json()["bottleneck_slo_signal"]
    assert signal["below_target"] is True


def test_bottleneck_slo_linked_to_cs302(client):
    signal = client.get("/api/progression/profile").json()["bottleneck_slo_signal"]
    assert signal["slo_code"] == "CS302-SLO1"
    assert signal["proficiency_rate"] == pytest.approx(0.41)


# ---------------------------------------------------------------------------
# Cycle 8 — AI graduation risk summary with confidence and rationale
# ---------------------------------------------------------------------------

def test_graduation_risk_summary_present(client):
    data = client.get("/api/progression/profile").json()
    assert "graduation_risk_summary" in data


def test_graduation_risk_summary_has_confidence(client):
    summary = client.get("/api/progression/profile").json()["graduation_risk_summary"]
    assert "confidence" in summary
    assert summary["confidence"] in {"High", "Medium", "Low"}


def test_graduation_risk_summary_has_rationale(client):
    summary = client.get("/api/progression/profile").json()["graduation_risk_summary"]
    assert "rationale" in summary
    assert len(summary["rationale"]) > 20


def test_graduation_risk_summary_has_actions(client):
    summary = client.get("/api/progression/profile").json()["graduation_risk_summary"]
    assert "actions" in summary
    assert isinstance(summary["actions"], list)
    assert len(summary["actions"]) >= 1


def test_graduation_risk_actions_have_type_and_description(client):
    actions = client.get("/api/progression/profile").json()["graduation_risk_summary"]["actions"]
    for action in actions:
        assert action.get("type"), f"Action missing type: {action}"
        assert action.get("description"), f"Action missing description: {action}"


# ---------------------------------------------------------------------------
# Cycle 9 — seeded plan update item (wfl-004, owned by department chair)
# ---------------------------------------------------------------------------

def test_plan_update_item_present(client):
    data = client.get("/api/progression/profile").json()
    assert "plan_update_item" in data
    assert data["plan_update_item"] is not None


def test_plan_update_item_has_owner_info(client):
    item = client.get("/api/progression/profile").json()["plan_update_item"]
    assert item.get("owner_name") == "Dr. Bader Al-Otaibi"
    assert item.get("owner_role") == "department chair"


def test_plan_update_item_has_trigger(client):
    item = client.get("/api/progression/profile").json()["plan_update_item"]
    assert item.get("trigger"), "trigger should be non-empty"


def test_plan_update_item_is_seeded_workflow(client):
    item = client.get("/api/progression/profile").json()["plan_update_item"]
    assert item["id"] == "wfl-004"
    assert item["status"] == "in_review"


# ---------------------------------------------------------------------------
# Cycle 10 — "Update Graduation Plan" creates academic advisor workflow item
# ---------------------------------------------------------------------------

UPDATE_PLAN_PAYLOAD = {
    "stage": "progression",
    "trigger": "Graduation plan update requested — routing to academic advisor",
    "owner_name": "Academic Advisor",
    "owner_role": "academic advisor",
    "status": "pending",
    "description": "Review and update Noor Al-Hamad's four-year graduation plan to address 12-credit deficit",
    "student_id": "stu-004",
}


def test_update_graduation_plan_creates_workflow_item(client):
    res = client.post("/api/workflows", json=UPDATE_PLAN_PAYLOAD)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    assert res.json().get("id"), "Created item must have an id"


def test_update_graduation_plan_routed_to_academic_advisor(client):
    res = client.post("/api/workflows", json=UPDATE_PLAN_PAYLOAD)
    assert res.status_code == 201
    item = res.json()
    assert item["owner_role"] == "academic advisor"
    assert item["stage"] == "progression"


def test_approved_plan_update_appears_in_workflow_list(client):
    created = client.post("/api/workflows", json=UPDATE_PLAN_PAYLOAD)
    assert created.status_code == 201
    created_id = created.json()["id"]

    all_items = client.get("/api/workflows").json()
    all_ids = {item["id"] for item in all_items}
    assert created_id in all_ids, f"Created item {created_id} not found in workflow list"
