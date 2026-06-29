"""Tests for the Career & Alumni page API (issue #20)."""

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
