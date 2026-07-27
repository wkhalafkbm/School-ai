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
    assert data["at_risk_detected_early"] == 3  # the three declining series, not the low-GPA snapshot
    assert data["registration_issues_resolved"] == 0
    assert data["graduation_delays_prevented"] == 1
    assert data["faculty_overload_alerts"] == 1  # fac-001 is 15 credits against a 12-credit cap


# ── /api/overview/journey-health ──────────────────────────────────────────────

def test_journey_health_returns_200(client):
    response = client.get("/api/overview/journey-health")
    assert response.status_code == 200


def test_journey_health_has_all_five_stages(client):
    from app.stages import JOURNEY_HEALTH_STAGES

    data = client.get("/api/overview/journey-health").json()
    assert set(data.keys()) == {stage.value for stage in JOURNEY_HEALTH_STAGES}


def test_journey_health_values_are_valid_status_codes(client):
    from app.status import StatusCode
    valid = {s.value for s in StatusCode}
    data = client.get("/api/overview/journey-health").json()
    for stage, status in data.items():
        assert status in valid, f"stage {stage!r} has invalid status {status!r}"


def test_journey_health_admissions_reflects_incomplete_onboarding_tasks(client):
    # 4/12 tasks incomplete → ~33% → watch
    data = client.get("/api/overview/journey-health").json()
    assert data["admissions"] in ("watch", "needs_attention", "urgent")


def test_journey_health_progression_reflects_on_track_ratio(client):
    # 2/5 not on_track → 40% → above 30% threshold → urgent
    data = client.get("/api/overview/journey-health").json()
    assert data["progression"] == "urgent"


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


def test_priority_queue_rows_carry_canonical_stages(client):
    """Every row routes off its stage — an off-vocabulary value strands it (#68)."""
    from app.stages import STAGES

    data = client.get("/api/overview/priority-queue").json()
    off_vocabulary = sorted({i["stage"] for i in data if i["stage"] not in STAGES})
    assert not off_vocabulary, f"priority queue emits unknown stages: {off_vocabulary}"


def test_priority_queue_capped_at_20(client):
    data = client.get("/api/overview/priority-queue").json()
    assert len(data) <= 20


def test_priority_queue_ordered_by_severity_descending(client):
    from app.status import StatusCode, status_meta
    data = client.get("/api/overview/priority-queue").json()
    ranks = [status_meta[StatusCode(item["status"])]["severity_rank"] for item in data]
    assert ranks == sorted(ranks, reverse=True)


# ── GPA-trend flags in the priority queue (issue #66) ─────────────────────────

# The fixture cast from #63. Tiers are the trend rule composed with the absolute
# GPA thresholds, and are asserted here rather than recomputed — the same tiers
# test_gpa_trend_evaluation pins on the workflow items the sweep creates.
FLAGGED_BY_TREND = {
    "stu-003": "urgent",           # decline through the 2.0 line
    "stu-015": "needs_attention",  # sharp drop, cumulative still healthy
    "stu-013": "watch",            # sustained decline, cumulative still healthy
}

NOT_FLAGGED_BY_TREND = [
    "stu-004",  # dip then recovery
    "stu-005",  # steady high
    "stu-019",  # steady but flat around 2.3
]


def queue_by_student(client) -> dict:
    return {
        item["student_id"]: item
        for item in client.get("/api/overview/priority-queue").json()
    }


@pytest.mark.parametrize("student_id", list(FLAGGED_BY_TREND))
def test_trend_flagged_students_reach_the_queue(client, student_id):
    assert student_id in queue_by_student(client)


# The GPA figures each student's own decline turns on, read off the #63 fixture
# series rather than recomputed — a reason quoting any other numbers is wrong
# even if the tier beside it happens to be right.
TREND_REASON_NUMBERS = {
    "stu-003": "1.90 → 1.40 in 2024-Fall",
    "stu-015": "3.00 → 2.40 in 2024-Fall",
    "stu-013": "2.90 → 2.65 → 2.40",
}


@pytest.mark.parametrize("student_id,numbers", list(TREND_REASON_NUMBERS.items()))
def test_trend_rows_quote_the_students_real_gpa_figures(client, student_id, numbers):
    assert numbers in queue_by_student(client)[student_id]["reason"]


@pytest.mark.parametrize("student_id,expected", list(FLAGGED_BY_TREND.items()))
def test_trend_rows_carry_the_tier_the_rule_assigned(client, student_id, expected):
    assert queue_by_student(client)[student_id]["status"] == expected


@pytest.mark.parametrize("student_id", NOT_FLAGGED_BY_TREND)
def test_students_whose_trajectory_never_fires_get_no_trend_row(client, student_id):
    """
    A steady or recovering student may still be queued by another source — what
    must not happen is the queue claiming their GPA is declining.
    """
    row = queue_by_student(client).get(student_id)
    assert row is None or "GPA declined" not in row["reason"]


def test_a_trend_row_outranks_a_lower_severity_row_from_another_source(client):
    """Severity ordering holds across sources, not just within one."""
    queue = [item["student_id"] for item in client.get("/api/overview/priority-queue").json()]
    trend_needs_attention = queue.index("stu-015")
    onboarding_watch = queue.index("stu-002")
    assert trend_needs_attention < onboarding_watch


def test_the_queue_still_shows_each_student_once(client):
    """The new source must widen the queue, not double-list anyone already in it."""
    queue = client.get("/api/overview/priority-queue").json()
    student_ids = [item["student_id"] for item in queue]
    assert len(student_ids) == len(set(student_ids))


def test_trend_rows_are_stamped_with_the_academic_risk_stage(client):
    """The stage the frontend routes on — an unknown value would strand the row."""
    for student_id in FLAGGED_BY_TREND:
        assert queue_by_student(client)[student_id]["stage"] == "academic_risk"


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


# ── at_risk_detected_early — the trend rule's population (#69) ────────────────

def test_at_risk_detected_early_counts_the_students_the_trend_rule_flags(client):
    """
    The KPI is "who is sliding", not "who is currently low". Three fixture series
    decline: stu-003, stu-013 and stu-015 — the same three FLAGGED_BY_TREND pins
    for the queue, because both read the one rule.

    stu-099 is the student the old snapshot definition counted: a 2.40 GPA held
    flat across three terms. Nothing about them was ever detected *early*, and
    they are correctly absent now.
    """
    assert client.get("/api/overview/metrics").json()["at_risk_detected_early"] == 3


def test_at_risk_detected_early_rows_carry_the_tier_and_the_rules_own_reason(client):
    """
    Severity first, then name — and the reason quotes the student's real figures
    off the #63 fixture series. A row explaining the decline in placeholder terms
    would leave an advisor with a number and no next action.
    """
    data = client.get("/api/overview/metrics/at_risk_detected_early/detail").json()

    assert data["rows"] == [
        {
            "id": "stu-003",
            "name": "Fahad Al-Ajmi",
            "context": "Computer Science",
            "status": "urgent",
            "detail": (
                "GPA declined 1.90 → 1.40 in 2024-Fall (sharp drop); "
                "GPA declined 2.40 → 1.90 → 1.40 across 2023-Fall–2024-Fall, "
                "a total of 1.00 over two terms (sustained decline)"
            ),
        },
        {
            "id": "stu-015",
            "name": "Hamad Al-Dashti",
            "context": "Business Administration",
            "status": "needs_attention",
            "detail": "GPA declined 3.00 → 2.40 in 2024-Fall (sharp drop)",
        },
        {
            "id": "stu-013",
            "name": "Turki Al-Azemi",
            "context": "Information Systems",
            "status": "watch",
            "detail": (
                "GPA declined 2.90 → 2.65 → 2.40 across 2023-Fall–2024-Fall, "
                "a total of 0.50 over two terms (sustained decline)"
            ),
        },
    ]


def test_at_risk_detected_early_explains_itself_in_trend_terms(client):
    """
    The panel's prose is the only place a reader learns what the headline number
    means. Leaving the old snapshot wording there would have the card counting
    one population and the panel describing another.
    """
    data = client.get("/api/overview/metrics/at_risk_detected_early/detail").json()

    definition = data["definition"].lower()
    assert "trend" in definition or "declin" in definition
    # The snapshot definition's two tells, both retired by #69.
    assert "2.5" not in data["definition"]
    assert "support case" not in definition

    assert data["empty_message"] == "No student shows a downward GPA trend right now."


def test_the_kpi_never_diverges_from_the_pure_rule(client):
    """
    #69's divergence guard, and the reason the count is not a second statement of
    the rule in SQL.

    The card's number arrives through the whole chain — fixture, seed, the term
    series query, the counter. This recomputes the population from the #63
    fixture file with the pure rule and nothing else. A break anywhere in that
    chain, or any future attempt to restate the rule somewhere along it, lands
    here as a disagreement rather than as a quietly wrong headline number.
    """
    import json

    from app.rules import check_gpa_trend

    series_by_student: dict[str, list[dict]] = {}
    for row in json.loads((FIXTURES_DIR / "student_term_gpa.json").read_text()):
        series_by_student.setdefault(row["student_id"], []).append(row)

    flagged_by_rule = set()
    for student_id, series in series_by_student.items():
        series.sort(key=lambda row: row["term_index"])
        # The same two students the rule declines to judge: an unrecorded term
        # makes a term-over-term delta a lie, and one term is not a trend.
        if any(r["term_gpa"] is None or r["cumulative_gpa"] is None for r in series):
            continue
        if len(series) < 2:
            continue
        if check_gpa_trend(series).flagged:
            flagged_by_rule.add(student_id)

    # Pinned so a fixture edit that empties the population fails loudly here
    # rather than making the comparison below trivially true at zero.
    assert flagged_by_rule == {"stu-003", "stu-013", "stu-015"}

    metrics = client.get("/api/overview/metrics").json()
    detail = client.get("/api/overview/metrics/at_risk_detected_early/detail").json()
    assert metrics["at_risk_detected_early"] == len(flagged_by_rule)
    assert detail["total"] == len(flagged_by_rule)


@pytest.fixture
def nobody_is_declining(engine):
    """
    A population with no downward trend in it — the three declining students lose
    their term history, and they are the only three the rule flags.

    Restored from the #63 fixture file afterwards so the rest of the module still
    sees the seeded population.
    """
    import json

    from sqlalchemy import text

    ids = ["stu-003", "stu-013", "stu-015"]

    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM student_term_gpa WHERE student_id = ANY(:ids)"),
            {"ids": ids},
        )
        conn.commit()

    yield

    restored = [
        row
        for row in json.loads((FIXTURES_DIR / "student_term_gpa.json").read_text())
        if row["student_id"] in ids
    ]
    with engine.connect() as conn:
        for row in restored:
            conn.execute(
                text("""
                    INSERT INTO student_term_gpa
                        (id, student_id, term, term_index, term_gpa,
                         cumulative_gpa, data_source)
                    VALUES
                        (:id, :student_id, :term, :term_index, :term_gpa,
                         :cumulative_gpa, CAST(:data_source AS datasource))
                """),
                row,
            )
        conn.commit()


def test_at_risk_detected_early_still_explains_itself_with_nothing_to_show(
    client, nobody_is_declining
):
    """
    Zero is a real answer for this metric, not a failure to load. The card still
    expands, and what it opens onto says why it is empty in the metric's own
    terms — a generic "no data" would read as a broken panel.
    """
    response = client.get("/api/overview/metrics/at_risk_detected_early/detail")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert data["rows"] == []
    assert data["empty_message"] == "No student shows a downward GPA trend right now."
    assert data["definition"].strip()
    assert data["destination"] == EXPECTED_DESTINATIONS["at_risk_detected_early"]

    assert client.get("/api/overview/metrics").json()["at_risk_detected_early"] == 0


@pytest.fixture
def five_extra_declining_students(engine):
    """
    Five more students in a sharp single-term drop, pushing the flagged
    population past the six-row cap. Named to sort last, so what the cap drops is
    decided by severity rather than by the alphabet.
    """
    from sqlalchemy import text

    ids = [f"stu-trend-cap-{i}" for i in range(5)]

    with engine.connect() as conn:
        for i, sid in enumerate(ids):
            conn.execute(
                text("""
                    INSERT INTO students (id, name, program_id, status, data_source)
                    VALUES (:id, :name, 'prog-001', 'enrolled', 'SIS')
                """),
                {"id": sid, "name": f"Zzz Trendfiller {i}"},
            )
            # 3.50 → 2.90 is a 0.60 sharp drop with a healthy cumulative, so the
            # rule lands every one of them on needs_attention.
            for index, (term, term_gpa, cumulative) in enumerate(
                [("2024-Spring", 3.5, 3.5), ("2024-Fall", 2.9, 3.2)], start=1
            ):
                conn.execute(
                    text("""
                        INSERT INTO student_term_gpa
                            (id, student_id, term, term_index, term_gpa,
                             cumulative_gpa, data_source)
                        VALUES (:id, :sid, :term, :idx, :gpa, :cum, 'SIS')
                    """),
                    {
                        "id": f"stg-cap-{i}-{index}",
                        "sid": sid,
                        "term": term,
                        "idx": index,
                        "gpa": term_gpa,
                        "cum": cumulative,
                    },
                )
        conn.commit()

    yield

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM student_term_gpa WHERE id LIKE 'stg-cap-%'"))
        conn.execute(text("DELETE FROM students WHERE id LIKE 'stu-trend-cap-%'"))
        conn.commit()


def test_at_risk_detected_early_caps_at_six_worst_first_while_the_total_counts_all(
    client, five_extra_declining_students
):
    """
    The cap is a display limit, not a change to the number. Severity decides who
    survives it: the 'watch' student falls off the end while every more urgent
    row stays, so the panel never truncates the worst case out of view.
    """
    data = client.get("/api/overview/metrics/at_risk_detected_early/detail").json()

    assert data["total"] == 8  # 3 seeded + 5 added
    assert len(data["rows"]) == 6
    assert client.get("/api/overview/metrics").json()["at_risk_detected_early"] == 8

    assert [row["name"] for row in data["rows"]] == [
        "Fahad Al-Ajmi",       # urgent
        "Hamad Al-Dashti",     # needs_attention, and H sorts before Z
        "Zzz Trendfiller 0",
        "Zzz Trendfiller 1",
        "Zzz Trendfiller 2",
        "Zzz Trendfiller 3",
    ]
    # Turki Al-Azemi is the 'watch' row, and the only tier the cap was allowed to drop.
    assert "Turki Al-Azemi" not in {row["name"] for row in data["rows"]}


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
