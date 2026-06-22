"""Tests for the Admissions page API (issue #12)."""

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
# Cycle 1 — tracer bullet: GET /api/admissions/profile returns 200
# ---------------------------------------------------------------------------

def test_admissions_profile_returns_200(client):
    response = client.get("/api/admissions/profile")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cycle 2 — stage_summary has health status and applicant counts
# ---------------------------------------------------------------------------

def test_stage_summary_present(client):
    data = client.get("/api/admissions/profile").json()
    assert "stage_summary" in data


def test_stage_summary_has_health_status(client):
    summary = client.get("/api/admissions/profile").json()["stage_summary"]
    assert "health" in summary
    assert summary["health"] in {"on_track", "watch", "needs_attention", "urgent"}


def test_stage_summary_has_applicant_count(client):
    summary = client.get("/api/admissions/profile").json()["stage_summary"]
    assert "applicant_count" in summary
    assert isinstance(summary["applicant_count"], int)
    assert summary["applicant_count"] >= 1


def test_stage_summary_has_pending_review_count(client):
    summary = client.get("/api/admissions/profile").json()["stage_summary"]
    assert "pending_review_count" in summary
    assert isinstance(summary["pending_review_count"], int)


# ---------------------------------------------------------------------------
# Cycle 3 — applicant profile for Waleed Khalaf (stu-001)
# ---------------------------------------------------------------------------

def test_applicant_present(client):
    data = client.get("/api/admissions/profile").json()
    assert "applicant" in data


def test_applicant_is_waleed_khalaf(client):
    applicant = client.get("/api/admissions/profile").json()["applicant"]
    assert applicant["name"] == "Waleed Khalaf"
    assert applicant["id"] == "stu-001"


def test_applicant_has_program_info(client):
    applicant = client.get("/api/admissions/profile").json()["applicant"]
    assert "program_name" in applicant
    assert applicant["program_name"]  # non-empty
    assert "program_interest" in applicant
    assert "admission_term" in applicant
    assert applicant["admission_term"] == "2024-Fall"


def test_applicant_has_sponsorship_and_financial_readiness(client):
    applicant = client.get("/api/admissions/profile").json()["applicant"]
    assert "sponsorship_status" in applicant
    assert applicant["sponsorship_status"]
    assert "financial_readiness" in applicant
    assert applicant["financial_readiness"]


def test_applicant_has_nationality(client):
    applicant = client.get("/api/admissions/profile").json()["applicant"]
    assert applicant.get("nationality") == "Kuwaiti"


# ---------------------------------------------------------------------------
# Cycle 4 — AI recommendation with confidence and rationale
# ---------------------------------------------------------------------------

def test_recommendation_present(client):
    data = client.get("/api/admissions/profile").json()
    assert "recommendation" in data


def test_recommendation_has_confidence(client):
    rec = client.get("/api/admissions/profile").json()["recommendation"]
    assert "confidence" in rec
    assert rec["confidence"] in {"High", "Medium", "Low"}


def test_recommendation_has_rationale(client):
    rec = client.get("/api/admissions/profile").json()["recommendation"]
    assert "rationale" in rec
    assert len(rec["rationale"]) > 20  # substantive text


def test_recommendation_has_action(client):
    rec = client.get("/api/admissions/profile").json()["recommendation"]
    assert "action" in rec
    assert rec["action"]  # non-empty


# ---------------------------------------------------------------------------
# Cycle 5 — evidence with graduate outcomes, signal strength, data completeness
# ---------------------------------------------------------------------------

def test_evidence_present(client):
    data = client.get("/api/admissions/profile").json()
    assert "evidence" in data


def test_evidence_has_graduate_outcomes(client):
    evidence = client.get("/api/admissions/profile").json()["evidence"]
    assert "graduate_outcomes" in evidence
    assert isinstance(evidence["graduate_outcomes"], list)
    assert len(evidence["graduate_outcomes"]) >= 1


def test_graduate_outcome_has_required_fields(client):
    outcomes = client.get("/api/admissions/profile").json()["evidence"]["graduate_outcomes"]
    for outcome in outcomes:
        assert "profile" in outcome
        assert "outcome" in outcome
        assert "cohort_size" in outcome


def test_evidence_has_signal_strength(client):
    evidence = client.get("/api/admissions/profile").json()["evidence"]
    assert "signal_strength" in evidence
    assert evidence["signal_strength"] in {"high", "medium", "low"}


def test_evidence_has_data_completeness(client):
    evidence = client.get("/api/admissions/profile").json()["evidence"]
    assert "data_completeness" in evidence
    assert evidence["data_completeness"] in {"complete", "partial", "minimal"}


# ---------------------------------------------------------------------------
# Cycle 6 — no financial impact estimates in the response
# ---------------------------------------------------------------------------

def test_no_financial_impact_fields(client):
    import json
    raw = json.dumps(client.get("/api/admissions/profile").json())
    forbidden = ["financial_impact", "tuition_revenue", "revenue_impact", "cost_estimate"]
    for field in forbidden:
        assert field not in raw, f"Forbidden financial field found: {field!r}"
