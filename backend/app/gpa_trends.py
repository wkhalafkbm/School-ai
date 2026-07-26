"""
Population-wide GPA trend evaluation — issue #64.

The decision itself is the pure rule in app.rules; this module is only the
database plumbing around it: read every student's term series, run the rule,
and record a workflow item for each newly flagged student. No AI in this path.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import WorkflowItem
from app.rules import GPATrendResult, check_gpa_trend, gpa_trend_status
from app.status import StatusCode

MIN_TERMS = 2

STAGE = "academic_progress"
WORKFLOW_TYPE = "academic_risk_review"
OWNER_ROLE = "academic advisor"
ASSIGNED_TO = "Academic Advising"

# Severity tier → workflow item priority.
PRIORITY_BY_STATUS = {
    StatusCode.urgent: "urgent",
    StatusCode.needs_attention: "high",
    StatusCode.watch: "medium",
}


def _term_series_by_student(db: Session) -> dict[str, list[dict]]:
    """Every student's term series, chronologically ordered, keyed by student id."""
    rows = db.execute(
        text("""
            SELECT g.student_id, s.name AS student_name, g.term, g.term_index,
                   g.term_gpa, g.cumulative_gpa
            FROM student_term_gpa g
            JOIN students s ON s.id = g.student_id
            ORDER BY g.student_id, g.term_index
        """)
    ).fetchall()

    series: dict[str, list[dict]] = {}
    incomplete: set[str] = set()

    for row in rows:
        # A term whose GPA is not recorded yet cannot be compared against, and a
        # gap would make a "term-over-term" delta a lie. Skip the whole student.
        if row.term_gpa is None or row.cumulative_gpa is None:
            incomplete.add(row.student_id)
            continue
        series.setdefault(row.student_id, []).append({
            "student_name": row.student_name,
            "term": row.term,
            "term_gpa": float(row.term_gpa),
            "cumulative_gpa": float(row.cumulative_gpa),
        })

    return {
        student_id: rows
        for student_id, rows in series.items()
        if student_id not in incomplete
    }


def evaluate_gpa_trends(db: Session) -> dict:
    """
    Run the GPA trend rule across every student with at least MIN_TERMS terms
    of history. Returns {evaluated, flagged, created, skipped_existing}.
    """
    evaluated = 0
    flagged = 0
    created = 0
    skipped_existing = 0

    for student_id, series in _term_series_by_student(db).items():
        if len(series) < MIN_TERMS:
            continue
        evaluated += 1

        result = check_gpa_trend(series)
        if not result.flagged:
            continue
        flagged += 1

        latest = series[-1]
        status = gpa_trend_status(
            result,
            term_gpa=latest["term_gpa"],
            cumulative_gpa=latest["cumulative_gpa"],
        )
        trigger = f"gpa_trend:{result.term}"

        already_flagged = (
            db.query(WorkflowItem)
            .filter(
                WorkflowItem.student_id == student_id,
                WorkflowItem.trigger == trigger,
            )
            .first()
        )
        if already_flagged is not None:
            skipped_existing += 1
            continue

        db.add(_trend_item(student_id, latest, result, status, trigger))
        created += 1

    db.commit()

    return {
        "evaluated": evaluated,
        "flagged": flagged,
        "created": created,
        "skipped_existing": skipped_existing,
    }


def _trend_item(
    student_id: str,
    latest: dict,
    result: GPATrendResult,
    status: str,
    trigger: str,
) -> WorkflowItem:
    """The workflow item a flagged student earns — deterministic prose, no AI."""
    name = latest["student_name"]
    return WorkflowItem(
        id=f"wft-{student_id}-{result.term}",
        student_id=student_id,
        workflow_type=WORKFLOW_TYPE,
        stage=STAGE,
        trigger=trigger,
        title=f"GPA Trend Review — {name}",
        description=(
            f"{result.reason}. {name}'s cumulative GPA now stands at "
            f"{latest['cumulative_gpa']:.2f}. Academic advisor to review the "
            f"trend and decide whether an intervention is warranted."
        ),
        status="pending",
        priority=PRIORITY_BY_STATUS[status],
        owner_name=None,
        owner_role=OWNER_ROLE,
        assigned_to=ASSIGNED_TO,
        created_date=date.today(),
        due_date=None,
        completed_date=None,
        data_source="demo",
    )
