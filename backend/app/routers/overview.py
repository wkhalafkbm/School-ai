from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.gpa_trends import gpa_trend_flagged, gpa_trend_queue_rows
from app.stages import Stage
from app.status import StatusCode, status_meta

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _sql_counter(sql: str) -> Callable[[Session], int]:
    """A counter backed by a single scalar query — the shape most KPIs take."""
    def count(db: Session) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    return count


# One counter per KPI, shared by the cards endpoint and the drill-down's total,
# so the number on a card and the panel explaining it can never disagree.
#
# Most counters are a scalar query. at_risk_detected_early is not: its population
# comes from a rule that reads a whole term series, and restating that rule in
# SQL is exactly how the card would start disagreeing with the drill-down rows
# beside it — those rows need the rule's tier and reason string regardless. So
# the counter calls the rule, the same way the priority queue below does.
METRIC_COUNTERS: dict[str, Callable[[Session], int]] = {
    "students_needing_attention": _sql_counter(
        "SELECT COUNT(DISTINCT student_id) FROM lms_signals WHERE risk_flag != 'none'"
    ),
    "at_risk_detected_early": lambda db: len(gpa_trend_flagged(db)),
    "registration_issues_resolved": _sql_counter("""
        SELECT COUNT(*) FROM workflow_items
        WHERE workflow_type = 'registration_resolution'
          AND status = 'approved'
    """),
    "graduation_delays_prevented": _sql_counter(
        "SELECT COUNT(*) FROM interventions WHERE status = 'completed'"
    ),
    "faculty_overload_alerts": _sql_counter("""
        SELECT COUNT(*) FROM faculty
        WHERE max_credits IS NOT NULL
          AND current_credits IS NOT NULL
          AND current_credits >= max_credits
    """),
}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    return {key: counter(db) for key, counter in METRIC_COUNTERS.items()}


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


def _program_names(db: Session, student_ids: list[str]) -> dict[str, str | None]:
    """Programme name per student — the context column, looked up for the capped rows only."""
    if not student_ids:
        return {}

    rows = db.execute(
        text("""
            SELECT s.id, p.name AS program_name
            FROM students s
            LEFT JOIN programs p ON p.id = s.program_id
            WHERE s.id = ANY(:ids)
        """),
        {"ids": student_ids},
    ).fetchall()

    return {r.id: r.program_name for r in rows}


def _at_risk_detected_early_rows(db: Session) -> list[dict]:
    # The rule owns the tier and the reason; this function only ranks its verdicts
    # and dresses them for the panel. Ordering and the cap have to happen here
    # rather than in SQL, because the tier being sorted on does not exist until
    # the rule has read the whole term series.
    flagged = sorted(
        gpa_trend_flagged(db),
        key=lambda row: (
            -status_meta[StatusCode(row["status"])]["severity_rank"],
            row["student_name"],
        ),
    )[:DRILL_DOWN_ROW_CAP]

    programs = _program_names(db, [row["student_id"] for row in flagged])

    return [
        {
            "id": row["student_id"],
            "name": row["student_name"],
            "context": programs.get(row["student_id"]),
            "status": row["status"],
            "detail": row["reason"],
        }
        for row in flagged
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
            "Students whose GPA is trending downward — a sharp term-over-term drop "
            "or a sustained slide across three terms. Caught by the trajectory, "
            "which turns before the absolute number does."
        ),
        "destination": {"label": "Academic Risk", "href": "/academic-risk"},
        "empty_message": "No student shows a downward GPA trend right now.",
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

    return {
        "metric_key": metric_key,
        "definition": meta["definition"],
        "destination": meta["destination"],
        "empty_message": meta["empty_message"],
        "total": METRIC_COUNTERS[metric_key](db),
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
    # admissions: ratio of incomplete onboarding tasks
    row = db.execute(
        text("SELECT COUNT(*) FILTER (WHERE NOT completed), COUNT(*) FROM onboarding_tasks")
    ).one()
    admissions_status = _classify(row[0] / row[1] if row[1] else 0)

    # enrollment: ratio of open registration_resolution items
    row = db.execute(
        text("""
            SELECT COUNT(*) FILTER (WHERE status != 'approved'), COUNT(*)
            FROM workflow_items
            WHERE workflow_type = 'registration_resolution'
        """)
    ).one()
    enrollment_status = _classify(row[0] / row[1] if row[1] else 0)

    # academic_risk: ratio of students with lms risk_flag != 'none'
    row = db.execute(
        text("""
            SELECT COUNT(DISTINCT student_id) FILTER (WHERE risk_flag != 'none'),
                   COUNT(DISTINCT student_id)
            FROM lms_signals
        """)
    ).one()
    academic_status = _classify(row[0] / row[1] if row[1] else 0)

    # progression: ratio of students NOT on track
    row = db.execute(
        text("""
            SELECT COUNT(*) FILTER (WHERE NOT on_track), COUNT(*)
            FROM student_course_progress
        """)
    ).one()
    progression_status = _classify(row[0] / row[1] if row[1] else 0)

    # career_alumni: ratio of pathways NOT in a positive state
    row = db.execute(
        text("""
            SELECT COUNT(*) FILTER (WHERE status NOT IN ('employed', 'active_search')),
                   COUNT(*)
            FROM career_pathways
        """)
    ).one()
    career_status = _classify(row[0] / row[1] if row[1] else 0)

    return {
        Stage.admissions: admissions_status,
        Stage.enrollment: enrollment_status,
        Stage.academic_risk: academic_status,
        Stage.progression: progression_status,
        Stage.career_alumni: career_status,
    }


QUEUE_ROW_CAP = 20


def _persisted_queue_rows(db: Session) -> list[dict]:
    """
    Queue rows for the signals a student's records state outright: an open LMS
    risk flag, a credit shortfall, an unfinished onboarding task. Each source
    carries a fixed severity, so the tier is a constant in the SELECT.
    """
    rows = db.execute(
        text("""
            SELECT
                s.id AS student_id,
                s.name AS student_name,
                'academic_risk' AS stage,
                'urgent' AS status,
                'LMS risk flag raised' AS reason
            FROM students s
            JOIN lms_signals l ON l.student_id = s.id
            WHERE l.risk_flag != 'none'

            UNION ALL

            SELECT
                s.id,
                s.name,
                'progression',
                'needs_attention',
                'Behind on credits — not on track for graduation'
            FROM students s
            JOIN student_course_progress scp ON scp.student_id = s.id
            WHERE NOT scp.on_track

            UNION ALL

            SELECT
                s.id,
                s.name,
                'admissions',
                'watch',
                'Incomplete onboarding tasks'
            FROM students s
            JOIN onboarding_tasks ot ON ot.student_id = s.id
            WHERE NOT ot.completed
        """)
    ).fetchall()

    return [
        {
            "student_id": r.student_id,
            "student_name": r.student_name,
            "stage": r.stage,
            "status": r.status,
            "reason": r.reason,
        }
        for r in rows
    ]


@router.get("/priority-queue")
def priority_queue(db: Session = Depends(get_db)):
    # The GPA-trend source can't be an arm of the UNION above: its tier comes
    # from a rule that reads a whole term series, and reimplementing that in SQL
    # is exactly how the queue would start disagreeing with the Academic Risk
    # panel. So it is computed on read and merged here instead.
    #
    # Trend rows lead, which makes them win ties below: where a student is
    # equally urgent for two reasons, "GPA declined 1.90 → 1.40 in 2024-Fall"
    # tells an advisor what to do next and "LMS risk flag raised" does not.
    rows = gpa_trend_queue_rows(db) + _persisted_queue_rows(db)

    # Every source speaks the same status vocabulary, so severity_rank orders a
    # row from any one of them against a row from any other. The sort is stable,
    # which is what keeps the tie-break above intact.
    rows.sort(
        key=lambda row: status_meta[StatusCode(row["status"])]["severity_rank"],
        reverse=True,
    )

    # One row per student — the advisor needs the worst thing about a student,
    # not every true thing. The sort above already put that row first.
    queue: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        if row["student_id"] in seen:
            continue
        seen.add(row["student_id"])
        queue.append(row)

    return queue[:QUEUE_ROW_CAP]


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
