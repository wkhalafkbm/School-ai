import os
import pytest
from pathlib import Path
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


# ── /api/overview/metrics ──────────────────────────────────────────────────────

def test_metrics_returns_200(client):
    response = client.get("/api/overview/metrics")
    assert response.status_code == 200


def test_metrics_has_all_five_kpi_keys(client):
    data = client.get("/api/overview/metrics").json()
    assert set(data.keys()) == {
        "students_needing_attention",
        "at_risk_detected_early",
        "registration_issues_resolved",
        "graduation_delays_prevented",
        "faculty_overload_alerts",
    }


def test_metrics_all_values_are_non_negative_integers(client):
    data = client.get("/api/overview/metrics").json()
    for key, val in data.items():
        assert isinstance(val, int) and val >= 0, f"{key}={val!r} is not a non-negative int"


def test_metrics_values_match_seeded_data(client):
    data = client.get("/api/overview/metrics").json()
    # seed.py coerces 'none' → False, so only 'high'/'medium'/'low' risk_flag rows count
    assert data["students_needing_attention"] == 3
    assert data["at_risk_detected_early"] == 1
    assert data["registration_issues_resolved"] == 0
    assert data["graduation_delays_prevented"] == 1
    assert data["faculty_overload_alerts"] == 1  # fac-001 is 15 credits against a 12-credit cap


# ── /api/overview/journey-health ──────────────────────────────────────────────

def test_journey_health_returns_200(client):
    response = client.get("/api/overview/journey-health")
    assert response.status_code == 200


def test_journey_health_has_all_five_stages(client):
    data = client.get("/api/overview/journey-health").json()
    assert set(data.keys()) == {
        "onboarding",
        "registration",
        "academic_progress",
        "graduation_planning",
        "career",
    }


def test_journey_health_values_are_valid_status_codes(client):
    from app.status import StatusCode
    valid = {s.value for s in StatusCode}
    data = client.get("/api/overview/journey-health").json()
    for stage, status in data.items():
        assert status in valid, f"stage {stage!r} has invalid status {status!r}"


def test_journey_health_onboarding_reflects_incomplete_tasks(client):
    # 4/12 tasks incomplete → ~33% → watch
    data = client.get("/api/overview/journey-health").json()
    assert data["onboarding"] in ("watch", "needs_attention", "urgent")


def test_journey_health_graduation_planning_reflects_on_track_ratio(client):
    # 2/5 not on_track → 40% → above 30% threshold → urgent
    data = client.get("/api/overview/journey-health").json()
    assert data["graduation_planning"] == "urgent"


# ── /api/overview/priority-queue ──────────────────────────────────────────────

def test_priority_queue_returns_200(client):
    response = client.get("/api/overview/priority-queue")
    assert response.status_code == 200


def test_priority_queue_returns_a_list(client):
    data = client.get("/api/overview/priority-queue").json()
    assert isinstance(data, list)


def test_priority_queue_items_have_required_fields(client):
    data = client.get("/api/overview/priority-queue").json()
    assert len(data) > 0
    for item in data:
        assert "student_name" in item
        assert "stage" in item
        assert "status" in item
        assert "reason" in item


def test_priority_queue_capped_at_20(client):
    data = client.get("/api/overview/priority-queue").json()
    assert len(data) <= 20


def test_priority_queue_ordered_by_severity_descending(client):
    from app.status import StatusCode, status_meta
    data = client.get("/api/overview/priority-queue").json()
    ranks = [status_meta[StatusCode(item["status"])]["severity_rank"] for item in data]
    assert ranks == sorted(ranks, reverse=True)


# ── /api/overview/chart-data ──────────────────────────────────────────────────

def test_chart_data_returns_200(client):
    response = client.get("/api/overview/chart-data")
    assert response.status_code == 200


def test_chart_data_has_all_four_series(client):
    data = client.get("/api/overview/chart-data").json()
    assert set(data.keys()) == {
        "enrollments_by_semester",
        "gpa_distribution",
        "intervention_outcomes",
        "lms_risk_by_semester",
    }


def test_chart_data_enrollments_by_semester_is_list_of_objects(client):
    data = client.get("/api/overview/chart-data").json()
    series = data["enrollments_by_semester"]
    assert isinstance(series, list) and len(series) > 0
    for item in series:
        assert "semester" in item and "count" in item


def test_chart_data_gpa_distribution_covers_buckets(client):
    data = client.get("/api/overview/chart-data").json()
    buckets = {b["bucket"] for b in data["gpa_distribution"]}
    assert buckets == {"<2.0", "2.0-2.5", "2.5-3.0", "3.0-3.5", "3.5-4.0"}


def test_chart_data_intervention_outcomes_is_list(client):
    data = client.get("/api/overview/chart-data").json()
    assert isinstance(data["intervention_outcomes"], list)


def test_chart_data_lms_risk_by_semester_is_list(client):
    data = client.get("/api/overview/chart-data").json()
    assert isinstance(data["lms_risk_by_semester"], list)
