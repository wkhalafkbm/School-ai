from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/faculty", tags=["faculty"])


def _require_faculty(faculty_id: str, db: Session) -> models.Faculty:
    faculty = db.query(models.Faculty).filter(models.Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    return faculty


# --- get_faculty_list ---

@router.get("", summary="Get faculty list", description="Returns all faculty members with name, title, department, email, and specialization.")
def get_faculty_list(db: Session = Depends(get_db)):
    faculty_list = db.query(models.Faculty).all()
    return {
        "faculty": [
            {
                "id": f.id,
                "name": f.name,
                "title": f.title,
                "department": f.department,
                "email": f.email,
                "specialization": f.specialization,
            }
            for f in faculty_list
        ]
    }


# --- get_faculty_workload ---

@router.get("/{faculty_id}/workload", summary="Get faculty workload", description="Returns a faculty member's current credit load, maximum credits, overload status, and list of assigned courses.")
def get_faculty_workload(faculty_id: str, db: Session = Depends(get_db)):
    faculty = _require_faculty(faculty_id, db)
    courses = (
        db.query(models.Course)
        .filter(models.Course.instructor_id == faculty_id)
        .all()
    )
    return {
        "id": faculty.id,
        "name": faculty.name,
        "department": faculty.department,
        "specialization": faculty.specialization,
        "max_credits": faculty.max_credits,
        "current_credits": faculty.current_credits,
        "overloaded": (faculty.current_credits or 0) > (faculty.max_credits or 0),
        "courses": [
            {
                "course_code": c.code,
                "course_name": c.name,
                "credits": c.credits,
                "semester": c.semester,
            }
            for c in courses
        ],
    }
