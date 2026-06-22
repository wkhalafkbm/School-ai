from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(tags=["alumni"])


# --- get_mentor_pool ---

@router.get("/api/mentors", summary="Get mentor pool", description="Returns all available alumni mentors with their current role, company, industry, mentoring capacity, and availability status.")
def get_mentor_pool(db: Session = Depends(get_db)):
    mentors = db.query(models.AlumniMentor).all()
    return {
        "mentors": [
            {
                "id": m.id,
                "name": m.name,
                "program_name": m.program.name if m.program else None,
                "graduation_year": m.graduation_year,
                "current_role": m.current_role,
                "current_company": m.current_company,
                "industry": m.industry,
                "mentoring_capacity": m.mentoring_capacity,
                "current_mentees": m.current_mentees,
                "available": m.available,
                "contact_email": m.contact_email,
                "linkedin_profile": m.linkedin_profile,
            }
            for m in mentors
        ]
    }


# --- get_alumni_mentors ---

@router.get("/api/alumni/mentors", summary="Get alumni mentors", description="Returns all alumni who are available as mentors, with graduation year, current role, company, and mentoring capacity.")
def get_alumni_mentors(db: Session = Depends(get_db)):
    mentors = db.query(models.AlumniMentor).all()
    return {
        "mentors": [
            {
                "id": m.id,
                "name": m.name,
                "program_name": m.program.name if m.program else None,
                "graduation_year": m.graduation_year,
                "current_role": m.current_role,
                "current_company": m.current_company,
                "industry": m.industry,
                "available": m.available,
                "mentoring_capacity": m.mentoring_capacity,
                "current_mentees": m.current_mentees,
            }
            for m in mentors
        ]
    }


# --- get_graduate_outcomes ---

@router.get("/api/alumni/outcomes", summary="Get graduate outcomes", description="Returns graduate outcome data including industry breakdown and individual alumni career trajectories.")
def get_graduate_outcomes(db: Session = Depends(get_db)):
    alumni = db.query(models.AlumniMentor).all()
    industry_breakdown: dict[str, int] = {}
    for a in alumni:
        if a.industry:
            industry_breakdown[a.industry] = industry_breakdown.get(a.industry, 0) + 1

    return {
        "total_alumni": len(alumni),
        "industry_breakdown": [
            {"industry": k, "count": v} for k, v in industry_breakdown.items()
        ],
        "outcomes": [
            {
                "name": a.name,
                "graduation_year": a.graduation_year,
                "current_role": a.current_role,
                "current_company": a.current_company,
                "industry": a.industry,
                "program_name": a.program.name if a.program else None,
            }
            for a in alumni
        ],
    }


# --- get_internship_options ---

@router.get("/api/internships", summary="Get internship options", description="Returns available internship opportunities derived from student career pathways, including target company, industry, and recommended semester.")
def get_internship_options(db: Session = Depends(get_db)):
    pathways = db.query(models.CareerPathway).all()
    seen_companies: set[str] = set()
    internships = []
    for p in pathways:
        for company in (p.target_companies or []):
            if company not in seen_companies:
                seen_companies.add(company)
                internships.append({
                    "company": company,
                    "target_semester": p.internship_target_semester,
                    "industry": p.target_industry,
                })
    return {"internships": internships}
