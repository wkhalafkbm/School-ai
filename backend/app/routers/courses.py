from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _require_course(course_id: str, db: Session) -> models.Course:
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# --- get_cohort_slo_history ---

@router.get("/{course_id}/slo-history", summary="Get cohort SLO history", description="Returns historical SLO proficiency rates and average scores for a course across past semesters.")
def get_cohort_slo_history(course_id: str, db: Session = Depends(get_db)):
    course = _require_course(course_id, db)
    history = (
        db.query(models.CohortSLOHistory)
        .filter(models.CohortSLOHistory.course_id == course_id)
        .order_by(models.CohortSLOHistory.semester)
        .all()
    )
    return {
        "course_id": course_id,
        "course_code": course.code,
        "course_name": course.name,
        "slo_history": [
            {
                "semester": h.semester,
                "slo_code": h.slo.code if h.slo else None,
                "proficiency_rate": h.proficiency_rate,
                "avg_score": h.avg_score,
                "cohort_size": h.cohort_size,
            }
            for h in history
        ],
    }


# --- get_slo_assessments ---

@router.get("/{course_id}/slo-assessments", summary="Get SLO assessments", description="Returns SLO assessment records for a course including proficiency rates, average scores, and number of students assessed per SLO.")
def get_slo_assessments(course_id: str, db: Session = Depends(get_db)):
    course = _require_course(course_id, db)
    assessments = (
        db.query(models.SLOAssessment)
        .filter(models.SLOAssessment.course_id == course_id)
        .all()
    )
    return {
        "course_id": course_id,
        "course_code": course.code,
        "assessments": [
            {
                "slo_code": a.slo.code if a.slo else None,
                "slo_description": a.slo.description if a.slo else None,
                "semester": a.semester,
                "assessment_date": str(a.assessment_date) if a.assessment_date else None,
                "assessed_students": a.assessed_students,
                "proficient_count": a.proficient_count,
                "proficiency_rate": a.proficiency_rate,
                "avg_score": a.avg_score,
            }
            for a in assessments
        ],
    }


# --- get_course_availability ---

@router.get("/{course_id}/availability", summary="Get course availability", description="Returns scheduled sections for a course with capacity, current enrollment, seats available, days, and time slots.")
def get_course_availability(course_id: str, db: Session = Depends(get_db)):
    course = _require_course(course_id, db)
    sections = (
        db.query(models.ScheduleSection)
        .filter(models.ScheduleSection.course_id == course_id)
        .all()
    )
    return {
        "course_id": course_id,
        "course_code": course.code,
        "course_name": course.name,
        "credits": course.credits,
        "sections": [
            {
                "section_code": s.section_code,
                "semester": s.semester,
                "days": s.days,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "room": s.room,
                "capacity": s.capacity,
                "enrolled": s.enrolled,
                "seats_available": (s.capacity or 0) - (s.enrolled or 0),
            }
            for s in sections
        ],
    }


# --- get_course_slo_performance ---

@router.get("/{course_id}/slo-performance", summary="Get course SLO performance", description="Returns per-SLO performance summary for a course including proficiency rate and total students assessed.")
def get_course_slo_performance(course_id: str, db: Session = Depends(get_db)):
    course = _require_course(course_id, db)
    slos = (
        db.query(models.SLO)
        .filter(models.SLO.course_id == course_id)
        .all()
    )
    result = []
    for slo in slos:
        results = slo.student_results
        proficient = sum(1 for r in results if r.proficient)
        total = len(results)
        result.append({
            "slo_code": slo.code,
            "description": slo.description,
            "bloom_level": slo.bloom_level,
            "assessment_method": slo.assessment_method,
            "total_assessed": total,
            "proficient_count": proficient,
            "proficiency_rate": round(proficient / total, 3) if total else None,
        })
    return {
        "course_id": course_id,
        "course_code": course.code,
        "slo_performance": result,
    }
