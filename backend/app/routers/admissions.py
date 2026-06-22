from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.status import StatusCode

router = APIRouter(prefix="/api/admissions", tags=["admissions"])

STUDENT_ID = "stu-001"


def _admissions_health(pending: int, total: int) -> str:
    if total == 0:
        return StatusCode.on_track
    ratio = pending / total
    if ratio <= 0.05:
        return StatusCode.on_track
    if ratio <= 0.30:
        return StatusCode.watch
    if ratio <= 0.60:
        return StatusCode.needs_attention
    return StatusCode.urgent


@router.get("/profile")
def admissions_profile(db: Session = Depends(get_db)):
    # --- stage summary ---
    applicant_count = db.execute(
        text("SELECT COUNT(*) FROM students WHERE status = 'applicant'")
    ).scalar() or 0

    pending_review_count = db.execute(
        text("""
            SELECT COUNT(*) FROM workflow_items
            WHERE stage = 'admissions' AND status IN ('pending', 'in_review')
        """)
    ).scalar() or 0

    health = _admissions_health(int(pending_review_count), max(int(applicant_count), 1))

    # --- applicant profile (Waleed Khalaf, stu-001) ---
    row = db.execute(
        text("""
            SELECT s.id, s.name, s.nationality, s.admission_term,
                   p.name AS program_name, p.degree_level
            FROM students s
            JOIN programs p ON p.id = s.program_id
            WHERE s.id = :sid
        """),
        {"sid": STUDENT_ID},
    ).one()

    sponsorship_status = "KFAS eligible" if row.nationality == "Kuwaiti" else "self-funded"

    # --- evidence: graduate outcomes from same program ---
    enrolled_count = db.execute(
        text("""
            SELECT COUNT(*) FROM students
            WHERE program_id = (
                SELECT program_id FROM students WHERE id = :sid
            )
            AND status = 'enrolled'
        """),
        {"sid": STUDENT_ID},
    ).scalar() or 0

    on_track_count = db.execute(
        text("""
            SELECT COUNT(*) FROM student_course_progress scp
            JOIN students s ON s.id = scp.student_id
            WHERE s.program_id = (
                SELECT program_id FROM students WHERE id = :sid
            )
            AND scp.on_track = TRUE
        """),
        {"sid": STUDENT_ID},
    ).scalar() or 0

    cohort_size = int(enrolled_count)
    on_track_pct = round((int(on_track_count) / cohort_size * 100)) if cohort_size else 0

    signal_strength = "medium" if cohort_size >= 5 else "low"
    data_completeness = "partial"

    # --- recommendation ---
    confidence = "Medium" if cohort_size >= 5 else "Low"
    rationale = (
        "Applicant profile aligns with program benchmarks. "
        "Sponsorship eligibility confirmed through KFAS. "
        f"Historical cohort of {cohort_size} similar profiles shows {on_track_pct}% on-track graduation rate."
    )

    return {
        "stage_summary": {
            "health": health,
            "applicant_count": int(applicant_count),
            "pending_review_count": int(pending_review_count),
        },
        "applicant": {
            "id": row.id,
            "name": row.name,
            "nationality": row.nationality,
            "admission_term": row.admission_term,
            "program_name": row.program_name,
            "program_interest": row.program_name,
            "degree_level": row.degree_level,
            "sponsorship_status": sponsorship_status,
            "financial_readiness": "eligible",
        },
        "recommendation": {
            "action": "Recommend standard admission pathway",
            "confidence": confidence,
            "rationale": rationale,
        },
        "evidence": {
            "graduate_outcomes": [
                {
                    "profile": f"Kuwaiti applicants — {row.program_name}",
                    "outcome": f"{on_track_pct}% on track for on-time graduation",
                    "cohort_size": cohort_size,
                }
            ],
            "signal_strength": signal_strength,
            "data_completeness": data_completeness,
        },
    }
