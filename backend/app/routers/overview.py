from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.status import StatusCode, status_meta

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    students_needing_attention = db.execute(
        text("SELECT COUNT(DISTINCT student_id) FROM lms_signals WHERE risk_flag != 'none'")
    ).scalar() or 0

    at_risk_detected_early = db.execute(
        text("""
            SELECT COUNT(*) FROM students s
            WHERE s.gpa < 2.5
              AND NOT EXISTS (
                  SELECT 1 FROM support_cases sc
                  WHERE sc.student_id = s.id
                    AND sc.status != 'closed'
              )
        """)
    ).scalar() or 0

    registration_issues_resolved = db.execute(
        text("""
            SELECT COUNT(*) FROM workflow_items
            WHERE workflow_type = 'registration_resolution'
              AND status = 'approved'
        """)
    ).scalar() or 0

    graduation_delays_prevented = db.execute(
        text("SELECT COUNT(*) FROM interventions WHERE status = 'completed'")
    ).scalar() or 0

    faculty_overload_alerts = db.execute(
        text("""
            SELECT COUNT(*) FROM faculty
            WHERE max_credits IS NOT NULL
              AND current_credits IS NOT NULL
              AND current_credits >= max_credits
        """)
    ).scalar() or 0

    return {
        "students_needing_attention": int(students_needing_attention),
        "at_risk_detected_early": int(at_risk_detected_early),
        "registration_issues_resolved": int(registration_issues_resolved),
        "graduation_delays_prevented": int(graduation_delays_prevented),
        "faculty_overload_alerts": int(faculty_overload_alerts),
    }


def _classify(ratio: float) -> str:
    if ratio <= 0.05:
        return StatusCode.on_track
    if ratio <= 0.15:
        return StatusCode.watch
    if ratio <= 0.30:
        return StatusCode.needs_attention
    return StatusCode.urgent


@router.get("/journey-health")
def journey_health(db: Session = Depends(get_db)):
    # onboarding: ratio of incomplete tasks
    row = db.execute(
        text("SELECT COUNT(*) FILTER (WHERE NOT completed), COUNT(*) FROM onboarding_tasks")
    ).one()
    onboarding_status = _classify(row[0] / row[1] if row[1] else 0)

    # registration: ratio of open registration_resolution items
    row = db.execute(
        text("""
            SELECT COUNT(*) FILTER (WHERE status != 'approved'), COUNT(*)
            FROM workflow_items
            WHERE workflow_type = 'registration_resolution'
        """)
    ).one()
    registration_status = _classify(row[0] / row[1] if row[1] else 0)

    # academic_progress: ratio of students with lms risk_flag != 'none'
    row = db.execute(
        text("""
            SELECT COUNT(DISTINCT student_id) FILTER (WHERE risk_flag != 'none'),
                   COUNT(DISTINCT student_id)
            FROM lms_signals
        """)
    ).one()
    academic_status = _classify(row[0] / row[1] if row[1] else 0)

    # graduation_planning: ratio of students NOT on track
    row = db.execute(
        text("""
            SELECT COUNT(*) FILTER (WHERE NOT on_track), COUNT(*)
            FROM student_course_progress
        """)
    ).one()
    graduation_status = _classify(row[0] / row[1] if row[1] else 0)

    # career: ratio of pathways NOT in a positive state
    row = db.execute(
        text("""
            SELECT COUNT(*) FILTER (WHERE status NOT IN ('employed', 'active_search')),
                   COUNT(*)
            FROM career_pathways
        """)
    ).one()
    career_status = _classify(row[0] / row[1] if row[1] else 0)

    return {
        "onboarding": onboarding_status,
        "registration": registration_status,
        "academic_progress": academic_status,
        "graduation_planning": graduation_status,
        "career": career_status,
    }


@router.get("/priority-queue")
def priority_queue(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            WITH signals AS (
                SELECT
                    s.id AS student_id,
                    s.name AS student_name,
                    'academic_progress' AS stage,
                    'urgent' AS status,
                    'LMS risk flag raised' AS reason,
                    4 AS rank
                FROM students s
                JOIN lms_signals l ON l.student_id = s.id
                WHERE l.risk_flag != 'none'

                UNION ALL

                SELECT
                    s.id,
                    s.name,
                    'graduation_planning',
                    'needs_attention',
                    'Behind on credits — not on track for graduation',
                    3
                FROM students s
                JOIN student_course_progress scp ON scp.student_id = s.id
                WHERE NOT scp.on_track

                UNION ALL

                SELECT
                    s.id,
                    s.name,
                    'onboarding',
                    'watch',
                    'Incomplete onboarding tasks',
                    2
                FROM students s
                JOIN onboarding_tasks ot ON ot.student_id = s.id
                WHERE NOT ot.completed
            ),
            ranked AS (
                SELECT DISTINCT ON (student_id)
                    student_id, student_name, stage, status, reason, rank
                FROM signals
                ORDER BY student_id, rank DESC
            )
            SELECT student_name, stage, status, reason
            FROM ranked
            ORDER BY rank DESC
            LIMIT 20
        """)
    ).fetchall()

    return [
        {
            "student_name": r[0],
            "stage": r[1],
            "status": r[2],
            "reason": r[3],
        }
        for r in rows
    ]


@router.get("/chart-data")
def chart_data(db: Session = Depends(get_db)):
    enrollment_rows = db.execute(
        text("""
            SELECT semester, COUNT(*) AS count
            FROM enrollments
            GROUP BY semester
            ORDER BY semester
        """)
    ).fetchall()

    gpa_rows = db.execute(
        text("""
            SELECT
                CASE
                    WHEN gpa < 2.0 THEN '<2.0'
                    WHEN gpa < 2.5 THEN '2.0-2.5'
                    WHEN gpa < 3.0 THEN '2.5-3.0'
                    WHEN gpa < 3.5 THEN '3.0-3.5'
                    ELSE '3.5-4.0'
                END AS bucket,
                COUNT(*) AS count
            FROM students
            WHERE gpa IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """)
    ).fetchall()

    intervention_rows = db.execute(
        text("""
            SELECT status, COUNT(*) AS count
            FROM interventions
            GROUP BY status
            ORDER BY status
        """)
    ).fetchall()

    lms_risk_rows = db.execute(
        text("""
            SELECT semester, COUNT(*) FILTER (WHERE risk_flag != 'none') AS at_risk, COUNT(*) AS total
            FROM lms_signals
            GROUP BY semester
            ORDER BY semester
        """)
    ).fetchall()

    return {
        "enrollments_by_semester": [
            {"semester": r[0], "count": r[1]} for r in enrollment_rows
        ],
        "gpa_distribution": [
            {"bucket": r[0], "count": r[1]} for r in gpa_rows
        ],
        "intervention_outcomes": [
            {"status": r[0], "count": r[1]} for r in intervention_rows
        ],
        "lms_risk_by_semester": [
            {"semester": r[0], "at_risk": r[1], "total": r[2]} for r in lms_risk_rows
        ],
    }
