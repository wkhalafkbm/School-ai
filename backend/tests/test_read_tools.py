"""Tests for issue #23 — Orchestrate agent read tools (data access layer).

Each test verifies one endpoint through its public interface.
TDD vertical slices: one test → one implementation → repeat.
"""

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
# Cycle 1 — tracer bullet: GET /api/students/{id} returns student profile
# ---------------------------------------------------------------------------

def test_student_profile_returns_200(client):
    response = client.get("/api/students/stu-001")
    assert response.status_code == 200


def test_student_profile_has_domain_fields(client):
    data = client.get("/api/students/stu-001").json()
    assert data["name"] == "Waleed Khalaf"
    assert data["program"] == "Computer Science"
    assert data["status"] == "applicant"
    assert data["admission_term"] == "2024-Fall"
    assert data["nationality"] == "Kuwaiti"


def test_student_profile_unknown_returns_404(client):
    response = client.get("/api/students/stu-999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cycle 2 — GET /api/students/{id}/academic-history
# ---------------------------------------------------------------------------

def test_academic_history_returns_200(client):
    response = client.get("/api/students/stu-002/academic-history")
    assert response.status_code == 200


def test_academic_history_has_enrollments(client):
    data = client.get("/api/students/stu-002/academic-history").json()
    assert "enrollments" in data
    assert isinstance(data["enrollments"], list)
    assert len(data["enrollments"]) >= 1
    first = data["enrollments"][0]
    assert "course_name" in first
    assert "semester" in first
    assert "status" in first


def test_academic_history_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/academic-history").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 3 — GET /api/students/{id}/sponsorship
# ---------------------------------------------------------------------------

def test_sponsorship_status_returns_200(client):
    response = client.get("/api/students/stu-001/sponsorship")
    assert response.status_code == 200


def test_sponsorship_has_domain_fields(client):
    data = client.get("/api/students/stu-001/sponsorship").json()
    assert "records" in data
    assert isinstance(data["records"], list)
    first = data["records"][0]
    assert "sponsor_name" in first
    assert "status" in first
    assert "coverage_type" in first


def test_sponsorship_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/sponsorship").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 4 — GET /api/students/{id}/onboarding
# ---------------------------------------------------------------------------

def test_onboarding_status_returns_200(client):
    response = client.get("/api/students/stu-002/onboarding")
    assert response.status_code == 200


def test_onboarding_has_tasks(client):
    data = client.get("/api/students/stu-002/onboarding").json()
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    assert len(data["tasks"]) >= 1
    first = data["tasks"][0]
    assert "task_name" in first
    assert "completed" in first
    assert "category" in first


def test_onboarding_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/onboarding").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 5 — GET /api/students/{id}/registrations
# ---------------------------------------------------------------------------

def test_course_registrations_returns_200(client):
    response = client.get("/api/students/stu-002/registrations")
    assert response.status_code == 200


def test_course_registrations_has_courses(client):
    data = client.get("/api/students/stu-002/registrations").json()
    assert "registrations" in data
    assert isinstance(data["registrations"], list)
    assert len(data["registrations"]) >= 1
    first = data["registrations"][0]
    assert "course_name" in first
    assert "semester" in first
    assert "status" in first


def test_course_registrations_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/registrations").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 6 — GET /api/students/{id}/prerequisites
# ---------------------------------------------------------------------------

def test_prerequisite_check_returns_200(client):
    response = client.get("/api/students/stu-002/prerequisites")
    assert response.status_code == 200


def test_prerequisite_check_has_results(client):
    data = client.get("/api/students/stu-002/prerequisites").json()
    assert "prerequisites" in data
    assert isinstance(data["prerequisites"], list)


def test_prerequisite_check_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/prerequisites").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 7 — GET /api/students/{id}/financial-holds
# ---------------------------------------------------------------------------

def test_financial_holds_returns_200(client):
    response = client.get("/api/students/stu-001/financial-holds")
    assert response.status_code == 200


def test_financial_holds_has_records(client):
    data = client.get("/api/students/stu-001/financial-holds").json()
    assert "financial_aid" in data
    assert isinstance(data["financial_aid"], list)


def test_financial_holds_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/financial-holds").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 8 — GET /api/students/{id}/admin-holds
# ---------------------------------------------------------------------------

def test_admin_holds_returns_200(client):
    response = client.get("/api/students/stu-002/admin-holds")
    assert response.status_code == 200


def test_admin_holds_has_holds(client):
    data = client.get("/api/students/stu-002/admin-holds").json()
    assert "holds" in data
    assert isinstance(data["holds"], list)
    assert len(data["holds"]) >= 1
    first = data["holds"][0]
    assert "hold_type" in first
    assert "severity" in first
    assert "blocks_registration" in first


def test_admin_holds_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/admin-holds").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 9 — GET /api/students/{id}/lms-signals
# ---------------------------------------------------------------------------

def test_lms_signals_returns_200(client):
    response = client.get("/api/students/stu-003/lms-signals")
    assert response.status_code == 200


def test_lms_signals_has_signals(client):
    data = client.get("/api/students/stu-003/lms-signals").json()
    assert "signals" in data
    assert isinstance(data["signals"], list)
    assert len(data["signals"]) >= 1
    first = data["signals"][0]
    assert "course_code" in first
    assert "assignment_submission_rate" in first
    assert "risk_flag" in first


def test_lms_signals_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/lms-signals").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 10 — GET /api/students/{id}/attendance (derived from LMS signals)
# ---------------------------------------------------------------------------

def test_attendance_returns_200(client):
    response = client.get("/api/students/stu-003/attendance")
    assert response.status_code == 200


def test_attendance_has_summary(client):
    data = client.get("/api/students/stu-003/attendance").json()
    assert "attendance_summary" in data
    assert isinstance(data["attendance_summary"], list)


def test_attendance_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/attendance").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 11 — GET /api/students/{id}/early-grades
# ---------------------------------------------------------------------------

def test_early_grades_returns_200(client):
    response = client.get("/api/students/stu-003/early-grades")
    assert response.status_code == 200


def test_early_grades_has_results(client):
    data = client.get("/api/students/stu-003/early-grades").json()
    assert "early_grades" in data
    assert isinstance(data["early_grades"], list)


def test_early_grades_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/early-grades").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 12 — GET /api/students/{id}/support-history
# ---------------------------------------------------------------------------

def test_support_history_returns_200(client):
    response = client.get("/api/students/stu-003/support-history")
    assert response.status_code == 200


def test_support_history_has_cases(client):
    data = client.get("/api/students/stu-003/support-history").json()
    assert "cases" in data
    assert isinstance(data["cases"], list)
    assert len(data["cases"]) >= 1
    first = data["cases"][0]
    assert "case_type" in first
    assert "subject" in first
    assert "status" in first


def test_support_history_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/support-history").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 13 — GET /api/students/{id}/risk-summary
# ---------------------------------------------------------------------------

def test_risk_summary_returns_200(client):
    response = client.get("/api/students/stu-003/risk-summary")
    assert response.status_code == 200


def test_risk_summary_has_risk_level(client):
    data = client.get("/api/students/stu-003/risk-summary").json()
    assert "risk_level" in data
    assert data["risk_level"] in {"high", "medium", "low", "none"}
    assert "risk_factors" in data
    assert isinstance(data["risk_factors"], list)


def test_risk_summary_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/risk-summary").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 14 — GET /api/students/{id}/transcript
# ---------------------------------------------------------------------------

def test_transcript_returns_200(client):
    response = client.get("/api/students/stu-004/transcript")
    assert response.status_code == 200


def test_transcript_has_courses(client):
    data = client.get("/api/students/stu-004/transcript").json()
    assert "courses" in data
    assert isinstance(data["courses"], list)
    assert len(data["courses"]) >= 1
    first = data["courses"][0]
    assert "course_name" in first
    assert "course_code" in first
    assert "credits" in first


def test_transcript_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/transcript").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 15 — GET /api/students/{id}/skills
# ---------------------------------------------------------------------------

def test_skill_profile_returns_200(client):
    response = client.get("/api/students/stu-001/skills")
    assert response.status_code == 200


def test_skill_profile_has_data(client):
    data = client.get("/api/students/stu-001/skills").json()
    assert "target_role" in data
    assert "skills_gap" in data
    assert isinstance(data["skills_gap"], list)


def test_skill_profile_unknown_student_returns_404(client):
    assert client.get("/api/students/stu-999/skills").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 16 — GET /api/programs (list all programs)
# ---------------------------------------------------------------------------

def test_program_options_returns_200(client):
    response = client.get("/api/programs")
    assert response.status_code == 200


def test_program_options_has_programs(client):
    data = client.get("/api/programs").json()
    assert "programs" in data
    assert isinstance(data["programs"], list)
    assert len(data["programs"]) >= 2
    first = data["programs"][0]
    assert "name" in first
    assert "department" in first
    assert "degree_level" in first


# ---------------------------------------------------------------------------
# Cycle 17 — GET /api/programs/{id}/success-patterns
# ---------------------------------------------------------------------------

def test_success_patterns_returns_200(client):
    response = client.get("/api/programs/prog-001/success-patterns")
    assert response.status_code == 200


def test_success_patterns_has_data(client):
    data = client.get("/api/programs/prog-001/success-patterns").json()
    assert "alumni_count" in data or "patterns" in data


def test_success_patterns_unknown_program_returns_404(client):
    assert client.get("/api/programs/prog-999/success-patterns").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 18 — GET /api/programs/{id}/requirements
# ---------------------------------------------------------------------------

def test_curriculum_requirements_returns_200(client):
    response = client.get("/api/programs/prog-001/requirements")
    assert response.status_code == 200


def test_curriculum_requirements_has_requirements(client):
    data = client.get("/api/programs/prog-001/requirements").json()
    assert "requirements" in data
    assert isinstance(data["requirements"], list)
    assert len(data["requirements"]) >= 1
    first = data["requirements"][0]
    assert "requirement_type" in first
    assert "description" in first


def test_curriculum_requirements_unknown_program_returns_404(client):
    assert client.get("/api/programs/prog-999/requirements").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 19 — GET /api/programs/{id}/electives
# ---------------------------------------------------------------------------

def test_electives_returns_200(client):
    response = client.get("/api/programs/prog-001/electives")
    assert response.status_code == 200


def test_electives_has_courses(client):
    data = client.get("/api/programs/prog-001/electives").json()
    assert "electives" in data
    assert isinstance(data["electives"], list)


def test_electives_unknown_program_returns_404(client):
    assert client.get("/api/programs/prog-999/electives").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 20 — GET /api/courses/{id}/slo-history
# ---------------------------------------------------------------------------

def test_cohort_slo_history_returns_200(client):
    response = client.get("/api/courses/crs-001/slo-history")
    assert response.status_code == 200


def test_cohort_slo_history_has_entries(client):
    data = client.get("/api/courses/crs-001/slo-history").json()
    assert "slo_history" in data
    assert isinstance(data["slo_history"], list)
    assert len(data["slo_history"]) >= 1
    first = data["slo_history"][0]
    assert "semester" in first
    assert "proficiency_rate" in first


def test_cohort_slo_history_unknown_course_returns_404(client):
    assert client.get("/api/courses/crs-999/slo-history").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 21 — GET /api/courses/{id}/slo-assessments
# ---------------------------------------------------------------------------

def test_slo_assessments_returns_200(client):
    response = client.get("/api/courses/crs-001/slo-assessments")
    assert response.status_code == 200


def test_slo_assessments_has_entries(client):
    data = client.get("/api/courses/crs-001/slo-assessments").json()
    assert "assessments" in data
    assert isinstance(data["assessments"], list)
    assert len(data["assessments"]) >= 1
    first = data["assessments"][0]
    assert "proficiency_rate" in first
    assert "assessed_students" in first


def test_slo_assessments_unknown_course_returns_404(client):
    assert client.get("/api/courses/crs-999/slo-assessments").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 22 — GET /api/courses/{id}/availability
# ---------------------------------------------------------------------------

def test_course_availability_returns_200(client):
    response = client.get("/api/courses/crs-001/availability")
    assert response.status_code == 200


def test_course_availability_has_sections(client):
    data = client.get("/api/courses/crs-001/availability").json()
    assert "sections" in data
    assert isinstance(data["sections"], list)
    assert len(data["sections"]) >= 1
    first = data["sections"][0]
    assert "section_code" in first
    assert "capacity" in first
    assert "enrolled" in first
    assert "seats_available" in first


def test_course_availability_unknown_course_returns_404(client):
    assert client.get("/api/courses/crs-999/availability").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 23 — GET /api/courses/{id}/slo-performance
# ---------------------------------------------------------------------------

def test_course_slo_performance_returns_200(client):
    response = client.get("/api/courses/crs-001/slo-performance")
    assert response.status_code == 200


def test_course_slo_performance_has_data(client):
    data = client.get("/api/courses/crs-001/slo-performance").json()
    assert "slo_performance" in data
    assert isinstance(data["slo_performance"], list)


def test_course_slo_performance_unknown_course_returns_404(client):
    assert client.get("/api/courses/crs-999/slo-performance").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 24 — GET /api/cohorts/{id}/prerequisite-gaps (cohort = program)
# ---------------------------------------------------------------------------

def test_prerequisite_gaps_returns_200(client):
    response = client.get("/api/cohorts/prog-001/prerequisite-gaps")
    assert response.status_code == 200


def test_prerequisite_gaps_has_data(client):
    data = client.get("/api/cohorts/prog-001/prerequisite-gaps").json()
    assert "gaps" in data
    assert isinstance(data["gaps"], list)


def test_prerequisite_gaps_unknown_cohort_returns_404(client):
    assert client.get("/api/cohorts/prog-999/prerequisite-gaps").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 25 — GET /api/cohorts/{id}/slo-results
# ---------------------------------------------------------------------------

def test_cohort_slo_results_returns_200(client):
    response = client.get("/api/cohorts/prog-001/slo-results")
    assert response.status_code == 200


def test_cohort_slo_results_has_data(client):
    data = client.get("/api/cohorts/prog-001/slo-results").json()
    assert "slo_results" in data
    assert isinstance(data["slo_results"], list)


def test_cohort_slo_results_unknown_cohort_returns_404(client):
    assert client.get("/api/cohorts/prog-999/slo-results").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 26 — GET /api/cohorts/{id}/progression
# ---------------------------------------------------------------------------

def test_cohort_progression_returns_200(client):
    response = client.get("/api/cohorts/prog-001/progression")
    assert response.status_code == 200


def test_cohort_progression_has_data(client):
    data = client.get("/api/cohorts/prog-001/progression").json()
    assert "progression" in data
    assert isinstance(data["progression"], list)


def test_cohort_progression_unknown_cohort_returns_404(client):
    assert client.get("/api/cohorts/prog-999/progression").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 27 — GET /api/faculty (list all faculty)
# ---------------------------------------------------------------------------

def test_faculty_list_returns_200(client):
    response = client.get("/api/faculty")
    assert response.status_code == 200


def test_faculty_list_has_faculty(client):
    data = client.get("/api/faculty").json()
    assert "faculty" in data
    assert isinstance(data["faculty"], list)
    assert len(data["faculty"]) >= 1
    first = data["faculty"][0]
    assert "name" in first
    assert "department" in first
    assert "title" in first


# ---------------------------------------------------------------------------
# Cycle 28 — GET /api/faculty/{id}/workload
# ---------------------------------------------------------------------------

def test_faculty_workload_returns_200(client):
    response = client.get("/api/faculty/fac-001/workload")
    assert response.status_code == 200


def test_faculty_workload_has_data(client):
    data = client.get("/api/faculty/fac-001/workload").json()
    assert "name" in data
    assert "current_credits" in data
    assert "max_credits" in data
    assert "courses" in data
    assert isinstance(data["courses"], list)


def test_faculty_workload_unknown_faculty_returns_404(client):
    assert client.get("/api/faculty/fac-999/workload").status_code == 404


# ---------------------------------------------------------------------------
# Cycle 29 — GET /api/mentors (mentor pool — AlumniMentor with availability)
# ---------------------------------------------------------------------------

def test_mentor_pool_returns_200(client):
    response = client.get("/api/mentors")
    assert response.status_code == 200


def test_mentor_pool_has_mentors(client):
    data = client.get("/api/mentors").json()
    assert "mentors" in data
    assert isinstance(data["mentors"], list)
    assert len(data["mentors"]) >= 1
    first = data["mentors"][0]
    assert "name" in first
    assert "current_role" in first
    assert "available" in first


# ---------------------------------------------------------------------------
# Cycle 30 — GET /api/alumni/mentors and GET /api/alumni/outcomes
# ---------------------------------------------------------------------------

def test_alumni_mentors_returns_200(client):
    response = client.get("/api/alumni/mentors")
    assert response.status_code == 200


def test_alumni_mentors_has_data(client):
    data = client.get("/api/alumni/mentors").json()
    assert "mentors" in data
    assert isinstance(data["mentors"], list)
    first = data["mentors"][0]
    assert "name" in first
    assert "graduation_year" in first
    assert "current_company" in first


def test_alumni_outcomes_returns_200(client):
    response = client.get("/api/alumni/outcomes")
    assert response.status_code == 200


def test_alumni_outcomes_has_data(client):
    data = client.get("/api/alumni/outcomes").json()
    assert "outcomes" in data
    assert isinstance(data["outcomes"], list)


# ---------------------------------------------------------------------------
# Cycle 31 — GET /api/internships
# ---------------------------------------------------------------------------

def test_internship_options_returns_200(client):
    response = client.get("/api/internships")
    assert response.status_code == 200


def test_internship_options_has_data(client):
    data = client.get("/api/internships").json()
    assert "internships" in data
    assert isinstance(data["internships"], list)
