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
    # Routing settles the moderation signal at "watch", but the header badge is
    # the more severe of that and the attainment signal (#97): with three of
    # four PLOs below target it stays at needs_attention.
    assert profile["stage_summary"]["health"] == "needs_attention"
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


# ---------------------------------------------------------------------------
# Issue #97 — the SLO → CLO → PLO attainment chain for Computer Science.
#
# Expected values are worked by hand from the fixtures. Each SLO's rate is its
# latest course-level assessment (2024-Fall throughout); a course's roll-up
# (the CLO level) is the mean of the SLOs it contributes to a PLO; a PLO's
# attainment is the mean of its course roll-ups, skipping courses with no
# assessed SLO. Target is 70%.
#
#   PLO1  CS101-SLO1 .733 | CS201-SLO1 .571 | CS301-SLO1 .680 | CS401-SLO1 —      → .661
#   PLO2  CS101 (.600, .833 → .7165) | CS201-SLO2 .500 | CS301-SLO2 —              → .608
#   PLO3  CS201-SLO3 .643 | CS302-SLO1 .410 (cohort history only) | CS401-SLO1 —   → .5265
#   PLO4  CS450-SLO1 .800 | CS301-SLO1 .680                                        → .740
# ---------------------------------------------------------------------------

def attainment(client) -> dict:
    response = client.get(PROFILE_URL)
    assert response.status_code == 200
    return response.json()["program_attainment"]


def plo(client, code: str) -> dict:
    [match] = [p for p in attainment(client)["plos"] if p["code"] == code]
    return match


def test_computer_science_plo_attainment_is_measured_against_a_seventy_percent_target(client):
    program = attainment(client)

    assert program["program_id"] == "prog-001"
    assert program["program_name"] == "Computer Science"
    assert program["attainment_target"] == 0.70
    assert program["latest_semester"] == "2024-Fall"

    by_code = {p["code"]: p for p in program["plos"]}
    assert list(by_code) == ["PLO1", "PLO2", "PLO3", "PLO4"]
    assert by_code["PLO1"]["attainment"] == pytest.approx(0.661, abs=0.0006)
    assert by_code["PLO2"]["attainment"] == pytest.approx(0.608, abs=0.0006)
    assert by_code["PLO3"]["attainment"] == pytest.approx(0.5265, abs=0.0006)
    assert by_code["PLO4"]["attainment"] == pytest.approx(0.740, abs=0.0006)
    assert {code: p["on_target"] for code, p in by_code.items()} == {
        "PLO1": False, "PLO2": False, "PLO3": False, "PLO4": True,
    }
    assert program["plos_below_target"] == 3


def test_a_plo_expands_to_the_courses_feeding_it_and_their_slos(client):
    """PLO1 is fed by four courses; CS101 contributes one SLO whose latest
    assessment is 2024-Fall with three semesters of history behind it."""
    plo1 = plo(client, "PLO1")

    assert plo1["title"] == "Program and build software"
    assert [c["course_code"] for c in plo1["courses"]] == ["CS101", "CS201", "CS301", "CS401"]
    assert plo1["slo_count"] == 4
    assert plo1["assessed_slo_count"] == 3

    [cs101] = [c for c in plo1["courses"] if c["course_code"] == "CS101"]
    assert cs101["course_name"] == "Introduction to Computer Science"
    assert cs101["attainment"] == 0.733
    assert cs101["on_target"] is True
    [slo] = cs101["slos"]
    assert slo["slo_code"] == "CS101-SLO1"
    assert slo["description"].startswith("Students will be able to write basic Python")
    assert slo["proficiency_rate"] == 0.733
    assert slo["on_target"] is True
    assert slo["last_assessed_semester"] == "2024-Fall"
    assert slo["assessed_students"] == 30
    assert slo["history"] == [
        {"semester": "2023-Fall", "proficiency_rate": 0.688},
        {"semester": "2024-Spring", "proficiency_rate": 0.714},
        {"semester": "2024-Fall", "proficiency_rate": 0.733},
    ]


def test_the_course_rollup_is_the_mean_of_the_slos_it_contributes(client):
    """CS101 feeds PLO2 with two SLOs, 60.0% and 83.3%: the CLO level is their
    mean, 71.65%, and that sits on target even though one SLO does not."""
    [cs101] = [c for c in plo(client, "PLO2")["courses"] if c["course_code"] == "CS101"]

    assert [s["slo_code"] for s in cs101["slos"]] == ["CS101-SLO2", "CS101-SLO3"]
    assert [s["on_target"] for s in cs101["slos"]] == [False, True]
    assert cs101["attainment"] == pytest.approx(0.7165, abs=0.0006)
    assert cs101["on_target"] is True


def test_an_unassessed_slo_is_listed_but_carries_no_rate(client):
    """CS401-SLO1 has never been assessed: the chain shows the gap instead of
    inventing a number, and the course is left out of the PLO mean."""
    [cs401] = [c for c in plo(client, "PLO1")["courses"] if c["course_code"] == "CS401"]

    assert cs401["attainment"] is None
    assert cs401["on_target"] is None
    [slo] = cs401["slos"]
    assert slo["slo_code"] == "CS401-SLO1"
    assert slo["proficiency_rate"] is None
    assert slo["last_assessed_semester"] is None
    assert slo["history"] == []


def test_a_semester_only_in_the_cohort_history_still_counts(client):
    """CS302-SLO1 was never written to the assessment table; its 2024-Fall
    cohort history supplies the rate the chain uses."""
    [cs302] = [c for c in plo(client, "PLO3")["courses"] if c["course_code"] == "CS302"]

    [slo] = cs302["slos"]
    assert slo["proficiency_rate"] == 0.41
    assert slo["last_assessed_semester"] == "2024-Fall"
    assert slo["source"] == "cohort_history"
    assert cs302["attainment"] == 0.41
    assert cs302["on_target"] is False


def test_stage_summary_counts_the_plos_below_target(client):
    summary = client.get(PROFILE_URL).json()["stage_summary"]

    assert summary["plo_count"] == 4
    assert summary["plos_below_target"] == 3
    assert summary["attainment_target"] == 0.70
    assert summary["health"] == "needs_attention"


def test_profile_stream_serves_the_attainment_chain_in_the_base_event(client):
    import json

    with client.stream("GET", f"{PROFILE_URL}/stream") as response:
        body = "".join(response.iter_text())

    base = json.loads(body.split("\n\n")[0].split("data: ", 1)[1])
    assert [p["code"] for p in base["program_attainment"]["plos"]] == ["PLO1", "PLO2", "PLO3", "PLO4"]


# ---------------------------------------------------------------------------
# Issue #99 — Agent 10 narrates the diagnosis. The agent does no arithmetic:
# one read tool hands it the program's attainment chain and the variance flags
# the backend already computed.
# ---------------------------------------------------------------------------

OUTCOME_ATTAINMENT_PATH = "/api/programs/{program_id}/outcome-attainment"
PROGRAMS_TOOL_SPEC = Path(__file__).parent.parent.parent / "orchestrate" / "tools" / "read" / "programs_tools.yaml"


def test_outcome_attainment_endpoint_returns_the_chain_and_the_variance_flags(client):
    response = client.get("/api/programs/prog-001/outcome-attainment")
    assert response.status_code == 200
    body = response.json()

    assert body["program_id"] == "prog-001"
    assert body["program_name"] == "Computer Science"
    assert body["attainment_target"] == 0.70
    assert [p["code"] for p in body["plos"]] == ["PLO1", "PLO2", "PLO3", "PLO4"]
    assert body["plos_below_target"] == 3

    [flag] = body["moderation_variance_flags"]
    assert flag["course_code"] == "CS101"
    assert flag["slo_code"] == "CS101-SLO1"
    assert flag["gap_points"] == 37.1
    assert [s["section_code"] for s in flag["sections"]] == ["CS101-01", "CS101-02"]
    # The flag says which PLOs the flagged SLO feeds, so the agent can explain
    # why the SLO matters without walking the chain itself.
    assert flag["feeds_plos"] == ["PLO1"]


def test_outcome_attainment_is_404_for_an_unknown_program(client):
    assert client.get("/api/programs/prog-999/outcome-attainment").status_code == 404


def _spec_operation() -> dict:
    import yaml

    spec = yaml.safe_load(PROGRAMS_TOOL_SPEC.read_text())
    assert OUTCOME_ATTAINMENT_PATH in spec["paths"], (
        f"{OUTCOME_ATTAINMENT_PATH} missing from programs_tools.yaml — the agent "
        "cannot call an endpoint that is not in the tool spec"
    )
    return spec["paths"][OUTCOME_ATTAINMENT_PATH]["get"]


def test_outcome_attainment_tool_spec_matches_the_live_endpoint():
    served = app.openapi()["paths"][OUTCOME_ATTAINMENT_PATH]["get"]
    spec = _spec_operation()
    assert spec["operationId"] == served["operationId"]
    assert spec["operationId"] == "get_outcome_attainment_api_programs__program_id__outcome_attainment_get"
    assert spec["summary"] == served["summary"]
    assert spec["description"] == served["description"]
    assert spec["tags"] == ["programs"]


def test_outcome_attainment_tool_description_tells_the_agent_what_it_gets():
    description = _spec_operation()["description"].lower()
    for word in ("plo", "attainment", "variance", "section", "gap"):
        assert word in description, f"description never mentions {word!r}"


# --- the gateway knows the agent under its own routing key ---

def test_gateway_routes_academic_quality_to_its_own_agent_id_variable(monkeypatch):
    from app.gateway.config import VALID_STAGES, get_agent_id

    assert "academic_quality" in VALID_STAGES
    monkeypatch.setenv("AGENT_ID_ACADEMIC_QUALITY", "agent-academic-quality-001")
    assert get_agent_id("academic_quality") == "agent-academic-quality-001"


# --- the profile's `diagnosis` field: canned in scripted mode ---

import httpx
import respx

import app.gateway.iam as iam_module

WXO_BASE = "https://wxo.example.com"
RUNS_URL = f"{WXO_BASE}/v1/orchestrate/runs"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
AGENT_QUALITY = "agent-academic-quality-001"


@pytest.fixture(autouse=True)
def reset_iam_token():
    iam_module._token = None
    iam_module._expires_at = 0.0
    yield


def test_scripted_mode_serves_the_canned_diagnosis_without_calling_the_agent(client, monkeypatch):
    monkeypatch.setenv("AI_MODE", "scripted")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_QUALITY", AGENT_QUALITY)

    with respx.mock(assert_all_called=False) as router:
        iam = router.post(IAM_URL).mock(return_value=httpx.Response(500))
        diagnosis = client.get(PROFILE_URL).json()["diagnosis"]

    assert not iam.called
    for name in ("CS101", "CS101-SLO1", "CS101-01", "CS101-02", "PLO1"):
        assert name in diagnosis, f"canned diagnosis never names {name}"
    assert "moderat" in diagnosis.lower()


# --- live: the agent narrates; on failure the canned paragraph stands ---

def _completed_run_response(run_id: str, text: str) -> dict:
    return {
        "id": run_id,
        "status": "completed",
        "result": {
            "data": {
                "message": {
                    "role": "assistant",
                    "content": [{"id": "1", "response_type": "text", "text": text}],
                }
            }
        },
    }


@pytest.fixture
def live_mode(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("WXO_BASE_URL", WXO_BASE)
    monkeypatch.setenv("WXO_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_ID_ACADEMIC_QUALITY", AGENT_QUALITY)


def test_live_diagnosis_comes_from_the_agent_and_asks_about_the_flagged_slo(client, live_mode):
    import json

    sent: list[dict] = []

    def capture(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"run_id": "run-quality"})

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(side_effect=capture)
        router.get(f"{RUNS_URL}/run-quality").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-quality", "Live agent: moderate CS101-SLO1 first.")
            )
        )

        diagnosis = client.get(PROFILE_URL).json()["diagnosis"]

    assert diagnosis == "Live agent: moderate CS101-SLO1 first."

    [request] = sent
    assert request["agent_id"] == AGENT_QUALITY
    content = request["message"]["content"]
    # A plain sentence, not JSON, like the cohort agent's payload (#48) — and
    # it hands the agent the ids its tools take and the names the answer must use.
    assert not content.lstrip().startswith("{")
    for name in ("prog-001", "crs-001", "CS101", "CS101-SLO1", "CS101-01", "CS101-02", "2024-Fall"):
        assert name in content, f"agent payload never mentions {name}"


def test_diagnosis_falls_back_to_the_canned_paragraph_when_the_run_fails(client, live_mode):
    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-quality-fail"}))
        router.get(f"{RUNS_URL}/run-quality-fail").mock(
            return_value=httpx.Response(200, json={"id": "run-quality-fail", "status": "failed"})
        )

        diagnosis = client.get(PROFILE_URL).json()["diagnosis"]

    assert diagnosis.startswith("CS101-SLO1 (writing basic Python programs) feeds PLO1")


def test_diagnosis_falls_back_when_orchestrate_is_unreachable(client, live_mode):
    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(side_effect=httpx.ConnectError("no route to IAM"))

        diagnosis = client.get(PROFILE_URL).json()["diagnosis"]

    assert diagnosis.startswith("CS101-SLO1 (writing basic Python programs) feeds PLO1")


def test_stream_shows_the_canned_diagnosis_at_once_and_streams_the_live_one_in(client, live_mode):
    import json

    with respx.mock(assert_all_mocked=True) as router:
        router.post(IAM_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        router.post(RUNS_URL).mock(return_value=httpx.Response(200, json={"run_id": "run-stream"}))
        router.get(f"{RUNS_URL}/run-stream").mock(
            return_value=httpx.Response(
                200, json=_completed_run_response("run-stream", "Live agent: streamed diagnosis.")
            )
        )

        with client.stream("GET", f"{PROFILE_URL}/stream") as response:
            body = "".join(response.iter_text())

    events = [chunk for chunk in body.split("\n\n") if chunk.strip()]
    names = [e.split("\n", 1)[0].removeprefix("event: ") for e in events]
    assert names == ["base", "field", "done"]

    base = json.loads(events[0].split("data: ", 1)[1])
    assert base["diagnosis"].startswith("CS101-SLO1 (writing basic Python programs) feeds PLO1")
    field = json.loads(events[1].split("data: ", 1)[1])
    assert field == {"path": "diagnosis", "value": "Live agent: streamed diagnosis."}
