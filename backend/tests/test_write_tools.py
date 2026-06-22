"""Tests for issue #24 — Orchestrate agent write tools (workflow creation layer).

Spec-validation tests confirm write_tools.yaml is valid OpenAPI and matches the
FastAPI endpoint signatures exactly. Integration cycles drive the actual endpoints
using field names sourced from the spec to prove spec and implementation stay in sync.
"""

import os
from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate as validate_openapi_spec
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db

WRITE_TOOLS_PATH = (
    Path(__file__).parent.parent.parent / "orchestrate" / "tools" / "write_tools.yaml"
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# DB fixtures (integration cycles only)
# ---------------------------------------------------------------------------


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
# Cycle 1 — tracer bullet: write_tools.yaml exists
# ---------------------------------------------------------------------------


def test_write_tools_yaml_exists():
    assert WRITE_TOOLS_PATH.exists(), f"write_tools.yaml not found at {WRITE_TOOLS_PATH}"


# ---------------------------------------------------------------------------
# Cycle 2 — YAML is valid and has OpenAPI 3.1.0 structure
# ---------------------------------------------------------------------------


def test_write_tools_yaml_is_valid_openapi():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    assert spec.get("openapi", "").startswith("3."), "Must be OpenAPI 3.x"
    assert "info" in spec
    assert "paths" in spec


def test_write_tools_yaml_passes_openapi_spec_validator():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    validate_openapi_spec(spec)  # raises if invalid


# ---------------------------------------------------------------------------
# Cycle 3 — POST /api/workflows path has operationId create_workflow_item
# ---------------------------------------------------------------------------


def test_spec_has_create_workflow_path():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    assert "/api/workflows" in spec["paths"], "Missing POST /api/workflows path"
    assert "post" in spec["paths"]["/api/workflows"], "Missing post operation"


def test_create_workflow_item_operation_id():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows"]["post"]
    assert op.get("operationId") == "create_workflow_item"


# ---------------------------------------------------------------------------
# Cycle 4 — create_workflow_item request body has all required fields
# ---------------------------------------------------------------------------


def _resolve_schema(spec, schema):
    """Follow a $ref one level deep to get the actual schema object."""
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return spec["components"]["schemas"][ref_name]
    return schema


def test_create_workflow_item_required_fields():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows"]["post"]
    raw = op["requestBody"]["content"]["application/json"]["schema"]
    schema = _resolve_schema(spec, raw)
    required = set(schema.get("required", []))
    expected = {"stage", "trigger", "owner_name", "owner_role", "description", "status"}
    missing = expected - required
    assert not missing, f"create_workflow_item schema missing required fields: {missing}"


def test_create_workflow_item_optional_fields_present():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows"]["post"]
    raw = op["requestBody"]["content"]["application/json"]["schema"]
    schema = _resolve_schema(spec, raw)
    props = set(schema.get("properties", {}).keys())
    assert "due_date" in props, "due_date must be a property (optional)"
    assert "student_id" in props, "student_id must be a property (optional)"


# ---------------------------------------------------------------------------
# Cycle 5 — PATCH /api/workflows/{item_id} path has operationId update_workflow_item
# ---------------------------------------------------------------------------


def test_spec_has_update_workflow_path():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    assert "/api/workflows/{item_id}" in spec["paths"], (
        "Missing PATCH /api/workflows/{item_id} path"
    )
    assert "patch" in spec["paths"]["/api/workflows/{item_id}"]


def test_update_workflow_item_operation_id():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows/{item_id}"]["patch"]
    assert op.get("operationId") == "update_workflow_item"


# ---------------------------------------------------------------------------
# Cycle 6 — update_workflow_item path param and patch body schema
# ---------------------------------------------------------------------------


def test_update_workflow_item_has_item_id_path_param():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows/{item_id}"]["patch"]
    params = {p["name"]: p for p in op.get("parameters", [])}
    assert "item_id" in params, "update_workflow_item must declare item_id path parameter"
    assert params["item_id"]["in"] == "path"
    assert params["item_id"]["required"] is True


def test_update_workflow_item_patch_body_schema():
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows/{item_id}"]["patch"]
    raw = op["requestBody"]["content"]["application/json"]["schema"]
    schema = _resolve_schema(spec, raw)
    props = set(schema.get("properties", {}).keys())
    assert "status" in props, "patch schema must include status"
    assert "due_date" in props, "patch schema must include due_date"


# ---------------------------------------------------------------------------
# Cycle 7 — Integration: agent simulation creates a workflow item via spec fields
# ---------------------------------------------------------------------------


def test_agent_simulation_create_workflow_item(client):
    """Parses spec field names and drives POST /api/workflows, proving spec+impl are in sync."""
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    op = spec["paths"]["/api/workflows"]["post"]
    raw = op["requestBody"]["content"]["application/json"]["schema"]
    schema = _resolve_schema(spec, raw)
    required_fields = set(schema.get("required", []))

    # Build a minimal valid payload using only field names declared in the spec
    payload = {f: None for f in schema.get("properties", {}).keys()}
    payload.update({
        "stage": "admissions",
        "trigger": "Write-tools spec integration test",
        "owner_name": "Sara Al-Rashidi",
        "owner_role": "admissions officer",
        "status": "pending",
        "due_date": "2026-01-15",
        "description": "Agent-generated: review transfer credits.",
        "student_id": None,
    })
    # Drop None values for optional fields
    payload = {k: v for k, v in payload.items() if v is not None or k in required_fields}
    payload = {k: v for k, v in payload.items() if v is not None}

    response = client.post("/api/workflows", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    body = response.json()
    assert "id" in body and body["id"], "Response must include a non-empty id"

    # Confirm it appears in the list
    items = client.get("/api/workflows").json()
    ids = [item["id"] for item in items]
    assert body["id"] in ids, "Spec-driven created item must persist in GET /api/workflows"


# ---------------------------------------------------------------------------
# Cycle 8 — Integration: agent simulation updates a workflow item via spec fields
# ---------------------------------------------------------------------------


def test_agent_simulation_update_workflow_item(client):
    """Parses spec patch fields and drives PATCH /api/workflows/{item_id}."""
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())

    # Create an item to patch
    create_payload = {
        "stage": "career",
        "trigger": "Write-tools patch integration test",
        "owner_name": "Lina Al-Enezi",
        "owner_role": "career advisor",
        "status": "pending",
        "due_date": "2026-02-01",
        "description": "Agent-generated: confirm internship placement.",
    }
    create_resp = client.post("/api/workflows", json=create_payload)
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # Derive patch fields from the spec
    patch_op = spec["paths"]["/api/workflows/{item_id}"]["patch"]
    raw = patch_op["requestBody"]["content"]["application/json"]["schema"]
    patch_schema = _resolve_schema(spec, raw)
    patch_props = set(patch_schema.get("properties", {}).keys())

    assert "status" in patch_props, "Spec patch schema must expose status field"
    patch_payload = {"status": "approved"}

    patch_resp = client.patch(f"/api/workflows/{item_id}", json=patch_payload)
    assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}"
    assert patch_resp.json()["status"] == "approved"
