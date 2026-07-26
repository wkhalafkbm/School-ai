import importlib.util
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

FIXTURE_TABLES = [
    "students", "programs", "courses", "faculty", "enrollments",
    "lms_signals", "onboarding_tasks", "prerequisites", "schedule_sections",
    "sponsorship_records", "financial_aid_records", "administrative_holds",
    "support_cases", "interventions", "graduation_requirements",
    "student_course_progress", "career_pathways", "alumni_mentors",
    "workflow_items", "slos", "slo_assessments", "cohort_slo_history",
    "student_slo_results", "student_term_gpa",
]

ZOOM_IN_STUDENTS = [
    "Waleed Khalaf",
    "Mariam Al-Kandari",
    "Fahad Al-Ajmi",
    "Noor Al-Hamad",
    "Omar Al-Mutairi",
]

FEATURED_COURSES = ["CS101", "CS201", "MATH101"]

# The GPA series ends at the term the students.json `gpa` scalar reflects.
# Students admitted in that term have no completed prior terms, so they are the
# one group exempt from the ">= 2 terms" rule.
LATEST_TERM = "2024-Fall"

# Chronological term order — term strings do not sort correctly as text.
TERM_ORDER = [
    "2021-Fall", "2022-Spring", "2022-Fall", "2023-Spring",
    "2023-Fall", "2024-Spring", "2024-Fall",
]


# The six deliberate GPA trajectories, cast from existing students. Each one
# isolates a single downstream trend rule so a detector can be tested against it.
DECLINE_TO_PROBATION = "stu-003"      # Fahad Al-Ajmi — urgent tier
SHARP_DROP = "stu-015"                # single-term drop, GPA still looks fine
SUSTAINED_DECLINE = "stu-013"         # two gentle declines, GPA still looks fine
DIP_THEN_RECOVERY = "stu-004"         # Noor Al-Hamad — must not flag
STEADY_HIGH = "stu-005"               # Omar Al-Mutairi — must not flag
STEADY_FLAT_MID = "stu-019"           # flat near 2.3 — must not flag

MUST_NOT_FLAG = [DIP_THEN_RECOVERY, STEADY_HIGH, STEADY_FLAT_MID]

SHARP_DROP_THRESHOLD = 0.5
SUSTAINED_DECLINE_THRESHOLD = 0.4


def load(table: str):
    path = FIXTURES_DIR / f"{table}.json"
    with open(path) as f:
        return json.load(f)


def term_gpa_by_student():
    """student_term_gpa rows grouped by student, sorted by term_index."""
    grouped: dict[str, list[dict]] = {}
    for row in load("student_term_gpa"):
        grouped.setdefault(row["student_id"], []).append(row)
    return {
        sid: sorted(rows, key=lambda r: r["term_index"])
        for sid, rows in grouped.items()
    }


def test_fixture_files_exist_and_are_valid_json():
    for table in FIXTURE_TABLES:
        path = FIXTURES_DIR / f"{table}.json"
        assert path.exists(), f"Missing fixture: {table}.json"
        data = load(table)
        assert isinstance(data, list), f"{table}.json must be a list"


def test_zoom_in_students_present():
    students = load("students")
    names = {s["name"] for s in students}
    for zoom in ZOOM_IN_STUDENTS:
        assert zoom in names, f"Zoom-in student '{zoom}' missing from students.json"


def test_aggregate_counts_in_range():
    assert 80 <= len(load("students")) <= 150, "students count out of range (80–150)"
    assert 6 <= len(load("programs")) <= 8, "programs count out of range (6–8)"
    assert 20 <= len(load("courses")) <= 30, "courses count out of range (20–30)"
    assert 10 <= len(load("faculty")) <= 15, "faculty count out of range (10–15)"


def test_cohort_slo_history_has_three_semesters_per_featured_course():
    history = load("cohort_slo_history")
    courses = load("courses")
    course_code_to_id = {c["code"]: c["id"] for c in courses}
    for code in FEATURED_COURSES:
        course_id = course_code_to_id.get(code)
        assert course_id, f"Featured course {code} not found in courses.json"
        semesters = {r["semester"] for r in history if r["course_id"] == course_id}
        assert len(semesters) >= 3, (
            f"cohort_slo_history has only {len(semesters)} semester(s) for course {code} (need ≥3)"
        )


def test_student_term_gpa_references_existing_students_only():
    student_ids = {s["id"] for s in load("students")}
    for i, row in enumerate(load("student_term_gpa")):
        assert row["student_id"] in student_ids, (
            f"student_term_gpa[{i}] id={row['id']!r} references unknown "
            f"student {row['student_id']!r}"
        )


def test_every_continuing_enrolled_student_has_at_least_two_terms():
    series = term_gpa_by_student()
    for student in load("students"):
        if student["status"] != "enrolled":
            continue
        rows = series.get(student["id"], [])
        if student["admission_term"] == LATEST_TERM:
            assert len(rows) == 1, (
                f"{student['id']} was admitted in {LATEST_TERM} and has no completed "
                f"prior terms, so it should hold exactly 1 row, not {len(rows)}"
            )
        else:
            assert len(rows) >= 2, (
                f"{student['id']} (admitted {student['admission_term']}) has "
                f"{len(rows)} term(s) of GPA history; needs at least 2"
            )


def test_term_index_orders_each_series_chronologically():
    for student_id, rows in term_gpa_by_student().items():
        indices = [r["term_index"] for r in rows]
        assert indices == list(range(1, len(rows) + 1)), (
            f"{student_id} term_index values are {indices}; "
            f"expected a contiguous 1..{len(rows)} sequence"
        )

        positions = [TERM_ORDER.index(r["term"]) for r in rows]
        assert positions == sorted(positions), (
            f"{student_id} terms {[r['term'] for r in rows]} are not in "
            f"chronological order when sorted by term_index"
        )
        assert rows[-1]["term"] == LATEST_TERM, (
            f"{student_id} series ends at {rows[-1]['term']}, not {LATEST_TERM}"
        )


def test_series_never_starts_before_admission_term():
    admission = {s["id"]: s["admission_term"] for s in load("students")}
    for student_id, rows in term_gpa_by_student().items():
        first = TERM_ORDER.index(rows[0]["term"])
        admitted = TERM_ORDER.index(admission[student_id])
        assert first >= admitted, (
            f"{student_id} has a {rows[0]['term']} row but was only "
            f"admitted in {admission[student_id]}"
        )


def deltas(rows):
    """Term-over-term change in term_gpa, oldest first."""
    gpas = [r["term_gpa"] for r in rows]
    return [round(b - a, 2) for a, b in zip(gpas, gpas[1:])]


def latest_drop(rows):
    """Magnitude of the most recent term-over-term drop (0.0 if it rose)."""
    return max(0.0, -deltas(rows)[-1])


def trailing_decline(rows):
    """Total magnitude of the run of consecutive declines ending the series."""
    total = 0.0
    for delta in reversed(deltas(rows)):
        if delta >= 0:
            break
        total = round(total - delta, 2)
    return total


def series_for(student_id):
    rows = term_gpa_by_student().get(student_id)
    assert rows, f"{student_id} has no student_term_gpa rows"
    return rows


def test_decline_to_probation_trajectory():
    """stu-003 — the demo's urgent case: falls through the 2.0 probation line."""
    rows = series_for(DECLINE_TO_PROBATION)
    gpas = [r["term_gpa"] for r in rows]

    assert all(b < a for a, b in zip(gpas, gpas[1:])), (
        f"{DECLINE_TO_PROBATION} term GPAs {gpas} are not monotonically declining"
    )
    assert gpas[-1] < 2.0, f"latest term GPA {gpas[-1]} is not below 2.0"
    assert rows[-1]["cumulative_gpa"] < 2.0, (
        f"latest cumulative {rows[-1]['cumulative_gpa']} is not below 2.0"
    )


def test_sharp_drop_trajectory_still_looks_fine_on_the_scalar():
    """One big drop in the latest term, while the cumulative GPA stays healthy."""
    rows = series_for(SHARP_DROP)

    assert latest_drop(rows) >= SHARP_DROP_THRESHOLD, (
        f"{SHARP_DROP} latest drop {latest_drop(rows)} is below the "
        f"{SHARP_DROP_THRESHOLD} sharp-drop threshold; deltas={deltas(rows)}"
    )
    assert rows[-1]["cumulative_gpa"] >= 2.5, (
        f"cumulative {rows[-1]['cumulative_gpa']} must stay >= 2.5 so the case "
        f"proves a trend detector catches what a threshold detector misses"
    )


def test_sustained_decline_trajectory_avoids_the_sharp_drop_rule():
    """Two gentle consecutive declines — neither big enough to trip sharp-drop."""
    rows = series_for(SUSTAINED_DECLINE)
    d = deltas(rows)

    assert d[-1] < 0 and d[-2] < 0, (
        f"{SUSTAINED_DECLINE} does not end in two consecutive declines: {d}"
    )
    assert trailing_decline(rows) >= SUSTAINED_DECLINE_THRESHOLD, (
        f"trailing decline {trailing_decline(rows)} is below the "
        f"{SUSTAINED_DECLINE_THRESHOLD} sustained-decline threshold: {d}"
    )
    assert max(-x for x in d if x < 0) < SHARP_DROP_THRESHOLD, (
        f"a single drop reaches the sharp-drop threshold, so this case no longer "
        f"isolates the sustained-decline rule: {d}"
    )
    assert rows[-1]["cumulative_gpa"] >= 2.5, (
        f"cumulative {rows[-1]['cumulative_gpa']} must stay >= 2.5"
    )


def test_dip_then_recovery_has_a_past_dip_but_ends_rising():
    """A past dip must not be punished — the series recovers."""
    rows = series_for(DIP_THEN_RECOVERY)
    d = deltas(rows)

    assert min(d) <= -SHARP_DROP_THRESHOLD + 0.01, (
        f"{DIP_THEN_RECOVERY} has no meaningful past dip to forgive: {d}"
    )
    assert d[-1] > 0, f"series must end on a rise, deltas={d}"


def test_steady_high_trajectory_is_flat_and_strong():
    rows = series_for(STEADY_HIGH)

    assert all(abs(x) <= 0.15 for x in deltas(rows)), (
        f"{STEADY_HIGH} is not steady: deltas={deltas(rows)}"
    )
    assert all(r["term_gpa"] >= 3.2 for r in rows), (
        f"{STEADY_HIGH} is not consistently high: "
        f"{[r['term_gpa'] for r in rows]}"
    )


def test_steady_flat_mid_trajectory_is_low_but_not_trending():
    """Proves the downstream rule is a trend detector, not a threshold detector."""
    rows = series_for(STEADY_FLAT_MID)

    assert all(abs(x) <= 0.15 for x in deltas(rows)), (
        f"{STEADY_FLAT_MID} is not flat: deltas={deltas(rows)}"
    )
    assert 2.2 <= rows[-1]["cumulative_gpa"] <= 2.4, (
        f"cumulative {rows[-1]['cumulative_gpa']} is outside the "
        f"unremarkable-but-low 2.2–2.4 band"
    )


def test_must_not_flag_trajectories_trip_neither_rule():
    for student_id in MUST_NOT_FLAG:
        rows = series_for(student_id)
        assert latest_drop(rows) < SHARP_DROP_THRESHOLD, (
            f"{student_id} trips the sharp-drop rule "
            f"({latest_drop(rows)} >= {SHARP_DROP_THRESHOLD}): {deltas(rows)}"
        )
        assert trailing_decline(rows) < SUSTAINED_DECLINE_THRESHOLD, (
            f"{student_id} trips the sustained-decline rule "
            f"({trailing_decline(rows)} >= {SUSTAINED_DECLINE_THRESHOLD}): "
            f"{deltas(rows)}"
        )


def test_filler_trajectories_trip_neither_rule():
    """Only the deliberate cases may flag; filler must stay quiet."""
    featured = {
        DECLINE_TO_PROBATION, SHARP_DROP, SUSTAINED_DECLINE,
        DIP_THEN_RECOVERY, STEADY_HIGH, STEADY_FLAT_MID,
    }
    for student_id, rows in term_gpa_by_student().items():
        if student_id in featured or len(rows) < 2:
            continue
        assert latest_drop(rows) < SHARP_DROP_THRESHOLD, (
            f"filler student {student_id} trips the sharp-drop rule: {deltas(rows)}"
        )
        assert trailing_decline(rows) < SUSTAINED_DECLINE_THRESHOLD, (
            f"filler student {student_id} trips the sustained-decline rule: "
            f"{deltas(rows)}"
        )


def test_latest_cumulative_gpa_equals_the_students_json_scalar():
    """The series and the snapshot must never disagree."""
    scalars = {s["id"]: s["gpa"] for s in load("students")}
    for student_id, rows in term_gpa_by_student().items():
        assert rows[-1]["cumulative_gpa"] == scalars[student_id], (
            f"{student_id}: latest cumulative_gpa {rows[-1]['cumulative_gpa']} "
            f"disagrees with students.json gpa {scalars[student_id]}"
        )


def running_mean_2dp(values):
    """Mean to 2dp, rounding halves up — exact, so .325 ties can't drift."""
    total = sum(Decimal(str(v)) for v in values)
    return (total / Decimal(len(values))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def test_cumulative_gpa_is_the_running_mean_of_term_gpa():
    for student_id, rows in term_gpa_by_student().items():
        for i, row in enumerate(rows):
            term_gpas = [r["term_gpa"] for r in rows[: i + 1]]
            expected = running_mean_2dp(term_gpas)
            assert Decimal(str(row["cumulative_gpa"])) == expected, (
                f"{student_id} {row['term']}: cumulative_gpa "
                f"{row['cumulative_gpa']} is not the running mean {expected} "
                f"of term GPAs {term_gpas}"
            )


def test_term_gpa_values_are_within_the_gpa_scale():
    for i, row in enumerate(load("student_term_gpa")):
        for field in ("term_gpa", "cumulative_gpa"):
            assert 0.0 <= row[field] <= 4.0, (
                f"student_term_gpa[{i}] {field}={row[field]} is outside 0.0–4.0"
            )


def test_committed_term_gpa_fixture_matches_its_generator():
    """The 275 rows are generated, not hand-maintained — so the committed file
    and the generator must never drift apart."""
    spec = importlib.util.spec_from_file_location(
        "generate_student_term_gpa",
        FIXTURES_DIR / "generate_student_term_gpa.py",
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)

    assert generator.build_rows() == load("student_term_gpa"), (
        "student_term_gpa.json does not match generate_student_term_gpa.py — "
        "regenerate the fixture instead of editing it by hand"
    )


def test_every_fixture_record_has_data_source():
    for table in FIXTURE_TABLES:
        for i, record in enumerate(load(table)):
            assert "data_source" in record, (
                f"{table}.json record[{i}] missing data_source"
            )
            assert record["data_source"] in ("SIS", "LMS", "demo"), (
                f"{table}.json record[{i}] has invalid data_source '{record['data_source']}'"
            )


# ---------------------------------------------------------------------------
# Issue #67 — the scripted fallback tells the same story as the live agent
# ---------------------------------------------------------------------------

RECOMMENDATION_FIXTURES = FIXTURES_DIR / "recommendations"


def test_scripted_engagement_rationale_mentions_the_gpa_trend():
    """When AI_MODE=scripted (or a live run falls back), the engagement stage
    still has to talk about the decline the Trend toggle is displaying."""
    payload = json.loads(
        (RECOMMENDATION_FIXTURES / "academic_risk_engagement.json").read_text()
    )
    result = payload["result"]
    series = term_gpa_by_student()[DECLINE_TO_PROBATION]
    latest, previous = series[-1], series[-2]

    assert "GPA" in result
    assert f"{previous['term_gpa']:.2f}" in result, (
        f"the prior term GPA {previous['term_gpa']:.2f} is missing from the "
        "scripted engagement rationale"
    )
    assert f"{latest['term_gpa']:.2f}" in result
    assert latest["term"] in result


def test_scripted_engagement_fixture_keeps_its_fallback_envelope():
    payload = json.loads(
        (RECOMMENDATION_FIXTURES / "academic_risk_engagement.json").read_text()
    )
    assert payload["stage"] == "academic_risk_engagement"
    assert payload["source"] == "fallback"
