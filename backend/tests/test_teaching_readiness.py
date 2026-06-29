"""Tests for the Teaching Readiness page API (issue #14)."""

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
# Cycle 1 — tracer bullet: GET /api/teaching-readiness/profile returns 200
# ---------------------------------------------------------------------------

def test_teaching_readiness_profile_returns_200(client):
    response = client.get("/api/teaching-readiness/profile")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — stage_summary has health, cohort_size, aggregate_readiness_score
# ---------------------------------------------------------------------------

def test_stage_summary_has_health(client):
    summary = client.get("/api/teaching-readiness/profile").json()["stage_summary"]
    assert "health" in summary
    assert summary["health"] in {"on_track", "watch", "needs_attention", "urgent"}


def test_stage_summary_has_cohort_size(client):
    summary = client.get("/api/teaching-readiness/profile").json()["stage_summary"]
    assert "cohort_size" in summary
    assert isinstance(summary["cohort_size"], int)
    assert summary["cohort_size"] > 0


def test_stage_summary_has_aggregate_readiness_score(client):
    summary = client.get("/api/teaching-readiness/profile").json()["stage_summary"]
    assert "aggregate_readiness_score" in summary
    score = summary["aggregate_readiness_score"]
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100


# ---------------------------------------------------------------------------
# Cycle 3 — featured_course is CS101 with slo_trends for 3 semesters
# ---------------------------------------------------------------------------

def test_featured_course_is_present(client):
    data = client.get("/api/teaching-readiness/profile").json()
    assert "featured_course" in data


def test_featured_course_is_cs101(client):
    course = client.get("/api/teaching-readiness/profile").json()["featured_course"]
    assert course["code"] == "CS101"
    assert course.get("name")


def test_featured_course_has_slo_trends(client):
    course = client.get("/api/teaching-readiness/profile").json()["featured_course"]
    assert "slo_trends" in course
    assert isinstance(course["slo_trends"], list)
    assert len(course["slo_trends"]) >= 1


# ---------------------------------------------------------------------------
# Cycle 4 — each SLO trend row has proficiency_rate per semester (3 semesters)
# ---------------------------------------------------------------------------

def test_slo_trends_have_slo_code_and_description(client):
    trends = client.get("/api/teaching-readiness/profile").json()["featured_course"]["slo_trends"]
    for t in trends:
        assert t.get("slo_code"), f"Missing slo_code: {t}"
        assert t.get("description"), f"Missing description: {t}"


def test_slo_trends_have_three_semesters(client):
    trends = client.get("/api/teaching-readiness/profile").json()["featured_course"]["slo_trends"]
    for t in trends:
        semesters = t.get("semesters", [])
        assert len(semesters) == 3, f"Expected 3 semesters for {t['slo_code']}, got {len(semesters)}"


def test_slo_trend_semesters_have_proficiency_rate(client):
    trends = client.get("/api/teaching-readiness/profile").json()["featured_course"]["slo_trends"]
    for t in trends:
        for s in t["semesters"]:
            assert "semester" in s
            assert "proficiency_rate" in s
            assert 0.0 <= s["proficiency_rate"] <= 1.0


def test_slo_trend_semesters_are_in_chronological_order(client):
    """Semesters must sort by year then season (Spring < Fall), not alphabetically.

    Alphabetical order puts 2024-Fall before 2024-Spring because 'F' < 'S',
    which produces a misleading trend line on the chart.
    """
    SEASON_RANK = {"Spring": 0, "Summer": 1, "Fall": 2}

    def sem_key(sem: str):
        year, season = sem.split("-")
        return (int(year), SEASON_RANK.get(season, 99))

    trends = client.get("/api/teaching-readiness/profile").json()["featured_course"]["slo_trends"]
    for t in trends:
        semesters = [s["semester"] for s in t["semesters"]]
        assert semesters == sorted(semesters, key=sem_key), (
            f"Semesters for {t['slo_code']} are not in chronological order: {semesters}"
        )


# ---------------------------------------------------------------------------
# Cycle 5 — assessment_failure_rates has failure_rate + rules_engine_result per SLO
# ---------------------------------------------------------------------------

def test_assessment_failure_rates_present(client):
    data = client.get("/api/teaching-readiness/profile").json()
    assert "assessment_failure_rates" in data
    assert isinstance(data["assessment_failure_rates"], list)
    assert len(data["assessment_failure_rates"]) >= 1


def test_assessment_failure_rates_have_required_fields(client):
    rates = client.get("/api/teaching-readiness/profile").json()["assessment_failure_rates"]
    valid = {"pass", "fail", "exception"}
    for r in rates:
        assert r.get("slo_code"), f"Missing slo_code: {r}"
        assert r.get("description"), f"Missing description: {r}"
        assert "failure_rate" in r
        assert 0.0 <= r["failure_rate"] <= 1.0
        assert r.get("rules_engine_result") in valid, (
            f"Invalid result {r.get('rules_engine_result')!r}"
        )


# ---------------------------------------------------------------------------
# Cycle 6 — no "confidence" field in assessment_failure_rates
# ---------------------------------------------------------------------------

def test_assessment_failure_rates_have_no_confidence_field(client):
    import json
    raw = json.dumps(client.get("/api/teaching-readiness/profile").json()["assessment_failure_rates"])
    assert "confidence" not in raw, "Forbidden 'confidence' field found in assessment_failure_rates"


# ---------------------------------------------------------------------------
# Cycle 7 — faculty_workload shows overloaded faculty with status "urgent"
# ---------------------------------------------------------------------------

def test_faculty_workload_present(client):
    data = client.get("/api/teaching-readiness/profile").json()
    assert "faculty_workload" in data
    assert isinstance(data["faculty_workload"], list)
    assert len(data["faculty_workload"]) >= 1


def test_faculty_workload_has_required_fields(client):
    workload = client.get("/api/teaching-readiness/profile").json()["faculty_workload"]
    for f in workload:
        assert f.get("id"), f"Missing id: {f}"
        assert f.get("name"), f"Missing name: {f}"
        assert f.get("department"), f"Missing department: {f}"
        assert "current_credits" in f
        assert "max_credits" in f
        assert "overloaded" in f
        assert f.get("status") in {"on_track", "watch", "needs_attention", "urgent"}


def test_dr_ahmed_alrashidi_is_overloaded(client):
    workload = client.get("/api/teaching-readiness/profile").json()["faculty_workload"]
    ahmed = next((f for f in workload if "Ahmed" in f["name"]), None)
    assert ahmed is not None, "Dr. Ahmed Al-Rashidi not found in faculty_workload"
    assert ahmed["overloaded"] is True
    assert ahmed["status"] == "urgent"
    assert ahmed["current_credits"] > ahmed["max_credits"]


# ---------------------------------------------------------------------------
# Cycle 8 — workload_threshold_result is "fail" (any faculty overloaded)
# ---------------------------------------------------------------------------

def test_workload_threshold_result_present(client):
    data = client.get("/api/teaching-readiness/profile").json()
    assert "workload_threshold_result" in data
    assert data["workload_threshold_result"] in {"pass", "fail"}


def test_workload_threshold_result_is_fail_when_overloaded(client):
    data = client.get("/api/teaching-readiness/profile").json()
    overloaded = any(f["overloaded"] for f in data["faculty_workload"])
    if overloaded:
        assert data["workload_threshold_result"] == "fail"


# ---------------------------------------------------------------------------
# Cycle 9 — no "confidence" field anywhere in the response
# ---------------------------------------------------------------------------

def test_no_confidence_field_in_response(client):
    import json
    raw = json.dumps(client.get("/api/teaching-readiness/profile").json())
    assert "confidence" not in raw, "Forbidden 'confidence' field found in response"
