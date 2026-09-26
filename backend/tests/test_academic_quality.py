"""Tests for the Academic Quality page API — issue #98 (marking variance flag)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

PROFILE_URL = "/api/academic-quality/profile"


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


def flags(client) -> list[dict]:
    response = client.get(PROFILE_URL)
    assert response.status_code == 200
    return response.json()["moderation_variance_flags"]


# ---------------------------------------------------------------------------
# Cycle 1 — tracer bullet: the fixture's two CS101 sections, 91% against 54%
# on the same SLO in the same semester, raise one moderation variance flag
# that names everything the card shows.
# ---------------------------------------------------------------------------

def test_profile_flags_the_cs101_marking_variance(client):
    [flag] = [f for f in flags(client) if f["course_code"] == "CS101"]

    assert flag["course_name"] == "Introduction to Computer Science"
    assert flag["slo_code"] == "CS101-SLO1"
    assert flag["slo_description"].startswith("Students will be able to write basic Python")
    assert flag["semester"] == "2024-Fall"
    assert flag["gap_points"] == 37.1
    assert flag["threshold_points"] == 20

    high, low = flag["sections"]
    assert high["section_code"] == "CS101-01"
    assert high["instructor_name"] == "Dr. Ahmed Al-Rashidi"
    assert high["proficiency_rate"] == 0.913
    assert low["section_code"] == "CS101-02"
    assert low["instructor_name"] == "Dr. Noura Al-Azemi"
    assert low["proficiency_rate"] == 0.542


# ---------------------------------------------------------------------------
# Cycle 2 — the threshold: a 20-point gap fires, a 19-point gap is silent.
# A second CS201 section is planted for the test and removed afterwards.
# ---------------------------------------------------------------------------

@pytest.fixture
def cs201_section_pair(engine):
    """Two 2024-Fall sections of CS201 taught by different instructors; the
    returned callable records their proficiency on CS201-SLO1."""
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO schedule_sections
                (id, course_id, section_code, instructor_id, semester, data_source)
            VALUES ('sec-test-cs201-02', 'crs-002', 'CS201-02', 'fac-005', '2024-Fall', 'demo')
        """))

    def assess(rate_01: float, rate_02: float) -> None:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO slo_assessments
                        (id, slo_id, course_id, section_id, semester, proficiency_rate, data_source)
                    VALUES
                        ('sla-test-01', 'slo-004', 'crs-002', 'sec-002', '2024-Fall', :r1, 'demo'),
                        ('sla-test-02', 'slo-004', 'crs-002', 'sec-test-cs201-02', '2024-Fall', :r2, 'demo')
                """),
                {"r1": rate_01, "r2": rate_02},
            )

    yield assess

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM slo_assessments WHERE id LIKE 'sla-test-%'"))
        conn.execute(text("DELETE FROM schedule_sections WHERE id = 'sec-test-cs201-02'"))


def cs201_flags(client) -> list[dict]:
    return [f for f in flags(client) if f["course_code"] == "CS201"]


def test_a_gap_of_exactly_twenty_points_raises_the_flag(client, cs201_section_pair):
    cs201_section_pair(0.70, 0.50)

    [flag] = cs201_flags(client)
    assert flag["gap_points"] == 20
    assert [s["section_code"] for s in flag["sections"]] == ["CS201-01", "CS201-02"]
    assert flag["sections"][1]["instructor_name"] == "Dr. Yousef Al-Mutawa"


def test_a_gap_of_nineteen_points_stays_silent(client, cs201_section_pair):
    cs201_section_pair(0.70, 0.51)

    assert cs201_flags(client) == []


def test_course_level_rollups_never_raise_a_flag(client):
    """Every pre-#98 assessment row has no section; the roll-up for CS201 sits
    next to nothing it could be compared with."""
    assert cs201_flags(client) == []


# ---------------------------------------------------------------------------
# Cycle 3 — routing for moderation. The page files a workflow item carrying the
# flag's trigger; the profile then reports the item against the flag, and the
# item is what Workflow Activity lists.
# ---------------------------------------------------------------------------

@pytest.fixture
def routed_items_cleanup(engine):
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM workflow_items WHERE stage = 'academic_quality'"))


def test_an_open_flag_is_unrouted_and_needs_attention(client):
    profile = client.get(PROFILE_URL).json()
    [flag] = [f for f in profile["moderation_variance_flags"] if f["course_code"] == "CS101"]

    assert flag["routed_item"] is None
    assert flag["moderation_owner_name"] == "Programme Quality Lead"
    assert profile["stage_summary"]["health"] == "needs_attention"
    assert profile["stage_summary"]["open_flag_count"] == 1


def test_routing_the_flag_files_a_pending_item_the_profile_reports_back(client, routed_items_cleanup):
    [flag] = [f for f in flags(client) if f["course_code"] == "CS101"]

    created = client.post(
        "/api/workflows",
        json={
            "stage": "academic_quality",
            "trigger": flag["trigger"],
            "owner_name": flag["moderation_owner_name"],
            "owner_role": flag["moderation_owner_role"],
            "status": "pending",
            "description": "Moderate CS101-SLO1 marking across CS101-01 and CS101-02",
        },
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    profile = client.get(PROFILE_URL).json()
    [flag_after] = [f for f in profile["moderation_variance_flags"] if f["course_code"] == "CS101"]
    assert flag_after["routed_item"] == {
        "id": item_id,
        "owner_name": "Programme Quality Lead",
        "owner_role": "programme quality lead",
        "status": "pending",
        "created_date": flag_after["routed_item"]["created_date"],
    }
    assert profile["stage_summary"]["health"] == "watch"
    assert profile["stage_summary"]["open_flag_count"] == 0

    listed = [i for i in client.get("/api/workflows").json() if i["id"] == item_id]
    assert listed and listed[0]["stage"] == "academic_quality"


# ---------------------------------------------------------------------------
# Cycle 4 — the stream variant the page consumes: base carries the flags.
# ---------------------------------------------------------------------------

def test_profile_stream_serves_the_flags_in_the_base_event(client):
    import json

    with client.stream("GET", f"{PROFILE_URL}/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    events = [chunk for chunk in body.split("\n\n") if chunk.strip()]
    assert events[0].startswith("event: base\n")
    base = json.loads(events[0].split("data: ", 1)[1])
    assert [f["course_code"] for f in base["moderation_variance_flags"]] == ["CS101"]
    assert events[-1].startswith("event: done\n")
