"""Cohort endpoints — cohort is identified by program_id."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])


def _require_program(cohort_id: str, db: Session) -> models.Program:
    program = db.query(models.Program).filter(models.Program.id == cohort_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Cohort (program) not found")
    return program


# --- get_prerequisite_gaps ---

@router.get("/{cohort_id}/prerequisite-gaps", summary="Get prerequisite gaps", description="Returns students in a program cohort who are enrolled in courses without having passed the required prerequisites.")
def get_prerequisite_gaps(cohort_id: str, db: Session = Depends(get_db)):
    program = _require_program(cohort_id, db)
    students = (
        db.query(models.Student)
        .filter(models.Student.program_id == cohort_id)
        .all()
    )
    gaps = []
    for student in students:
        passed_course_ids = {
            e.course_id
            for e in student.enrollments
            if e.grade and e.grade not in {"F", "W", "WF"}
        }
        enrolled_course_ids = {e.course_id for e in student.enrollments}
        prereqs = (
            db.query(models.Prerequisite)
            .filter(models.Prerequisite.course_id.in_(enrolled_course_ids))
            .all()
        )
        for p in prereqs:
            if p.prerequisite_course_id not in passed_course_ids:
                gaps.append({
                    "student_name": student.name,
                    "student_id": student.id,
                    "course_code": p.course.code if p.course else None,
                    "prerequisite_code": p.prerequisite_course.code if p.prerequisite_course else None,
                })
    return {
        "cohort_id": cohort_id,
        "program_name": program.name,
        "gaps": gaps,
    }


# --- get_cohort_slo_results ---

@router.get("/{cohort_id}/slo-results", summary="Get cohort SLO results", description="Returns SLO proficiency history across all courses in a program cohort, aggregated by course and semester.")
def get_cohort_slo_results(cohort_id: str, db: Session = Depends(get_db)):
    program = _require_program(cohort_id, db)
    course_ids = [c.id for c in program.courses]
    history = (
        db.query(models.CohortSLOHistory)
        .filter(models.CohortSLOHistory.course_id.in_(course_ids))
        .all()
    )
    return {
        "cohort_id": cohort_id,
        "program_name": program.name,
        "slo_results": [
            {
                "course_code": h.course_code,
                "slo_code": h.slo.code if h.slo else None,
                "semester": h.semester,
                "proficiency_rate": h.proficiency_rate,
                "avg_score": h.avg_score,
                "cohort_size": h.cohort_size,
            }
            for h in history
        ],
    }


# --- get_cohort_progression ---

@router.get("/{cohort_id}/progression", summary="Get cohort progression", description="Returns credit progression and graduation timeline for each student in a program cohort, including on-track status and projected graduation date.")
def get_cohort_progression(cohort_id: str, db: Session = Depends(get_db)):
    program = _require_program(cohort_id, db)
    progress_records = (
        db.query(models.StudentCourseProgress)
        .filter(models.StudentCourseProgress.program_id == cohort_id)
        .all()
    )
    return {
        "cohort_id": cohort_id,
        "program_name": program.name,
        "progression": [
            {
                "student_id": p.student_id,
                "student_name": p.student.name if p.student else None,
                "credits_earned": p.credits_earned,
                "credits_required": p.credits_required,
                "credits_deficit": p.credits_deficit,
                "on_track": p.on_track,
                "projected_graduation": p.projected_graduation,
                "expected_graduation": p.expected_graduation,
            }
            for p in progress_records
        ],
    }
