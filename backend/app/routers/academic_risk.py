from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.evidence import build_evidence
from app.status import StatusCode

router = APIRouter(prefix="/api/academic-risk", tags=["academic-risk"])

STUDENT_ID = "stu-003"
CURRENT_SEMESTER = "2024-Fall"


def _academic_risk_health(urgent: int, needs_attention: int, watch: int) -> str:
    if urgent > 0:
        return StatusCode.urgent
    if needs_attention > 0:
        return StatusCode.needs_attention
    if watch > 0:
        return StatusCode.watch
    return StatusCode.on_track


def _academic_failure_risk(gpa: float) -> str:
    if gpa < 2.0:
        return StatusCode.urgent
    if gpa < 2.5:
        return StatusCode.needs_attention
    return StatusCode.watch


def _attrition_risk(avg_login: float, avg_submission: float) -> str:
    if avg_login < 5 and avg_submission < 0.5:
        return StatusCode.urgent
    if avg_login < 10 or avg_submission < 0.7:
        return StatusCode.needs_attention
    return StatusCode.watch


@router.get("/profile")
def academic_risk_profile(db: Session = Depends(get_db)):
    # --- stage summary: count students by worst LMS risk flag ---
    counts_row = db.execute(
        text("""
            WITH student_worst AS (
                SELECT student_id,
                    CASE
                        WHEN bool_or(risk_flag = 'high')   THEN 'urgent'
                        WHEN bool_or(risk_flag = 'medium') THEN 'needs_attention'
                        WHEN bool_or(risk_flag = 'low')    THEN 'watch'
                        ELSE NULL
                    END AS risk_level
                FROM lms_signals
                WHERE risk_flag != 'none'
                GROUP BY student_id
            )
            SELECT
                COUNT(*) FILTER (WHERE risk_level = 'urgent')           AS urgent_count,
                COUNT(*) FILTER (WHERE risk_level = 'needs_attention')  AS needs_attention_count,
                COUNT(*) FILTER (WHERE risk_level = 'watch')            AS watch_count
            FROM student_worst
            WHERE risk_level IS NOT NULL
        """)
    ).one()

    urgent_count = int(counts_row.urgent_count or 0)
    needs_attention_count = int(counts_row.needs_attention_count or 0)
    watch_count = int(counts_row.watch_count or 0)

    # --- student profile ---
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

    # --- LMS signals for Fahad ---
    lms_rows = db.execute(
        text("""
            SELECT login_count_last_30_days, assignment_submission_rate,
                   avg_quiz_score, risk_flag
            FROM lms_signals
            WHERE student_id = :sid AND semester = :sem
        """),
        {"sid": STUDENT_ID, "sem": CURRENT_SEMESTER},
    ).fetchall()

    avg_login = (
        sum(r.login_count_last_30_days for r in lms_rows) / len(lms_rows)
        if lms_rows else 0.0
    )
    avg_submission = (
        sum(r.assignment_submission_rate for r in lms_rows) / len(lms_rows)
        if lms_rows else 0.0
    )

    # --- risk indicators ---
    failure_risk = _academic_failure_risk(float(student_row.gpa))
    dropout_risk = _attrition_risk(avg_login, avg_submission)

    # --- cohort SLO pattern: Fahad's failing SLOs with cohort context ---
    slo_pattern_rows = db.execute(
        text("""
            SELECT s.code, s.description, r.score, r.proficient,
                   ROUND(h.cohort_size * (1.0 - h.proficiency_rate))::int
                       AS peers_underperforming,
                   h.cohort_size
            FROM student_slo_results r
            JOIN slos s ON s.id = r.slo_id
            JOIN cohort_slo_history h
                ON h.slo_id = r.slo_id
               AND h.semester = r.semester
               AND h.course_id = r.course_id
            WHERE r.student_id = :sid
              AND r.proficient = false
              AND r.semester = :sem
            ORDER BY s.code
        """),
        {"sid": STUDENT_ID, "sem": CURRENT_SEMESTER},
    ).fetchall()

    cohort_slo_pattern = [
        {
            "slo_code": row.code,
            "description": row.description,
            "student_score": float(row.score),
            "proficient": bool(row.proficient),
            "peers_underperforming": int(row.peers_underperforming or 0),
            "cohort_size": int(row.cohort_size),
        }
        for row in slo_pattern_rows
    ]

    # --- AI-generated intervention plan via evidence builder ---
    lms_signals_for_evidence = [
        {
            "risk_flag": r.risk_flag,
            "avg_quiz_score": float(r.avg_quiz_score),
            "assignment_submission_rate": float(r.assignment_submission_rate),
        }
        for r in lms_rows
    ]
    evidence_output = build_evidence(
        {
            "lms_data": lms_signals_for_evidence,
            "sis_data": {"gpa": float(student_row.gpa)},
            "historical_matches": 6,
            "slo_results": cohort_slo_pattern,
        }
    )

    intervention_plan = {
        "actions": [
            {
                "type": "tutoring_referral",
                "description": "Refer Fahad to peer tutoring for CS201 data structures and algorithms",
                "priority": "high",
            },
            {
                "type": "advisor_meeting",
                "description": "Schedule weekly faculty advisor check-in for the remainder of the semester",
                "priority": "high",
            },
            {
                "type": "lms_engagement_alert",
                "description": "Enable LMS automated engagement alerts for Fahad's three active courses",
                "priority": "medium",
            },
        ],
        "confidence": evidence_output.confidence,
        "rationale": evidence_output.rationale,
    }

    # --- sponsor escalation (seeded workflow item, auto-triggered at threshold) ---
    escalation_row = db.execute(
        text("""
            SELECT id, trigger, owner_name, owner_role, status, created_date
            FROM workflow_items
            WHERE student_id = :sid
              AND stage = 'academic_progress'
              AND workflow_type = 'intervention_approval'
            ORDER BY created_date DESC
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()

    sponsor_escalation = (
        {
            "id": escalation_row.id,
            "trigger": escalation_row.trigger,
            "owner_name": escalation_row.owner_name,
            "owner_role": escalation_row.owner_role,
            "status": escalation_row.status,
            "created_date": str(escalation_row.created_date),
        }
        if escalation_row
        else None
    )

    return {
        "stage_summary": {
            "health": _academic_risk_health(urgent_count, needs_attention_count, watch_count),
            "watch_count": watch_count,
            "needs_attention_count": needs_attention_count,
            "urgent_count": urgent_count,
        },
        "student": {
            "id": student_row.id,
            "name": student_row.name,
            "program_name": student_row.program_name,
            "year_level": student_row.year_level,
            "gpa": float(student_row.gpa),
            "academic_failure_risk": failure_risk,
            "attrition_risk": dropout_risk,
        },
        "cohort_slo_pattern": cohort_slo_pattern,
        "intervention_plan": intervention_plan,
        "sponsor_escalation": sponsor_escalation,
    }
