from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, DateTime, Text,
    ForeignKey, Enum as SAEnum, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class DataSource(str, enum.Enum):
    SIS = "SIS"
    LMS = "LMS"
    demo = "demo"


class Base(DeclarativeBase):
    pass


class Program(Base):
    __tablename__ = "programs"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String)
    degree_level = Column(String)
    total_credits = Column(Integer)
    duration_years = Column(Integer)
    data_source = Column(SAEnum(DataSource), nullable=False)

    students = relationship("Student", back_populates="program")
    courses = relationship("Course", back_populates="program")
    graduation_requirements = relationship("GraduationRequirement", back_populates="program")
    alumni_mentors = relationship("AlumniMentor", back_populates="program")


class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    title = Column(String)
    department = Column(String)
    email = Column(String)
    specialization = Column(String)
    max_credits = Column(Integer)
    current_credits = Column(Integer)
    data_source = Column(SAEnum(DataSource), nullable=False)

    courses = relationship("Course", back_populates="instructor")


class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    credits = Column(Integer)
    semester = Column(String)
    program_id = Column(String, ForeignKey("programs.id"))
    instructor_id = Column(String, ForeignKey("faculty.id"))
    data_source = Column(SAEnum(DataSource), nullable=False)

    program = relationship("Program", back_populates="courses")
    instructor = relationship("Faculty", back_populates="courses")
    enrollments = relationship("Enrollment", back_populates="course")
    slos = relationship("SLO", back_populates="course")
    cohort_slo_history = relationship("CohortSLOHistory", back_populates="course")
    schedule_sections = relationship("ScheduleSection", back_populates="course")
    prerequisites_as_course = relationship(
        "Prerequisite", foreign_keys="Prerequisite.course_id", back_populates="course"
    )
    prerequisites_as_requirement = relationship(
        "Prerequisite", foreign_keys="Prerequisite.prerequisite_course_id", back_populates="prerequisite_course"
    )


class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    gender = Column(String)
    nationality = Column(String)
    program_id = Column(String, ForeignKey("programs.id"))
    status = Column(String)
    year_level = Column(Integer)
    credits_earned = Column(Integer)
    gpa = Column(Float)
    admission_term = Column(String)
    data_source = Column(SAEnum(DataSource), nullable=False)

    program = relationship("Program", back_populates="students")
    enrollments = relationship("Enrollment", back_populates="student")
    lms_signals = relationship("LMSSignal", back_populates="student")
    onboarding_tasks = relationship("OnboardingTask", back_populates="student")
    sponsorship_records = relationship("SponsorshipRecord", back_populates="student")
    financial_aid_records = relationship("FinancialAidRecord", back_populates="student")
    administrative_holds = relationship("AdministrativeHold", back_populates="student")
    support_cases = relationship("SupportCase", back_populates="student")
    interventions = relationship("Intervention", back_populates="student")
    student_course_progress = relationship("StudentCourseProgress", back_populates="student")
    career_pathways = relationship("CareerPathway", back_populates="student")
    workflow_items = relationship("WorkflowItem", back_populates="student")
    student_slo_results = relationship("StudentSLOResult", back_populates="student")


class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    section_id = Column(String, ForeignKey("schedule_sections.id"))
    semester = Column(String)
    grade = Column(String)
    status = Column(String)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    section = relationship("ScheduleSection", back_populates="enrollments")


class LMSSignal(Base):
    __tablename__ = "lms_signals"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    semester = Column(String)
    signal_date = Column(Date)
    login_count_last_30_days = Column(Integer)
    last_login_days_ago = Column(Integer)
    assignment_submission_rate = Column(Float)
    avg_quiz_score = Column(Float)
    video_watch_rate = Column(Float)
    forum_posts = Column(Integer)
    risk_flag = Column(String(10), default="none")
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="lms_signals")


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    task_name = Column(String)
    category = Column(String)
    completed = Column(Boolean, default=False)
    due_date = Column(Date)
    completed_date = Column(Date)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="onboarding_tasks")


class Prerequisite(Base):
    __tablename__ = "prerequisites"
    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    prerequisite_course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    min_grade = Column(String)
    data_source = Column(SAEnum(DataSource), nullable=False)

    course = relationship("Course", foreign_keys=[course_id], back_populates="prerequisites_as_course")
    prerequisite_course = relationship("Course", foreign_keys=[prerequisite_course_id], back_populates="prerequisites_as_requirement")


class ScheduleSection(Base):
    __tablename__ = "schedule_sections"
    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    section_code = Column(String)
    instructor_id = Column(String, ForeignKey("faculty.id"))
    semester = Column(String)
    days = Column(JSON)
    start_time = Column(String)
    end_time = Column(String)
    room = Column(String)
    capacity = Column(Integer)
    enrolled = Column(Integer)
    data_source = Column(SAEnum(DataSource), nullable=False)

    course = relationship("Course", back_populates="schedule_sections")
    enrollments = relationship("Enrollment", back_populates="section")


class SponsorshipRecord(Base):
    __tablename__ = "sponsorship_records"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    sponsor_name = Column(String)
    sponsor_full_name = Column(String)
    program_id = Column(String, ForeignKey("programs.id"))
    coverage_type = Column(String)
    amount_per_semester = Column(Float)
    currency = Column(String)
    status = Column(String)
    application_date = Column(Date)
    approval_date = Column(Date)
    notes = Column(Text)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="sponsorship_records")


class FinancialAidRecord(Base):
    __tablename__ = "financial_aid_records"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    aid_type = Column(String)
    amount = Column(Float)
    currency = Column(String)
    semester = Column(String)
    status = Column(String)
    applied_date = Column(Date)
    approved_date = Column(Date)
    renewable = Column(Boolean)
    renewal_conditions = Column(Text)
    notes = Column(Text)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="financial_aid_records")


class AdministrativeHold(Base):
    __tablename__ = "administrative_holds"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    hold_type = Column(String)
    reason = Column(Text)
    severity = Column(String)
    blocks_registration = Column(Boolean, default=False)
    blocks_transcript = Column(Boolean, default=False)
    placed_by = Column(String)
    placed_date = Column(Date)
    resolved_date = Column(Date)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="administrative_holds")


class SupportCase(Base):
    __tablename__ = "support_cases"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    case_type = Column(String)
    subject = Column(String)
    description = Column(Text)
    priority = Column(String)
    status = Column(String)
    assigned_to_faculty_id = Column(String, ForeignKey("faculty.id"))
    resolution = Column(Text)
    opened_date = Column(Date)
    closed_date = Column(Date)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="support_cases")


class Intervention(Base):
    __tablename__ = "interventions"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    case_id = Column(String, ForeignKey("support_cases.id"))
    intervention_type = Column(String)
    recommended_by = Column(String)
    description = Column(Text)
    status = Column(String)
    created_date = Column(Date)
    approved_date = Column(Date)
    completed_date = Column(Date)
    outcome = Column(Text)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="interventions")


class GraduationRequirement(Base):
    __tablename__ = "graduation_requirements"
    id = Column(String, primary_key=True)
    program_id = Column(String, ForeignKey("programs.id"), nullable=False)
    requirement_type = Column(String)
    description = Column(Text)
    required_value = Column(Integer)
    data_source = Column(SAEnum(DataSource), nullable=False)

    program = relationship("Program", back_populates="graduation_requirements")


class StudentCourseProgress(Base):
    __tablename__ = "student_course_progress"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    program_id = Column(String, ForeignKey("programs.id"))
    credits_earned = Column(Integer)
    credits_required = Column(Integer)
    credits_deficit = Column(Integer)
    expected_credits_at_year_3 = Column(Integer)
    core_credits_earned = Column(Integer)
    math_credits_earned = Column(Integer)
    capstone_completed = Column(Boolean, default=False)
    internship_hours_completed = Column(Integer)
    on_track = Column(Boolean)
    projected_graduation = Column(String)
    expected_graduation = Column(String)
    notes = Column(Text)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="student_course_progress")


class CareerPathway(Base):
    __tablename__ = "career_pathways"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    target_role = Column(String)
    target_industry = Column(String)
    status = Column(String)
    skills_gap = Column(JSON)
    recommended_courses = Column(JSON)
    target_companies = Column(JSON)
    linkedin_profile = Column(String)
    internship_target_semester = Column(String)
    created_date = Column(Date)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="career_pathways")


class AlumniMentor(Base):
    __tablename__ = "alumni_mentors"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    program_id = Column(String, ForeignKey("programs.id"))
    graduation_year = Column(Integer)
    current_role = Column(String)
    current_company = Column(String)
    industry = Column(String)
    contact_email = Column(String)
    linkedin_profile = Column(String)
    mentoring_capacity = Column(Integer)
    current_mentees = Column(Integer)
    mentee_student_ids = Column(JSON)
    available = Column(Boolean, default=True)
    data_source = Column(SAEnum(DataSource), nullable=False)

    program = relationship("Program", back_populates="alumni_mentors")


class WorkflowItem(Base):
    __tablename__ = "workflow_items"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"))
    workflow_type = Column(String)
    title = Column(String)
    description = Column(Text)
    status = Column(String)
    priority = Column(String)
    assigned_to = Column(String)
    created_date = Column(Date)
    due_date = Column(Date)
    completed_date = Column(Date)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="workflow_items")


class SLO(Base):
    __tablename__ = "slos"
    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    code = Column(String)
    description = Column(Text)
    bloom_level = Column(String)
    assessment_method = Column(String)
    data_source = Column(SAEnum(DataSource), nullable=False)

    course = relationship("Course", back_populates="slos")
    assessments = relationship("SLOAssessment", back_populates="slo")
    cohort_history = relationship("CohortSLOHistory", back_populates="slo")
    student_results = relationship("StudentSLOResult", back_populates="slo")


class SLOAssessment(Base):
    __tablename__ = "slo_assessments"
    id = Column(String, primary_key=True)
    slo_id = Column(String, ForeignKey("slos.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"))
    semester = Column(String)
    assessment_date = Column(Date)
    assessed_students = Column(Integer)
    proficient_count = Column(Integer)
    proficiency_rate = Column(Float)
    avg_score = Column(Float)
    data_source = Column(SAEnum(DataSource), nullable=False)

    slo = relationship("SLO", back_populates="assessments")


class CohortSLOHistory(Base):
    __tablename__ = "cohort_slo_history"
    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    slo_id = Column(String, ForeignKey("slos.id"), nullable=False)
    course_code = Column(String)
    semester = Column(String, nullable=False)
    proficiency_rate = Column(Float)
    avg_score = Column(Float)
    cohort_size = Column(Integer)
    data_source = Column(SAEnum(DataSource), nullable=False)

    course = relationship("Course", back_populates="cohort_slo_history")
    slo = relationship("SLO", back_populates="cohort_history")


class StudentSLOResult(Base):
    __tablename__ = "student_slo_results"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    slo_id = Column(String, ForeignKey("slos.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"))
    semester = Column(String)
    score = Column(Float)
    proficient = Column(Boolean)
    attempt_number = Column(Integer)
    data_source = Column(SAEnum(DataSource), nullable=False)

    student = relationship("Student", back_populates="student_slo_results")
    slo = relationship("SLO", back_populates="student_results")
