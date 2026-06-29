from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.evidence import build_evidence
from app.status import StatusCode

router = APIRouter(prefix="/api/progression", tags=["progression"])

STUDENT_ID = "stu-004"
CURRENT_SEMESTER = "2024-Fall"
BOTTLENECK_COURSE_ID = "crs-005"
SLO_TARGET_RATE = 0.70


def _progression_health(at_risk: int, total: int) -> str:
    if total == 0:
        return StatusCode.on_track
    ratio = at_risk / total
    if ratio > 0.5:
        return StatusCode.urgent
    if ratio > 0.3:
        return StatusCode.needs_attention
    if ratio > 0.1:
        return StatusCode.watch
    return StatusCode.on_track


@router.get("/profile")
def progression_profile(db: Session = Depends(get_db)):
    # --- stage summary: on_track vs at_risk graduation counts ---
    counts_row = db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE on_track = true)  AS on_track_count,
                COUNT(*) FILTER (WHERE on_track = false) AS at_risk_count
            FROM student_course_progress
        """)
    ).one()

    on_track_count = int(counts_row.on_track_count or 0)
    at_risk_count = int(counts_row.at_risk_count or 0)

    # --- Noor's student profile ---
    student_row = db.execute(
        text("""
            SELECT s.id, s.name, s.year_level, s.gpa,
                   p.name AS program_name
            FROM students s
            JOIN programs p ON p.id = s.program_id
            WHERE s.id = :sid
        """),
        {"sid": STUDENT_ID},
    ).one()

    # --- Noor's course progress ---
    progress_row = db.execute(
        text("""
            SELECT credits_earned, credits_required,
                   core_credits_earned, math_credits_earned,
                   capstone_completed, internship_hours_completed,
                   projected_graduation, expected_graduation
            FROM student_course_progress
            WHERE student_id = :sid
        """),
        {"sid": STUDENT_ID},
    ).one()

    # --- graduation requirements for Noor's program ---
    req_rows = db.execute(
        text("""
            SELECT requirement_type, required_value
            FROM graduation_requirements
            WHERE program_id = (
                SELECT program_id FROM students WHERE id = :sid
            )
        """),
        {"sid": STUDENT_ID},
    ).fetchall()

    reqs = {row.requirement_type: int(row.required_value) for row in req_rows}

    credit_map = {
        "total": {
            "earned": int(progress_row.credits_earned),
            "required": reqs.get("total_credits", 132),
        },
        "core": {
            "earned": int(progress_row.core_credits_earned),
            "required": reqs.get("core_credits", 60),
        },
        "math": {
            "earned": int(progress_row.math_credits_earned),
            "required": reqs.get("math_credits", 12),
        },
        "capstone": {
            "completed": bool(progress_row.capstone_completed),
            "required": True,
        },
        "internship": {
            "hours_completed": int(progress_row.internship_hours_completed),
            "hours_required": reqs.get("internship", 240),
        },
        "substitutions": [
            {
                "substituted_course": "CS201 (Data Structures)",
                "note": "Approved substitution — counted toward core elective requirement",
            }
        ],
    }

    # --- bottleneck course: highest fill-rate section among Noor's active enrollments ---
    bottleneck_row = db.execute(
        text("""
            SELECT c.id, c.code AS course_code, c.name AS course_name,
                   ss.capacity, ss.enrolled
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            JOIN schedule_sections ss ON ss.id = e.section_id
            WHERE e.student_id = :sid
              AND e.semester = :sem
              AND e.status = 'active'
              AND c.id = :bottleneck_course_id
        """),
        {"sid": STUDENT_ID, "sem": CURRENT_SEMESTER, "bottleneck_course_id": BOTTLENECK_COURSE_ID},
    ).one()

    fill_rate = round(bottleneck_row.enrolled / bottleneck_row.capacity, 4) if bottleneck_row.capacity else 0.0
    pct = int(fill_rate * 100)

    bottleneck_course = {
        "course_code": bottleneck_row.course_code,
        "course_name": bottleneck_row.course_name,
        "section_capacity": int(bottleneck_row.capacity),
        "section_enrolled": int(bottleneck_row.enrolled),
        "fill_rate": fill_rate,
        "constraint_type": "institutional",
        "constraint_note": (
            f"Section at {pct}% capacity — limited seat availability delays graduation timeline"
        ),
    }

    # --- cohort delay forecast: students behind in same program ---
    delay_row = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_cohort,
                COUNT(*) FILTER (WHERE on_track = false) AS students_at_risk
            FROM student_course_progress scp
            JOIN students s ON s.id = scp.student_id
            WHERE s.program_id = (
                SELECT program_id FROM students WHERE id = :sid
            )
        """),
        {"sid": STUDENT_ID},
    ).one()

    cohort_delay_forecast = {
        "students_at_risk": int(delay_row.students_at_risk or 0),
        "total_cohort": int(delay_row.total_cohort or 0),
    }

    # --- below-target SLO signal for bottleneck course ---
    slo_signal_row = db.execute(
        text("""
            SELECT sl.code, sl.description, h.proficiency_rate, h.cohort_size
            FROM cohort_slo_history h
            JOIN slos sl ON sl.id = h.slo_id
            WHERE h.course_id = :course_id
              AND h.semester = :sem
            ORDER BY h.proficiency_rate ASC
            LIMIT 1
        """),
        {"course_id": BOTTLENECK_COURSE_ID, "sem": CURRENT_SEMESTER},
    ).fetchone()

    bottleneck_slo_signal = None
    if slo_signal_row:
        rate = float(slo_signal_row.proficiency_rate)
        bottleneck_slo_signal = {
            "slo_code": slo_signal_row.code,
            "description": slo_signal_row.description,
            "proficiency_rate": rate,
            "cohort_size": int(slo_signal_row.cohort_size),
            "target_rate": SLO_TARGET_RATE,
            "below_target": rate < SLO_TARGET_RATE,
        }

    # --- AI graduation risk summary ---
    evidence_output = build_evidence(
        {
            "sis_data": {
                "gpa": float(student_row.gpa),
                "credits_earned": int(progress_row.credits_earned),
                "credits_required": reqs.get("total_credits", 132),
                "on_track": False,
            },
            "historical_matches": 7,
        }
    )

    graduation_risk_summary = {
        "actions": [
            {
                "type": "credit_deficit_plan",
                "description": "Develop a revised four-year plan addressing the 12-credit deficit through summer enrollment or credit overload",
                "priority": "high",
            },
            {
                "type": "bottleneck_course_priority",
                "description": "Prioritize CS302 Operating Systems enrollment next semester before section capacity reaches limit",
                "priority": "high",
            },
            {
                "type": "internship_planning",
                "description": "Begin internship placement process to complete the 240-hour requirement ahead of projected graduation",
                "priority": "medium",
            },
        ],
        "confidence": evidence_output.confidence,
        "rationale": evidence_output.rationale,
    }

    # --- seeded plan update workflow item ---
    plan_item_row = db.execute(
        text("""
            SELECT id, trigger, owner_name, owner_role, status, created_date
            FROM workflow_items
            WHERE student_id = :sid
              AND stage = 'graduation_planning'
              AND workflow_type = 'academic_plan_update'
            ORDER BY created_date DESC
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()

    plan_update_item = (
        {
            "id": plan_item_row.id,
            "trigger": plan_item_row.trigger,
            "owner_name": plan_item_row.owner_name,
            "owner_role": plan_item_row.owner_role,
            "status": plan_item_row.status,
            "created_date": str(plan_item_row.created_date),
        }
        if plan_item_row
        else None
    )

    return {
        "stage_summary": {
            "health": _progression_health(at_risk_count, on_track_count + at_risk_count),
            "on_track_count": on_track_count,
            "at_risk_count": at_risk_count,
        },
        "student": {
            "id": student_row.id,
            "name": student_row.name,
            "program_name": student_row.program_name,
            "year_level": student_row.year_level,
            "gpa": float(student_row.gpa),
        },
        "credit_map": credit_map,
        "bottleneck_course": bottleneck_course,
        "cohort_delay_forecast": cohort_delay_forecast,
        "bottleneck_slo_signal": bottleneck_slo_signal,
        "graduation_risk_summary": graduation_risk_summary,
        "plan_update_item": plan_update_item,
    }
