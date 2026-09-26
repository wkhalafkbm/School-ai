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
    "student_slo_results", "student_term_gpa", "academic_plan_courses",
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
# Issue #85 — a catalog entry is term-agnostic; its offerings carry the term
#
# The same course can run in more than one term. Repeating it in the catalog to
# say so would split it into two ids and break the prerequisite graph, so the
# term lives on the offering and the catalog entry stays term-free.
# ---------------------------------------------------------------------------

PLANNED_TERM = "2025-Spring"


def offerings_by_course():
    """schedule_sections grouped by the course they offer."""
    grouped: dict[str, list[dict]] = {}
    for section in load("schedule_sections"):
        grouped.setdefault(section["course_id"], []).append(section)
    return grouped


def test_one_catalog_entry_per_course_code():
    codes = [c["code"] for c in load("courses")]
    duplicates = {code for code in codes if codes.count(code) > 1}
    assert not duplicates, (
        f"{sorted(duplicates)} appear more than once in the catalog — a course "
        f"offered in a second term must reuse its entry, not gain a new id, or "
        f"the prerequisite graph splits in two"
    )


def test_a_course_offered_in_two_terms_keeps_one_catalog_entry():
    offerings = offerings_by_course()
    courses = {c["id"]: c for c in load("courses")}

    reoffered = {
        course_id: sections
        for course_id, sections in offerings.items()
        if len({s["semester"] for s in sections}) > 1
    }
    assert reoffered, (
        "no course is offered in more than one term, so nothing proves the "
        "catalog can carry a course across terms without duplicating it"
    )
    for course_id, sections in reoffered.items():
        assert course_id in courses, f"{course_id} has offerings but no catalog entry"
        assert len({s["section_code"] for s in sections}) == len(sections), (
            f"{courses[course_id]['code']} has offerings sharing a section code"
        )


def test_catalog_entries_added_for_the_planned_term_carry_no_term():
    """The courses the recovery plan introduced exist only as future offerings,
    so nothing about them should name a term but the offering itself."""
    offerings = offerings_by_course()
    courses = {c["id"]: c for c in load("courses")}

    new_entries = [
        courses[course_id]
        for course_id, sections in offerings.items()
        if {s["semester"] for s in sections} == {PLANNED_TERM}
    ]
    assert new_entries, f"no course is offered only in {PLANNED_TERM}"
    for course in new_entries:
        assert course["semester"] is None, (
            f"{course['code']} carries semester {course['semester']!r}; the term "
            f"a course runs in belongs to its offering, not its catalog entry"
        )


def test_every_planned_class_is_seated_in_an_offering_of_its_own_term():
    sections = {s["id"]: s for s in load("schedule_sections")}
    courses = {c["id"]: c for c in load("courses")}

    plan = load("academic_plan_courses")
    assert plan, "academic_plan_courses.json holds no planned classes"
    for i, row in enumerate(plan):
        section = sections[row["section_id"]]
        assert section["semester"] == row["term"], (
            f"academic_plan_courses[{i}] plans {courses[row['course_id']]['code']} "
            f"in {row['term']} but section {section['id']} runs in "
            f"{section['semester']}"
        )
        assert section["course_id"] == row["course_id"], (
            f"academic_plan_courses[{i}] names course {row['course_id']} but "
            f"section {section['id']} offers {section['course_id']}"
        )


def test_planned_term_classes_never_meet_at_the_same_time():
    """A plan the student could not actually attend is not a plan."""
    sections = {s["id"]: s for s in load("schedule_sections")}
    by_day: dict[str, list[dict]] = {}
    for row in load("academic_plan_courses"):
        section = sections[row["section_id"]]
        for day in section["days"]:
            by_day.setdefault((row["student_id"], row["term"], day), []).append(section)

    for (student_id, term, day), meetings in by_day.items():
        ordered = sorted(meetings, key=lambda s: s["start_time"])
        for earlier, later in zip(ordered, ordered[1:]):
            assert earlier["end_time"] <= later["start_time"], (
                f"{student_id}'s {term} plan double-books {day}: "
                f"{earlier['section_code']} ({earlier['start_time']}–"
                f"{earlier['end_time']}) overlaps {later['section_code']} "
                f"({later['start_time']}–{later['end_time']})"
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


# ---------------------------------------------------------------------------
# Issue #98 — the marking variance the demo turns on: two sections of one
# Computer Science course assess the same SLO in the same semester and report
# proficiency rates roughly 37 points apart.
# ---------------------------------------------------------------------------

def test_two_sections_of_one_cs_course_assess_the_same_slo_far_apart():
    courses = {c["id"]: c for c in load("courses")}
    sections = {s["id"]: s for s in load("schedule_sections")}
    cs_program_ids = {
        p["id"] for p in load("programs") if p["name"] == "Computer Science"
    }

    section_level = [a for a in load("slo_assessments") if a.get("section_id")]
    assert section_level, "no section-level SLO assessment rows"

    by_slo_semester: dict[tuple[str, str], list[dict]] = {}
    for row in section_level:
        by_slo_semester.setdefault((row["slo_id"], row["semester"]), []).append(row)

    pairs = [rows for rows in by_slo_semester.values() if len(rows) == 2]
    assert pairs, "no SLO is assessed by two sections in the same semester"

    variance_pairs = []
    for high, low in (sorted(rows, key=lambda r: -r["proficiency_rate"]) for rows in pairs):
        course = courses[high["course_id"]]
        assert course["program_id"] in cs_program_ids, (
            f"{course['code']} is not a Computer Science course"
        )
        assert low["course_id"] == high["course_id"]
        high_section, low_section = sections[high["section_id"]], sections[low["section_id"]]
        assert high_section["course_id"] == course["id"]
        assert low_section["course_id"] == course["id"]
        assert high_section["semester"] == high["semester"]
        assert low_section["semester"] == low["semester"]
        assert high_section["instructor_id"] != low_section["instructor_id"], (
            "both sections are taught by the same instructor"
        )
        if abs(high["proficiency_rate"] - 0.91) <= 0.02 and abs(low["proficiency_rate"] - 0.54) <= 0.02:
            variance_pairs.append((high, low))

    assert variance_pairs, (
        "no pair of section-level rows reports roughly 91% and 54% proficient"
    )


# ---------------------------------------------------------------------------
# Issue #97 — the SLO → CLO → PLO attainment chain. Program Learning Outcomes
# for Computer Science live in a config file the backend loads; every Computer
# Science SLO has to feed at least one PLO or the chain has a hole in it.
# ---------------------------------------------------------------------------

def cs_slo_codes() -> set[str]:
    cs_program_ids = {p["id"] for p in load("programs") if p["name"] == "Computer Science"}
    cs_course_ids = {c["id"] for c in load("courses") if c["program_id"] in cs_program_ids}
    return {s["code"] for s in load("slos") if s["course_id"] in cs_course_ids}


def test_computer_science_has_three_or_four_plos_with_a_seventy_percent_target():
    from app.outcomes import load_program_outcomes

    outcomes = load_program_outcomes()

    assert outcomes["program_id"] == "prog-001"
    assert outcomes["program_name"] == "Computer Science"
    assert outcomes["attainment_target"] == 0.70
    assert 3 <= len(outcomes["plos"]) <= 4
    codes = [plo["code"] for plo in outcomes["plos"]]
    assert len(set(codes)) == len(codes), "PLO codes repeat"
    for plo in outcomes["plos"]:
        assert plo["title"], f"{plo['code']} has no title"
        assert plo["slo_codes"], f"{plo['code']} maps no SLOs"


def test_every_computer_science_slo_feeds_at_least_one_plo():
    from app.outcomes import load_program_outcomes

    mapped = {code for plo in load_program_outcomes()["plos"] for code in plo["slo_codes"]}

    assert cs_slo_codes() - mapped == set(), "Computer Science SLOs no PLO claims"
    assert mapped - cs_slo_codes() == set(), "PLOs claim SLOs that are not Computer Science"


def cs_course_ids() -> set[str]:
    cs_program_ids = {p["id"] for p in load("programs") if p["name"] == "Computer Science"}
    return {c["id"] for c in load("courses") if c["program_id"] in cs_program_ids}


def test_computer_science_slo_assessments_span_at_least_three_semesters():
    """Trends are only visible with history: every Computer Science course that
    reports a course-level SLO assessment reports one for three semesters or more."""
    courses = {c["id"]: c["code"] for c in load("courses")}
    course_level = [
        a for a in load("slo_assessments")
        if not a.get("section_id") and a["course_id"] in cs_course_ids()
    ]
    assert course_level, "no course-level SLO assessments for Computer Science"

    semesters_by_course: dict[str, set[str]] = {}
    for row in course_level:
        semesters_by_course.setdefault(row["course_id"], set()).add(row["semester"])
    for course_id, semesters in semesters_by_course.items():
        assert len(semesters) >= 3, (
            f"{courses[course_id]} has SLO assessments for only {sorted(semesters)} (need ≥3 semesters)"
        )
