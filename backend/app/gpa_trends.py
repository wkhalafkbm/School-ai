"""
GPA trend evaluation — issues #64 and #65.

The decision itself is the pure rule in app.rules; this module is only the
database plumbing around it. Two entry points share that rule:

- evaluate_gpa_trends() sweeps the population and records a workflow item for
  each newly flagged student (#64).
- build_gpa_trend() reads one student's trend for display (#65), computing the
  status on read and never persisting it.

No AI in either path.
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


def _term_series(db: Session, student_id: str) -> list[dict]:
    """One student's term series, chronologically ordered."""
    rows = db.execute(
        text("""
            SELECT term, term_gpa, cumulative_gpa
            FROM student_term_gpa
            WHERE student_id = :sid
            ORDER BY term_index
        """),
        {"sid": student_id},
    ).fetchall()

    return [
        {
            "term": row.term,
            "term_gpa": None if row.term_gpa is None else float(row.term_gpa),
            "cumulative_gpa": (
                None if row.cumulative_gpa is None else float(row.cumulative_gpa)
            ),
        }
        for row in rows
    ]


def build_gpa_trend(db: Session, student_id: str) -> dict:
    """
    One student's GPA trend, computed on read for display.

    Returns the term series plus the trend verdict. Nothing here is persisted:
    the status is a fact about the GPA history, recomputed every request, so a
    completed workflow item can never suppress it.
    """
    series = _term_series(db, student_id)

    # A term with no GPA recorded yet cannot be compared against, and a gap
    # would make a term-over-term delta a lie — same call evaluate_gpa_trends
    # makes. The series still displays; only the verdict is withheld.
    unrecorded = [
        row["term"]
        for row in series
        if row["term_gpa"] is None or row["cumulative_gpa"] is None
    ]

    if unrecorded:
        result = GPATrendResult(
            flagged=False,
            rules_fired=(),
            reason=(
                f"GPA not yet recorded for {', '.join(unrecorded)} — "
                "trend not evaluated"
            ),
        )
        status = None
    elif len(series) < MIN_TERMS:
        result = check_gpa_trend(series)
        status = None
    else:
        result = check_gpa_trend(series)
        latest = series[-1]
        status = gpa_trend_status(
            result,
            term_gpa=latest["term_gpa"],
            cumulative_gpa=latest["cumulative_gpa"],
        )

    return {
        "series": series,
        "status": status,
        "reason": result.reason,
        "rules_fired": list(result.rules_fired),
        "workflow_item": _linked_workflow_item(db, student_id),
    }


def _linked_workflow_item(db: Session, student_id: str) -> dict | None:
    """
    The most recent workflow item opened by a GPA trend for this student.

    Its status answers "is anyone acting on this?" — a different question from
    the trend status above, which answers "is the GPA still falling?". The two
    are reported side by side and neither overrides the other.
    """
    row = db.execute(
        text("""
            SELECT id, status, created_date
            FROM workflow_items
            WHERE student_id = :sid
              AND trigger LIKE 'gpa_trend:%'
            ORDER BY created_date DESC
            LIMIT 1
        """),
        {"sid": student_id},
    ).fetchone()

    if row is None:
        return None
    return {
        "id": row.id,
        "status": row.status,
        "created_date": str(row.created_date),
    }


def gpa_trend_queue_rows(db: Session) -> list[dict]:
    """
    A priority-queue row for every student the trend rule currently flags (#66).

    Like build_gpa_trend, the tier is computed on read and nothing is persisted,
    so the queue and the Academic Risk trend panel read the same rule over the
    same history and cannot disagree about who is declining, or how badly.
    """
    rows = []

    for student_id, series in _term_series_by_student(db).items():
        if len(series) < MIN_TERMS:
            continue

        result = check_gpa_trend(series)
        if not result.flagged:
            continue

        latest = series[-1]
        rows.append({
            "student_id": student_id,
            "student_name": latest["student_name"],
            "stage": STAGE,
            "status": gpa_trend_status(
                result,
                term_gpa=latest["term_gpa"],
                cumulative_gpa=latest["cumulative_gpa"],
            ),
            "reason": result.reason,
        })

    return rows


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
