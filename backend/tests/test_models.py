from app.models import (
    Student, Program, Course, Faculty, Enrollment, LMSSignal,
    OnboardingTask, Prerequisite, ScheduleSection, SponsorshipRecord,
    FinancialAidRecord, AdministrativeHold, SupportCase, Intervention,
    GraduationRequirement, StudentCourseProgress, CareerPathway,
    AlumniMentor, WorkflowItem, SLO, SLOAssessment,
    CohortSLOHistory, StudentSLOResult,
)


ALL_MODELS = [
    Student, Program, Course, Faculty, Enrollment, LMSSignal,
    OnboardingTask, Prerequisite, ScheduleSection, SponsorshipRecord,
    FinancialAidRecord, AdministrativeHold, SupportCase, Intervention,
    GraduationRequirement, StudentCourseProgress, CareerPathway,
    AlumniMentor, WorkflowItem, SLO, SLOAssessment,
    CohortSLOHistory, StudentSLOResult,
]


def test_all_models_importable():
    assert len(ALL_MODELS) == 23


def test_metadata_validates():
    from app.models import Base
    tables = set(Base.metadata.tables.keys())
    expected = {
        "students", "programs", "courses", "faculty", "enrollments",
        "lms_signals", "onboarding_tasks", "prerequisites", "schedule_sections",
        "sponsorship_records", "financial_aid_records", "administrative_holds",
        "support_cases", "interventions", "graduation_requirements",
        "student_course_progress", "career_pathways", "alumni_mentors",
        "workflow_items", "slos", "slo_assessments", "cohort_slo_history",
        "student_slo_results",
    }
    assert tables == expected


def test_every_model_has_data_source_column():
    for model in ALL_MODELS:
        columns = {c.name for c in model.__table__.columns}
        assert "data_source" in columns, f"{model.__name__} missing data_source"
