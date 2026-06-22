from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/programs", tags=["programs"])


def _require_program(program_id: str, db: Session) -> models.Program:
    program = db.query(models.Program).filter(models.Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


# --- get_program_options ---

@router.get("", summary="Get program options", description="Returns all available degree programs including name, department, degree level, total credits, and duration.")
def get_program_options(db: Session = Depends(get_db)):
    programs = db.query(models.Program).all()
    return {
        "programs": [
            {
                "id": p.id,
                "name": p.name,
                "department": p.department,
                "degree_level": p.degree_level,
                "total_credits": p.total_credits,
                "duration_years": p.duration_years,
            }
            for p in programs
        ]
    }


# --- get_historical_success_patterns ---

@router.get("/{program_id}/success-patterns", summary="Get historical success patterns", description="Returns alumni outcomes and industry breakdown for a program, showing historical graduate success patterns by industry and role.")
def get_success_patterns(program_id: str, db: Session = Depends(get_db)):
    program = _require_program(program_id, db)
    alumni = (
        db.query(models.AlumniMentor)
        .filter(models.AlumniMentor.program_id == program_id)
        .all()
    )
    industry_counts: dict[str, int] = {}
    for a in alumni:
        industry_counts[a.industry] = industry_counts.get(a.industry, 0) + 1

    return {
        "program_id": program_id,
        "program_name": program.name,
        "alumni_count": len(alumni),
        "patterns": [
            {
                "industry": industry,
                "alumni_count": count,
            }
            for industry, count in industry_counts.items()
        ],
        "sample_outcomes": [
            {
                "name": a.name,
                "graduation_year": a.graduation_year,
                "current_role": a.current_role,
                "current_company": a.current_company,
                "industry": a.industry,
            }
            for a in alumni[:5]
        ],
    }


# --- get_curriculum_requirements ---

@router.get("/{program_id}/requirements", summary="Get curriculum requirements", description="Returns all graduation requirements for a program including credit thresholds, mandatory courses, and capstone conditions.")
def get_curriculum_requirements(program_id: str, db: Session = Depends(get_db)):
    program = _require_program(program_id, db)
    requirements = (
        db.query(models.GraduationRequirement)
        .filter(models.GraduationRequirement.program_id == program_id)
        .all()
    )
    return {
        "program_id": program_id,
        "program_name": program.name,
        "total_credits": program.total_credits,
        "requirements": [
            {
                "requirement_type": r.requirement_type,
                "description": r.description,
                "required_value": r.required_value,
            }
            for r in requirements
        ],
    }


# --- get_electives ---

@router.get("/{program_id}/electives", summary="Get electives", description="Returns available elective courses for a program — courses that are not required as prerequisites for any other course.")
def get_electives(program_id: str, db: Session = Depends(get_db)):
    program = _require_program(program_id, db)
    courses = (
        db.query(models.Course)
        .filter(models.Course.program_id == program_id)
        .all()
    )
    # Electives are courses in the program not listed as prerequisites for anything
    required_course_ids = {
        p.course_id
        for p in db.query(models.Prerequisite).all()
    }
    electives = [c for c in courses if c.id not in required_course_ids]
    return {
        "program_id": program_id,
        "program_name": program.name,
        "electives": [
            {
                "course_code": c.code,
                "course_name": c.name,
                "credits": c.credits,
                "description": c.description,
                "semester": c.semester,
            }
            for c in electives
        ],
    }
