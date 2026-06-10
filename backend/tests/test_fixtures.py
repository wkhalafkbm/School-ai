import json
import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

FIXTURE_TABLES = [
    "students", "programs", "courses", "faculty", "enrollments",
    "lms_signals", "onboarding_tasks", "prerequisites", "schedule_sections",
    "sponsorship_records", "financial_aid_records", "administrative_holds",
    "support_cases", "interventions", "graduation_requirements",
    "student_course_progress", "career_pathways", "alumni_mentors",
    "workflow_items", "slos", "slo_assessments", "cohort_slo_history",
    "student_slo_results",
]

ZOOM_IN_STUDENTS = [
    "Waleed Khalaf",
    "Mariam Al-Kandari",
    "Fahad Al-Ajmi",
    "Noor Al-Hamad",
    "Omar Al-Mutairi",
]

FEATURED_COURSES = ["CS101", "CS201", "MATH101"]


def load(table: str):
    path = FIXTURES_DIR / f"{table}.json"
    with open(path) as f:
        return json.load(f)


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


def test_every_fixture_record_has_data_source():
    for table in FIXTURE_TABLES:
        for i, record in enumerate(load(table)):
            assert "data_source" in record, (
                f"{table}.json record[{i}] missing data_source"
            )
            assert record["data_source"] in ("SIS", "LMS", "demo"), (
                f"{table}.json record[{i}] has invalid data_source '{record['data_source']}'"
            )
