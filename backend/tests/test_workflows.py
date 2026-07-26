"""Tests for the Workflow Orchestration Gateway (issue #9)."""

import os
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.stages import STAGES

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

OWNER_ROLES = {
    "admissions officer",
    "registrar specialist",
    "department chair",
    "faculty advisor",
    "student affairs officer",
    "academic advisor",
    "career advisor",
}


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
# Cycle 1 — tracer bullet: GET /api/workflows returns 200
# ---------------------------------------------------------------------------

def test_list_workflows_returns_200(client):
    response = client.get("/api/workflows")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — GET /api/workflows returns a list with required fields
# ---------------------------------------------------------------------------

def test_list_workflows_returns_a_list(client):
    data = client.get("/api/workflows").json()
    assert isinstance(data, list)


def test_list_workflows_items_have_required_fields(client):
    data = client.get("/api/workflows").json()
    assert len(data) > 0
    required = {"id", "stage", "trigger", "owner_name", "owner_role", "status", "due_date", "description"}
    for item in data:
        missing = required - item.keys()
        assert not missing, f"Workflow item missing fields: {missing}"


def test_list_workflows_items_have_valid_owner_roles(client):
    data = client.get("/api/workflows").json()
    for item in data:
        assert item["owner_role"] in OWNER_ROLES, (
            f"Invalid owner_role {item['owner_role']!r} for item {item['id']}"
        )


def test_list_workflows_seeded_items_present(client):
    data = client.get("/api/workflows").json()
    assert len(data) >= 3, "Expected at least 3 seeded workflow items"


# ---------------------------------------------------------------------------
# Cycle 3 — POST /api/workflows creates a new item (agent tool call path)
# ---------------------------------------------------------------------------

def test_create_workflow_item_returns_201(client):
    payload = {
        "stage": "admissions",
        "trigger": "Orchestrate agent recommendation",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "admissions officer",
        "status": "pending",
        "due_date": "2025-09-15",
        "description": "Review international transfer credits for conditional admission.",
        "student_id": "stu-001",
    }
    response = client.post("/api/workflows", json=payload)
    assert response.status_code == 201


def test_create_workflow_item_response_has_id(client):
    payload = {
        "stage": "enrollment",
        "trigger": "Hold placed by finance office",
        "owner_name": "Khalid Al-Fadli",
        "owner_role": "registrar specialist",
        "status": "pending",
        "due_date": "2025-09-10",
        "description": "Resolve financial hold before registration deadline.",
        "student_id": "stu-002",
    }
    response = client.post("/api/workflows", json=payload)
    body = response.json()
    assert "id" in body
    assert body["id"]  # non-empty


def test_created_item_appears_in_list(client):
    payload = {
        "stage": "academic_risk",
        "trigger": "LMS risk flag raised",
        "owner_name": "Noura Al-Hamdan",
        "owner_role": "academic advisor",
        "status": "in_review",
        "due_date": "2025-10-01",
        "description": "Check in with student — submission rate below 60%.",
        "student_id": "stu-003",
    }
    response = client.post("/api/workflows", json=payload)
    assert response.status_code == 201
    created_id = response.json()["id"]

    items = client.get("/api/workflows").json()
    ids = [item["id"] for item in items]
    assert created_id in ids, "Newly created item must appear in GET /api/workflows"


# ---------------------------------------------------------------------------
# Cycle 4 — PATCH /api/workflows/{id} updates status and due_date
# ---------------------------------------------------------------------------

def test_patch_workflow_updates_status(client):
    payload = {
        "stage": "progression",
        "trigger": "Credits deficit detected",
        "owner_name": "Ahmad Al-Shammari",
        "owner_role": "department chair",
        "status": "pending",
        "due_date": "2025-11-01",
        "description": "Student is 6 credits short of graduation requirement.",
        "student_id": "stu-004",
    }
    item_id = client.post("/api/workflows", json=payload).json()["id"]

    patch_response = client.patch(f"/api/workflows/{item_id}", json={"status": "approved"})
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "approved"


def test_patch_workflow_updates_due_date(client):
    payload = {
        "stage": "career_alumni",
        "trigger": "Internship deadline approaching",
        "owner_name": "Lina Al-Enezi",
        "owner_role": "career advisor",
        "status": "pending",
        "due_date": "2025-12-01",
        "description": "Confirm internship placement before semester close.",
        "student_id": "stu-005",
    }
    item_id = client.post("/api/workflows", json=payload).json()["id"]

    patch_response = client.patch(
        f"/api/workflows/{item_id}", json={"due_date": "2025-12-15"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["due_date"] == "2025-12-15"


def test_patch_nonexistent_workflow_returns_404(client):
    response = client.patch(f"/api/workflows/{uuid.uuid4()}", json={"status": "approved"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cycle 5 — Agent tool call: POST accepts minimal payload without student_id
# ---------------------------------------------------------------------------

def test_create_workflow_without_student_id_is_allowed(client):
    payload = {
        "stage": "admissions",
        "trigger": "Orchestrate agent callback",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "admissions officer",
        "status": "pending",
        "due_date": "2025-09-20",
        "description": "Agent-generated task: review supplemental documents.",
    }
    response = client.post("/api/workflows", json=payload)
    assert response.status_code == 201
    assert "id" in response.json()


# ---------------------------------------------------------------------------
# Cycle 6 — Mock Orchestrate callback: agent tool call persists in PostgreSQL
# ---------------------------------------------------------------------------

def test_orchestrate_agent_callback_persists_item(client):
    """Simulates the Orchestrate agent calling POST /api/workflows as a write tool."""
    agent_payload = {
        "stage": "enrollment",
        "trigger": "Orchestrate agent: hold resolution recommended",
        "owner_name": "Khalid Al-Fadli",
        "owner_role": "registrar specialist",
        "status": "pending",
        "due_date": "2025-09-12",
        "description": "Agent-initiated: resolve administrative hold before add/drop deadline.",
        "student_id": "stu-001",
    }

    create_response = client.post("/api/workflows", json=agent_payload)
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Verify the item persists and is retrievable via the list endpoint
    list_response = client.get("/api/workflows")
    assert list_response.status_code == 200
    ids = [item["id"] for item in list_response.json()]
    assert created_id in ids, "Agent-created item must persist and appear in subsequent GET"

    # Verify all fields round-trip correctly
    match = next(item for item in list_response.json() if item["id"] == created_id)
    assert match["stage"] == "enrollment"
    assert match["trigger"] == "Orchestrate agent: hold resolution recommended"
    assert match["owner_role"] == "registrar specialist"
    assert match["status"] == "pending"


# ---------------------------------------------------------------------------
# Cycle 7 — All 7 required owner roles are present in seeded fixture data
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cycle 8 — Duplicate-suppression at the gateway (issue #53)
# ---------------------------------------------------------------------------

def test_duplicate_create_workflow_item_returns_same_id(client):
    payload = {
        "stage": "career_alumni",
        "trigger": "Mentor match recommendation for Omar Al-Mutairi",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "career advisor",
        "status": "pending",
        "description": (
            "Facilitate mentor introduction between Omar Al-Mutairi and "
            "Eng. Noura Al-Ghanim (FinTech Data Scientist) and schedule initial meeting."
        ),
        "student_id": "stu-005",
    }

    first = client.post("/api/workflows", json=payload)
    second = client.post("/api/workflows", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_duplicate_create_workflow_item_does_not_create_second_row(client):
    payload = {
        "stage": "career_alumni",
        "trigger": "Mentor match recommendation for Layla Al-Sabah",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "career advisor",
        "status": "pending",
        "description": "Facilitate mentor introduction between Layla Al-Sabah and Eng. Huda Al-Otaibi.",
        "student_id": "stu-006",
    }

    client.post("/api/workflows", json=payload)
    client.post("/api/workflows", json=payload)

    items = client.get("/api/workflows").json()
    matches = [item for item in items if item["trigger"] == payload["trigger"]]
    assert len(matches) == 1


def test_workflow_items_differing_by_a_field_are_not_deduped(client):
    base_payload = {
        "stage": "career_alumni",
        "trigger": "Mentor match recommendation for Yousef Al-Harbi",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "career advisor",
        "status": "pending",
        "description": "Facilitate mentor introduction between Yousef Al-Harbi and Eng. Fatima Al-Zahrani.",
        "student_id": "stu-007",
    }
    other_payload = {**base_payload, "student_id": "stu-008"}

    first = client.post("/api/workflows", json=base_payload)
    second = client.post("/api/workflows", json=other_payload)

    assert first.json()["id"] != second.json()["id"]

    items = client.get("/api/workflows").json()
    matches = [item for item in items if item["trigger"] == base_payload["trigger"]]
    assert len(matches) == 2


def test_duplicate_after_dedupe_window_expires_creates_new_item(client, monkeypatch):
    from app.routers import workflows

    monkeypatch.setattr(workflows, "_DEDUPE_WINDOW_SECONDS", 0.05)

    payload = {
        "stage": "career_alumni",
        "trigger": "Mentor match recommendation for Reem Al-Dosari",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "career advisor",
        "status": "pending",
        "description": "Facilitate mentor introduction between Reem Al-Dosari and Eng. Maha Al-Qahtani.",
        "student_id": "stu-009",
    }

    first = client.post("/api/workflows", json=payload)
    time.sleep(0.1)
    second = client.post("/api/workflows", json=payload)

    assert first.json()["id"] != second.json()["id"]


def test_all_seven_owner_roles_present_in_seed(client):
    data = client.get("/api/workflows").json()
    seeded = {item["owner_role"] for item in data if item["id"].startswith("wfl-")}
    required = {
        "admissions officer",
        "registrar specialist",
        "department chair",
        "faculty advisor",
        "student affairs officer",
        "academic advisor",
        "career advisor",
    }
    missing = required - seeded
    assert not missing, f"Seeded fixtures missing owner roles: {missing}"


# ---------------------------------------------------------------------------
# Issue #68 — the stage vocabulary is a contract, not a suggestion. A stage the
# pages do not read is a row nobody ever sees, so the gateway refuses it at the
# door instead of storing it.
# ---------------------------------------------------------------------------

def _valid_payload(**overrides) -> dict:
    return {
        "stage": "academic_risk",
        "trigger": "Vocabulary guard probe",
        "owner_name": "Noura Al-Hamdan",
        "owner_role": "academic advisor",
        "status": "pending",
        "description": "Probe payload for stage/status validation.",
        "student_id": "stu-003",
        **overrides,
    }


@pytest.mark.parametrize("stage", sorted(STAGES))
def test_create_accepts_every_canonical_stage(client, stage):
    response = client.post(
        "/api/workflows",
        json=_valid_payload(stage=stage, trigger=f"Canonical stage probe — {stage}"),
    )
    assert response.status_code == 201, response.text
    assert response.json()["stage"] == stage


def test_create_stamps_the_item_with_todays_date(client, engine):
    """
    Every page that lists items orders them by created_date; a NULL there sorts
    unpredictably and renders as a blank column.
    """
    from datetime import date
    from sqlalchemy import text

    item_id = client.post(
        "/api/workflows", json=_valid_payload(trigger="Created-date probe")
    ).json()["id"]

    with engine.connect() as conn:
        created = conn.execute(
            text("SELECT created_date FROM workflow_items WHERE id = :id"),
            {"id": item_id},
        ).scalar_one()
    assert created == date.today()


@pytest.mark.parametrize("retired_stage", ["academic_progress", "registration", "career"])
def test_create_rejects_a_retired_stage(client, retired_stage):
    response = client.post(
        "/api/workflows",
        json=_valid_payload(
            stage=retired_stage, trigger=f"Retired stage probe — {retired_stage}"
        ),
    )
    assert response.status_code == 422, response.text
    detail = response.text
    assert retired_stage in detail
    assert "academic_risk" in detail, "422 must name the vocabulary the agent may use"


def test_create_rejects_an_unknown_status(client):
    response = client.post(
        "/api/workflows",
        json=_valid_payload(status="complete", trigger="Unknown status probe"),
    )
    assert response.status_code == 422, response.text


def test_patch_rejects_the_retired_complete_status(client):
    item_id = client.post(
        "/api/workflows", json=_valid_payload(trigger="Patch status probe — complete")
    ).json()["id"]

    response = client.patch(f"/api/workflows/{item_id}", json={"status": "complete"})
    assert response.status_code == 422, response.text
    assert "completed" in response.text


def test_patch_accepts_the_terminal_completed_status(client):
    item_id = client.post(
        "/api/workflows", json=_valid_payload(trigger="Patch status probe — completed")
    ).json()["id"]

    response = client.patch(f"/api/workflows/{item_id}", json={"status": "completed"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Cycle — CORS must allow the frontend to POST/PATCH workflow items
# (regression: allow_methods was left as ["GET"] after POST/PATCH endpoints
# were added, so every "create workflow item" button in the frontend failed
# with a browser-side CORS preflight rejection — "Failed to fetch")
# ---------------------------------------------------------------------------

def test_cors_preflight_allows_post_from_frontend_origin(client):
    response = client.options(
        "/api/workflows",
        headers={
            "origin": "http://localhost:3000",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    assert response.status_code == 200
    allowed_methods = {m.strip() for m in response.headers["access-control-allow-methods"].split(",")}
    assert "POST" in allowed_methods


def test_cors_preflight_allows_patch_from_frontend_origin(client):
    response = client.options(
        "/api/workflows/wfl-001",
        headers={
            "origin": "http://localhost:3000",
            "access-control-request-method": "PATCH",
            "access-control-request-headers": "content-type",
        },
    )
    assert response.status_code == 200
    allowed_methods = {m.strip() for m in response.headers["access-control-allow-methods"].split(",")}
    assert "PATCH" in allowed_methods
