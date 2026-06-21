"""Tests for the Workflow Orchestration Gateway (issue #9)."""

import os
import uuid
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
        "stage": "registration",
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
        "stage": "academic_progress",
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
        "stage": "graduation_planning",
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
        "stage": "career",
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
        "stage": "registration",
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
    assert match["stage"] == "registration"
    assert match["trigger"] == "Orchestrate agent: hold resolution recommended"
    assert match["owner_role"] == "registrar specialist"
    assert match["status"] == "pending"


# ---------------------------------------------------------------------------
# Cycle 7 — All 7 required owner roles are present in seeded fixture data
# ---------------------------------------------------------------------------

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
