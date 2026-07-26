"""Tests for POST /api/academic-risk/evaluate-trends (issue #64)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

EVALUATE_URL = "/api/academic-risk/evaluate-trends"


@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(autouse=True, scope="module")
def seeded_db(engine):
    from alembic.config import Config
    from alembic import command

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


@pytest.fixture(autouse=True)
def no_trend_items(engine):
    """
    Start every test from a database with no trend-created items, so creation
    and idempotency are observed from a known baseline. Seeding already runs the
    evaluation (see test_seed), which would otherwise mask the first create.
    """
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM workflow_items WHERE trigger LIKE 'gpa_trend:%'"))
        conn.commit()
    yield


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
# Cycle 1 — the endpoint reports what it evaluated
# ---------------------------------------------------------------------------


def test_evaluate_trends_returns_a_summary(client):
    response = client.post(EVALUATE_URL)
    assert response.status_code == 200
    assert set(response.json()) == {
        "evaluated",
        "flagged",
        "created",
        "skipped_existing",
    }


# ---------------------------------------------------------------------------
# Cycle 2 — flagged students get a workflow item
# ---------------------------------------------------------------------------


def trend_items(client):
    return [
        item for item in client.get("/api/workflows").json()
        if (item["trigger"] or "").startswith("gpa_trend:")
    ]


def test_evaluate_trends_creates_one_item_per_flagged_student(client):
    summary = client.post(EVALUATE_URL).json()
    assert summary["flagged"] > 0
    assert summary["created"] == summary["flagged"]
    assert len(trend_items(client)) == summary["created"]


def test_created_items_carry_the_academic_progress_stage(client):
    client.post(EVALUATE_URL)
    items = trend_items(client)
    assert items
    for item in items:
        assert item["stage"] == "academic_progress"


# ---------------------------------------------------------------------------
# Cycle 3 — re-running the endpoint is a no-op
# ---------------------------------------------------------------------------


def test_second_evaluation_creates_nothing(client):
    first = client.post(EVALUATE_URL).json()
    second = client.post(EVALUATE_URL).json()

    assert second["created"] == 0
    assert second["skipped_existing"] == first["created"]
    assert second["flagged"] == first["flagged"]


def test_second_evaluation_leaves_no_duplicate_items(client):
    client.post(EVALUATE_URL)
    after_first = trend_items(client)
    client.post(EVALUATE_URL)
    after_second = trend_items(client)

    assert len(after_second) == len(after_first)
    assert {i["id"] for i in after_second} == {i["id"] for i in after_first}


def test_idempotency_survives_a_fresh_process(client, engine):
    """
    The check must be a database lookup, not the in-memory dedupe cache in
    workflows.py — that cache neither survives a restart nor outlives its window.
    """
    client.post(EVALUATE_URL)

    from app.gpa_trends import evaluate_gpa_trends
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=engine)()
    try:
        summary = evaluate_gpa_trends(session)
    finally:
        session.close()

    assert summary["created"] == 0
    assert summary["skipped_existing"] > 0


# ---------------------------------------------------------------------------
# Cycle 4 — the created item's fields
# ---------------------------------------------------------------------------


def item_row(engine, student_id: str):
    """
    The trend item persisted for a student. Read over SQL because priority,
    workflow_type and title are not part of the GET /api/workflows contract.
    """
    with engine.connect() as conn:
        return conn.execute(
            text("""
                SELECT id, workflow_type, stage, trigger, title, description,
                       status, priority, owner_name, owner_role, created_date
                FROM workflow_items
                WHERE student_id = :sid AND trigger LIKE 'gpa_trend:%'
            """),
            {"sid": student_id},
        ).one()


def test_created_items_use_the_academic_risk_review_type(client, engine):
    client.post(EVALUATE_URL)
    assert item_row(engine, "stu-003").workflow_type == "academic_risk_review"


def test_created_items_are_pending_and_unclaimed(client):
    client.post(EVALUATE_URL)
    for item in trend_items(client):
        assert item["status"] == "pending"
        assert item["owner_role"] == "academic advisor"
        assert item["owner_name"] is None


def test_trigger_names_the_term_that_was_evaluated(client, engine):
    client.post(EVALUATE_URL)
    assert item_row(engine, "stu-003").trigger == "gpa_trend:2024-Fall"


def test_description_states_the_real_gpa_numbers(client, engine):
    client.post(EVALUATE_URL)
    description = item_row(engine, "stu-003").description
    assert "1.90" in description
    assert "1.40" in description
    assert "2024-Fall" in description


def test_title_names_the_student(client, engine):
    client.post(EVALUATE_URL)
    assert "Fahad Al-Ajmi" in item_row(engine, "stu-003").title


# ---------------------------------------------------------------------------
# Cycle 5 — the fixture cast from #63 produces exactly the expected items
# ---------------------------------------------------------------------------


def test_the_fixture_cast_flags_exactly_three_students(client):
    summary = client.post(EVALUATE_URL).json()
    assert summary["flagged"] == 3
    assert summary["created"] == 3


def test_evaluated_covers_the_students_with_history(client, engine):
    with engine.connect() as conn:
        with_history = conn.execute(
            text("""
                SELECT COUNT(*) FROM (
                    SELECT student_id FROM student_term_gpa
                    GROUP BY student_id HAVING COUNT(*) >= 2
                ) s
            """)
        ).scalar_one()
    assert client.post(EVALUATE_URL).json()["evaluated"] == with_history


@pytest.mark.parametrize("student_id,expected_priority", [
    ("stu-003", "urgent"),   # decline through the 2.0 line
    ("stu-015", "high"),     # sharp drop, cumulative still healthy
    ("stu-013", "medium"),   # sustained decline, cumulative still healthy
])
def test_priority_follows_the_severity_tier(client, engine, student_id, expected_priority):
    client.post(EVALUATE_URL)
    assert item_row(engine, student_id).priority == expected_priority


@pytest.mark.parametrize("student_id", [
    "stu-004",  # dip then recovery
    "stu-005",  # steady high
    "stu-019",  # steady but flat around 2.3
])
def test_non_declining_students_get_no_item(client, engine, student_id):
    client.post(EVALUATE_URL)
    with engine.connect() as conn:
        count = conn.execute(
            text("""
                SELECT COUNT(*) FROM workflow_items
                WHERE student_id = :sid AND trigger LIKE 'gpa_trend:%'
            """),
            {"sid": student_id},
        ).scalar_one()
    assert count == 0


def test_created_items_satisfy_the_academic_risk_page_query(client, engine):
    """The Academic Risk page reads workflow items by stage = 'academic_progress'."""
    client.post(EVALUATE_URL)
    with engine.connect() as conn:
        triggers = conn.execute(
            text("""
                SELECT trigger FROM workflow_items
                WHERE stage = 'academic_progress' AND status = 'pending'
            """)
        ).scalars().all()
    assert "gpa_trend:2024-Fall" in triggers


# ---------------------------------------------------------------------------
# Cycle 6 — a term with no recorded GPA yet must not break the sweep
# ---------------------------------------------------------------------------


@pytest.fixture
def student_with_a_null_term_gpa(engine):
    """stu-005's latest term, with its GPA blanked out — term_gpa is nullable."""
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE student_term_gpa SET term_gpa = NULL
            WHERE student_id = 'stu-005' AND term = '2024-Fall'
        """))
        conn.commit()
    yield "stu-005"
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE student_term_gpa SET term_gpa = 3.50
            WHERE student_id = 'stu-005' AND term = '2024-Fall'
        """))
        conn.commit()


def test_a_null_term_gpa_does_not_break_the_evaluation(client, student_with_a_null_term_gpa):
    response = client.post(EVALUATE_URL)
    assert response.status_code == 200
    assert response.json()["flagged"] == 3, "the three declining students still flag"


def test_a_student_with_a_null_term_gpa_is_not_flagged(
    client, engine, student_with_a_null_term_gpa
):
    client.post(EVALUATE_URL)
    with engine.connect() as conn:
        count = conn.execute(
            text("""
                SELECT COUNT(*) FROM workflow_items
                WHERE student_id = :sid AND trigger LIKE 'gpa_trend:%'
            """),
            {"sid": student_with_a_null_term_gpa},
        ).scalar_one()
    assert count == 0
