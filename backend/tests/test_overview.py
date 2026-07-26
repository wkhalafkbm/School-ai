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
        assert "student_id" in item
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


# ── /api/overview/metrics/{metric_key}/detail ─────────────────────────────────

DETAIL_URL = "/api/overview/metrics/students_needing_attention/detail"

# Every metric names its own destination — no two panels may share rows, and a
# wrong destination would strand the user on an unrelated stage page.
EXPECTED_DESTINATIONS = {
    "students_needing_attention": {"label": "Academic Risk", "href": "/academic-risk"},
    "at_risk_detected_early": {"label": "Academic Risk", "href": "/academic-risk"},
    "registration_issues_resolved": {"label": "Workflow Activity", "href": "/workflow-activity"},
    "graduation_delays_prevented": {"label": "Progression", "href": "/progression"},
    "faculty_overload_alerts": {"label": "Teaching Readiness", "href": "/teaching-readiness"},
}

ALL_METRIC_KEYS = list(EXPECTED_DESTINATIONS)


@pytest.mark.parametrize("metric_key", ALL_METRIC_KEYS)
def test_metric_detail_returns_200_for_every_metric(client, metric_key):
    assert client.get(f"/api/overview/metrics/{metric_key}/detail").status_code == 200


@pytest.mark.parametrize("metric_key", ALL_METRIC_KEYS)
def test_metric_detail_payload_shape_is_identical_across_metrics(client, metric_key):
    data = client.get(f"/api/overview/metrics/{metric_key}/detail").json()
    assert set(data.keys()) == {
        "metric_key", "definition", "destination", "total", "rows", "empty_message",
    }
    assert data["metric_key"] == metric_key
    assert data["definition"].strip()
    assert data["empty_message"].strip()
    assert data["destination"] == EXPECTED_DESTINATIONS[metric_key]
    for row in data["rows"]:
        assert set(row.keys()) == {"id", "name", "context", "status", "detail"}


@pytest.mark.parametrize("metric_key", ALL_METRIC_KEYS)
def test_metric_detail_total_matches_the_kpi_count_on_the_card(client, metric_key):
    # The panel explains the number on the card, so the two must never disagree.
    kpi = client.get("/api/overview/metrics").json()[metric_key]
    detail = client.get(f"/api/overview/metrics/{metric_key}/detail").json()
    assert detail["total"] == kpi
    assert len(detail["rows"]) == min(kpi, 6)


def test_metric_detail_definitions_are_written_per_metric_not_shared(client):
    definitions = [
        client.get(f"/api/overview/metrics/{key}/detail").json()["definition"]
        for key in ALL_METRIC_KEYS
    ]
    assert len(set(definitions)) == len(definitions)


def test_metric_detail_rows_identify_the_students_behind_the_count(client):
    rows = client.get(DETAIL_URL).json()["rows"]

    # The seeded at-risk students: stu-003 (high), stu-004 and stu-019 (medium).
    assert {r["name"] for r in rows} == {"Fahad Al-Ajmi", "Noor Al-Hamad", "Khalid Al-Mansouri"}

    fahad = next(r for r in rows if r["name"] == "Fahad Al-Ajmi")
    assert fahad == {
        "id": "stu-003",
        "name": "Fahad Al-Ajmi",
        "context": "Computer Science",
        "status": "urgent",
        "detail": "Risk flag: high",
    }


def test_metric_detail_rows_are_ordered_by_severity_then_by_name(client):
    rows = client.get(DETAIL_URL).json()["rows"]
    assert [r["name"] for r in rows] == [
        "Fahad Al-Ajmi",        # urgent — a 'high' flag outranks everything below
        "Khalid Al-Mansouri",   # needs_attention, and K sorts before N
        "Noor Al-Hamad",        # needs_attention
    ]


def test_metric_detail_404s_for_an_unknown_metric(client):
    assert client.get("/api/overview/metrics/not_a_metric/detail").status_code == 404


# ── at_risk_detected_early — a single-row metric on the seeded data ───────────

def test_at_risk_detected_early_names_the_one_uncased_low_gpa_student(client):
    data = client.get("/api/overview/metrics/at_risk_detected_early/detail").json()

    # stu-099 is the only student under 2.5 GPA with no open support case;
    # the other low-GPA students already have one and so are not "early".
    assert data["total"] == 1
    assert data["rows"] == [
        {
            "id": "stu-099",
            "name": "Mansour Al-Subaie",
            "context": "Business Administration",
            "status": "watch",
            "detail": "GPA 2.4 — no open support case",
        }
    ]


# ── registration_issues_resolved — genuinely zero on the seeded data ──────────

def test_registration_issues_resolved_is_empty_but_still_explains_itself(client):
    data = client.get("/api/overview/metrics/registration_issues_resolved/detail").json()

    assert data["total"] == 0
    assert data["rows"] == []
    # The empty message speaks in this metric's own terms, not a generic "no data".
    assert "registration" in data["empty_message"].lower()
    assert data["destination"] == EXPECTED_DESTINATIONS["registration_issues_resolved"]


@pytest.fixture
def one_resolved_registration_item(engine):
    """Approve a registration-resolution item so the zero metric grows a row."""
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO workflow_items
                    (id, student_id, workflow_type, status, "trigger", title, data_source)
                VALUES
                    ('wfl-t58', 'stu-002', 'registration_resolution', 'approved',
                     'Financial hold detected', 'Registration Hold Resolution', 'SIS')
            """)
        )
        conn.commit()

    yield

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM workflow_items WHERE id = 'wfl-t58'"))
        conn.commit()


def test_registration_issues_resolved_rows_say_what_was_resolved(
    client, one_resolved_registration_item
):
    data = client.get("/api/overview/metrics/registration_issues_resolved/detail").json()

    assert data["total"] == 1
    assert data["rows"] == [
        {
            "id": "wfl-t58",
            "name": "Mariam Al-Kandari",
            "context": "Information Systems",
            "status": "on_track",  # an achievement — resolved items are positive
            "detail": "Resolved: Financial hold detected",
        }
    ]


# ── graduation_delays_prevented — an achievement metric ───────────────────────

def test_graduation_delays_prevented_names_the_completed_intervention(client):
    data = client.get("/api/overview/metrics/graduation_delays_prevented/detail").json()

    assert data["total"] == 1
    assert data["rows"] == [
        {
            "id": "int-004",
            "name": "Khalid Al-Mansouri",
            "context": "Computer Science",
            "status": "on_track",  # an achievement — completed interventions are positive
            "detail": "Advisor meeting",
        }
    ]


@pytest.fixture
def six_more_completed_interventions(engine):
    """Push completed interventions past the six-row cap."""
    from sqlalchemy import text

    with engine.connect() as conn:
        for i in range(6):
            conn.execute(
                text("""
                    INSERT INTO interventions
                        (id, student_id, intervention_type, status, data_source)
                    VALUES (:id, 'stu-003', 'tutoring_referral', 'completed', 'SIS')
                """),
                {"id": f"int-cap-{i}"},
            )
        conn.commit()

    yield

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM interventions WHERE id LIKE 'int-cap-%'"))
        conn.commit()


def test_graduation_delays_prevented_caps_at_six_and_stays_uniformly_positive(
    client, six_more_completed_interventions
):
    data = client.get("/api/overview/metrics/graduation_delays_prevented/detail").json()

    # 1 seeded + 6 from the fixture; the cap bites while total counts everyone.
    assert data["total"] == 7
    assert len(data["rows"]) == 6
    assert all(r["status"] == "on_track" for r in data["rows"])


# ── faculty_overload_alerts — rows are faculty, not students ──────────────────

def test_faculty_overload_alerts_shows_department_and_load_against_ceiling(client):
    data = client.get("/api/overview/metrics/faculty_overload_alerts/detail").json()

    assert data["total"] == 1
    assert data["rows"] == [
        {
            "id": "fac-001",
            "name": "Dr. Ahmed Al-Rashidi",
            "context": "Computer Science",  # department — faculty have no programme
            "status": "urgent",  # 15 credits against a 12-credit ceiling
            "detail": "15 of 12 credits",
        }
    ]


@pytest.fixture
def five_extra_at_risk_students(engine):
    """Push the at-risk population past the six-row cap, then take it back down.

    They all carry a 'low' flag, so they sort below the seeded students and the
    cap has to bite in the middle of this group rather than at a natural break.
    """
    from sqlalchemy import text

    ids = [f"stu-cap-{i}" for i in range(5)]
    with engine.connect() as conn:
        for i, sid in enumerate(ids):
            conn.execute(
                text("""
                    INSERT INTO students (id, name, program_id, status, data_source)
                    VALUES (:id, :name, 'prog-001', 'enrolled', 'SIS')
                """),
                {"id": sid, "name": f"Zzz Capfiller {i}"},
            )
            conn.execute(
                text("""
                    INSERT INTO lms_signals (id, student_id, course_id, semester, risk_flag, data_source)
                    VALUES (:id, :sid, 'crs-001', '2024-Fall', 'low', 'LMS')
                """),
                {"id": f"lms-cap-{i}", "sid": sid},
            )
        conn.commit()

    yield ids

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM lms_signals WHERE id LIKE 'lms-cap-%'"))
        conn.execute(text("DELETE FROM students WHERE id LIKE 'stu-cap-%'"))
        conn.commit()


def test_metric_detail_caps_rows_at_six_while_the_total_still_counts_everyone(
    client, five_extra_at_risk_students
):
    data = client.get(DETAIL_URL).json()

    # 3 seeded at-risk students + 5 added by the fixture
    assert data["total"] == 8
    assert len(data["rows"]) == 6


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
