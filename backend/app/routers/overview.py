from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.status import StatusCode, status_meta

router = APIRouter(prefix="/api/overview", tags=["overview"])


# One count query per KPI, shared by the cards endpoint and the drill-down's
# total, so the number on a card and the panel explaining it can never disagree.
METRIC_COUNT_SQL: dict[str, str] = {
    "students_needing_attention": (
        "SELECT COUNT(DISTINCT student_id) FROM lms_signals WHERE risk_flag != 'none'"
    ),
    "at_risk_detected_early": """
        SELECT COUNT(*) FROM students s
        WHERE s.gpa < 2.5
          AND NOT EXISTS (
              SELECT 1 FROM support_cases sc
              WHERE sc.student_id = s.id
                AND sc.status != 'closed'
          )
    """,
    "registration_issues_resolved": """
        SELECT COUNT(*) FROM workflow_items
        WHERE workflow_type = 'registration_resolution'
          AND status = 'approved'
    """,
    "graduation_delays_prevented": (
        "SELECT COUNT(*) FROM interventions WHERE status = 'completed'"
    ),
    "faculty_overload_alerts": """
        SELECT COUNT(*) FROM faculty
        WHERE max_credits IS NOT NULL
          AND current_credits IS NOT NULL
          AND current_credits >= max_credits
    """,
}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    return {
        key: int(db.execute(text(sql)).scalar() or 0)
        for key, sql in METRIC_COUNT_SQL.items()
    }


# The panel shows the six that matter most. Capped in the query, not in the
# panel, so the payload never carries rows nobody can see.
DRILL_DOWN_ROW_CAP = 6


def _students_needing_attention_rows(db: Session) -> list[dict]:
    rows = db.execute(
        text("""
            WITH student_worst AS (
                SELECT student_id,
                    CASE
                        WHEN bool_or(risk_flag = 'high')   THEN 'urgent'
                        WHEN bool_or(risk_flag = 'medium') THEN 'needs_attention'
                        WHEN bool_or(risk_flag = 'low')    THEN 'watch'
                    END AS status,
                    CASE
                        WHEN bool_or(risk_flag = 'high')   THEN 'high'
                        WHEN bool_or(risk_flag = 'medium') THEN 'medium'
                        WHEN bool_or(risk_flag = 'low')    THEN 'low'
                    END AS worst_flag
                FROM lms_signals
                WHERE risk_flag != 'none'
                GROUP BY student_id
            )
            SELECT s.id, s.name, p.name AS program_name, w.status, w.worst_flag
            FROM student_worst w
            JOIN students s ON s.id = w.student_id
            LEFT JOIN programs p ON p.id = s.program_id
            ORDER BY
                CASE w.status
                    WHEN 'urgent'          THEN 0
                    WHEN 'needs_attention' THEN 1
                    WHEN 'watch'           THEN 2
                    WHEN 'on_track'        THEN 3
                    ELSE 4
                END,
                s.name
            LIMIT :cap
        """),
        {"cap": DRILL_DOWN_ROW_CAP},
    ).fetchall()

    return [
        {
            "id": r.id,
            "name": r.name,
            "context": r.program_name,
            "status": r.status,
            "detail": f"Risk flag: {r.worst_flag}",
        }
        for r in rows
    ]


def _at_risk_detected_early_rows(db: Session) -> list[dict]:
    # Every row here is uniformly 'watch' — these students were caught before
    # anyone raised a case — so severity ordering falls through to GPA, worst first.
    rows = db.execute(
        text("""
            SELECT s.id, s.name, p.name AS program_name, s.gpa
            FROM students s
            LEFT JOIN programs p ON p.id = s.program_id
            WHERE s.gpa < 2.5
              AND NOT EXISTS (
                  SELECT 1 FROM support_cases sc
                  WHERE sc.student_id = s.id
                    AND sc.status != 'closed'
              )
            ORDER BY s.gpa, s.name
            LIMIT :cap
        """),
        {"cap": DRILL_DOWN_ROW_CAP},
    ).fetchall()

    return [
        {
            "id": r.id,
            "name": r.name,
            "context": r.program_name,
            "status": StatusCode.watch,
            "detail": f"GPA {r.gpa:.1f} — no open support case",
        }
        for r in rows
    ]


def _registration_issues_resolved_rows(db: Session) -> list[dict]:
    # An achievement metric: every row is a cleared blocker, uniformly positive.
    rows = db.execute(
        text("""
            SELECT w.id, s.name, p.name AS program_name, w.trigger
            FROM workflow_items w
            LEFT JOIN students s ON s.id = w.student_id
            LEFT JOIN programs p ON p.id = s.program_id
            WHERE w.workflow_type = 'registration_resolution'
              AND w.status = 'approved'
            ORDER BY s.name, w.id
            LIMIT :cap
        """),
        {"cap": DRILL_DOWN_ROW_CAP},
    ).fetchall()

    return [
        {
            "id": r.id,
            "name": r.name,
            "context": r.program_name,
            "status": StatusCode.on_track,
            "detail": f"Resolved: {r.trigger}",
        }
        for r in rows
    ]


def _graduation_delays_prevented_rows(db: Session) -> list[dict]:
    # An achievement metric: every row is a completed intervention, uniformly positive.
    rows = db.execute(
        text("""
            SELECT i.id, s.name, p.name AS program_name, i.intervention_type
            FROM interventions i
            JOIN students s ON s.id = i.student_id
            LEFT JOIN programs p ON p.id = s.program_id
            WHERE i.status = 'completed'
            ORDER BY s.name, i.id
            LIMIT :cap
        """),
        {"cap": DRILL_DOWN_ROW_CAP},
    ).fetchall()

    return [
        {
            "id": r.id,
            "name": r.name,
            "context": r.program_name,
            "status": StatusCode.on_track,
            "detail": (r.intervention_type or "intervention").replace("_", " ").capitalize(),
        }
        for r in rows
    ]


def _faculty_overload_alerts_rows(db: Session) -> list[dict]:
    # Rows are faculty, so the context column carries department, not programme.
    rows = db.execute(
        text("""
            SELECT id, name, department, current_credits, max_credits
            FROM faculty
            WHERE max_credits IS NOT NULL
              AND current_credits IS NOT NULL
              AND current_credits >= max_credits
            ORDER BY current_credits - max_credits DESC, name
            LIMIT :cap
        """),
        {"cap": DRILL_DOWN_ROW_CAP},
    ).fetchall()

    return [
        {
            "id": r.id,
            "name": r.name,
            "context": r.department,
            "status": (
                StatusCode.urgent
                if r.current_credits > r.max_credits
                else StatusCode.needs_attention
            ),
            "detail": f"{r.current_credits} of {r.max_credits} credits",
        }
        for r in rows
    ]


METRIC_DETAIL_META: dict[str, dict] = {
    "students_needing_attention": {
        "definition": (
            "Students carrying at least one open LMS risk flag — counted once each, "
            "however many flags they hold."
        ),
        "destination": {"label": "Academic Risk", "href": "/academic-risk"},
        "empty_message": "No student is carrying an LMS risk flag right now.",
        "rows": _students_needing_attention_rows,
    },
    "at_risk_detected_early": {
        "definition": (
            "Students below a 2.5 GPA with no open support case — surfaced by the "
            "platform before anyone raised a case for them."
        ),
        "destination": {"label": "Academic Risk", "href": "/academic-risk"},
        "empty_message": "Every student below a 2.5 GPA already has an open support case.",
        "rows": _at_risk_detected_early_rows,
    },
    "registration_issues_resolved": {
        "definition": (
            "Registration-resolution items approved this term — each one a "
            "registration blocker cleared for a student."
        ),
        "destination": {"label": "Workflow Activity", "href": "/workflow-activity"},
        "empty_message": "No registration issue has been resolved yet this term.",
        "rows": _registration_issues_resolved_rows,
    },
    "graduation_delays_prevented": {
        "definition": (
            "Interventions completed this term — each one closed out before it "
            "could push a graduation date back."
        ),
        "destination": {"label": "Progression", "href": "/progression"},
        "empty_message": "No intervention has been completed yet this term.",
        "rows": _graduation_delays_prevented_rows,
    },
    "faculty_overload_alerts": {
        "definition": (
            "Faculty members teaching at or above their credit ceiling this semester."
        ),
        "destination": {"label": "Teaching Readiness", "href": "/teaching-readiness"},
        "empty_message": "No faculty member is at or over their credit ceiling.",
        "rows": _faculty_overload_alerts_rows,
    },
}


@router.get("/metrics/{metric_key}/detail")
def metric_detail(metric_key: str, db: Session = Depends(get_db)):
    meta = METRIC_DETAIL_META.get(metric_key)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"No drill-down for metric {metric_key!r}")

    total = db.execute(text(METRIC_COUNT_SQL[metric_key])).scalar() or 0

    return {
        "metric_key": metric_key,
        "definition": meta["definition"],
        "destination": meta["destination"],
        "empty_message": meta["empty_message"],
        "total": int(total),
        "rows": meta["rows"](db),
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
            SELECT student_id, student_name, stage, status, reason
            FROM ranked
            ORDER BY rank DESC
            LIMIT 20
        """)
    ).fetchall()

    return [
        {
            "student_id": r[0],
            "student_name": r[1],
            "stage": r[2],
            "status": r[3],
            "reason": r[4],
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
