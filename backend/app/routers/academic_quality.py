"""
Academic Quality — the home of Agent 10 (academic outcomes & quality
intelligence).

Issue #98 adds the anomaly the demo turns on: a **moderation variance** flag.
Two sections of one course assess the same SLO in the same semester; when
their proficiency rates differ by MODERATION_VARIANCE_THRESHOLD_POINTS or more,
the engine flags the pair and offers to route the evidence to a human for
moderation. Routing writes a workflow item under this stage; the profile
reports that item back against the flag so the page can show where the
Measure → Diagnose → Moderate → Validate → Act → Re-measure workflow stands.

Issue #97 adds the upward half of the deck's evidence chain: Assessment →
SLO → CLO → PLO → program effectiveness, for the program configured in
``config/program_learning_outcomes.json``. The arithmetic lives in
``app.outcomes``; this module only fetches the rows it needs.
"""

import asyncio
from itertools import combinations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.outcomes import compute_attainment, load_program_outcomes
from app.stages import Stage
from app.status import StatusCode, status_meta
from app.streaming import ResolverFn, set_nested, stream_profile

router = APIRouter(prefix="/api/academic-quality", tags=["academic-quality"])

# Two sections of one course differing on the same SLO by this many percentage
# points or more is a marking inconsistency a human has to moderate.
MODERATION_VARIANCE_THRESHOLD_POINTS = 20

MODERATION_OWNER_NAME = "Programme Quality Lead"
MODERATION_OWNER_ROLE = "programme quality lead"


def variance_trigger(course_code: str, slo_code: str, semester: str) -> str:
    """
    The trigger a routed flag's workflow item carries. The page sends this
    string back verbatim when it routes, so the profile can find the item
    again and report the flag as routed.
    """
    return f"Marking variance flagged — {course_code} {slo_code} ({semester})"


def _section_rates(db: Session) -> list:
    """Every section-level assessment, with the course, SLO and instructor it names."""
    return db.execute(
        text("""
            SELECT a.slo_id, a.semester, a.proficiency_rate,
                   a.assessed_students, a.proficient_count,
                   c.id AS course_id, c.code AS course_code, c.name AS course_name,
                   sl.code AS slo_code, sl.description AS slo_description,
                   ss.id AS section_id, ss.section_code,
                   f.id AS instructor_id, f.name AS instructor_name
            FROM slo_assessments a
            JOIN slos sl ON sl.id = a.slo_id
            JOIN courses c ON c.id = sl.course_id
            JOIN schedule_sections ss ON ss.id = a.section_id
            LEFT JOIN faculty f ON f.id = ss.instructor_id
            WHERE a.section_id IS NOT NULL
            ORDER BY c.code, sl.code, a.semester, ss.section_code
        """)
    ).fetchall()


def _routed_items(db: Session) -> dict[str, dict]:
    """Workflow items filed under this stage, keyed by trigger; latest wins."""
    rows = db.execute(
        text("""
            SELECT id, trigger, owner_name, owner_role, status, created_date
            FROM workflow_items
            WHERE stage = :stage
            ORDER BY created_date, id
        """),
        {"stage": Stage.academic_quality},
    ).fetchall()
    return {
        row.trigger: {
            "id": row.id,
            "owner_name": row.owner_name,
            "owner_role": row.owner_role,
            "status": row.status,
            "created_date": str(row.created_date),
        }
        for row in rows
    }


def _section_entry(row) -> dict:
    return {
        "section_id": row.section_id,
        "section_code": row.section_code,
        "instructor_id": row.instructor_id,
        "instructor_name": row.instructor_name,
        "proficiency_rate": float(row.proficiency_rate),
        "assessed_students": int(row.assessed_students) if row.assessed_students is not None else None,
        "proficient_count": int(row.proficient_count) if row.proficient_count is not None else None,
    }


def moderation_variance_flags(db: Session) -> list[dict]:
    """
    One flag per pair of sections of the same course whose proficiency rates
    on the same SLO in the same semester differ by the threshold or more.
    Course-level roll-ups (section null) never take part.
    """
    grouped: dict[tuple[str, str, str], list] = {}
    for row in _section_rates(db):
        grouped.setdefault((row.course_id, row.slo_id, row.semester), []).append(row)

    routed = _routed_items(db)
    flags: list[dict] = []
    for rows in grouped.values():
        for a, b in combinations(rows, 2):
            high, low = sorted((a, b), key=lambda r: -float(r.proficiency_rate))
            # Rates are stored to three decimals; rounding the gap to one
            # decimal point keeps a 0.70 / 0.50 pair from landing at 19.999.
            gap_points = round((float(high.proficiency_rate) - float(low.proficiency_rate)) * 100, 1)
            if gap_points < MODERATION_VARIANCE_THRESHOLD_POINTS:
                continue
            trigger = variance_trigger(high.course_code, high.slo_code, high.semester)
            flags.append(
                {
                    "course_id": high.course_id,
                    "course_code": high.course_code,
                    "course_name": high.course_name,
                    "slo_id": high.slo_id,
                    "slo_code": high.slo_code,
                    "slo_description": high.slo_description,
                    "semester": high.semester,
                    "sections": [_section_entry(high), _section_entry(low)],
                    "gap_points": gap_points,
                    "threshold_points": MODERATION_VARIANCE_THRESHOLD_POINTS,
                    "trigger": trigger,
                    "moderation_owner_name": MODERATION_OWNER_NAME,
                    "moderation_owner_role": MODERATION_OWNER_ROLE,
                    "routed_item": routed.get(trigger),
                }
            )
    return flags


def _program_slos(db: Session, program_id: str) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT sl.id AS slo_id, sl.code AS slo_code, sl.description,
                   c.id AS course_id, c.code AS course_code, c.name AS course_name
            FROM slos sl
            JOIN courses c ON c.id = sl.course_id
            WHERE c.program_id = :program_id
            ORDER BY c.code, sl.code
        """),
        {"program_id": program_id},
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def _program_assessments(db: Session, program_id: str) -> list[dict]:
    """
    Course-level proficiency per SLO per semester. Section-level rows never
    take part (they are the moderation flag's evidence, not the chain's); the
    cohort SLO history fills in any semester the assessment table lacks.
    """
    rows = db.execute(
        text("""
            SELECT a.slo_id, a.semester, a.proficiency_rate, a.assessed_students,
                   'assessment' AS source
            FROM slo_assessments a
            JOIN slos sl ON sl.id = a.slo_id
            JOIN courses c ON c.id = sl.course_id
            WHERE c.program_id = :program_id AND a.section_id IS NULL
            UNION ALL
            SELECT h.slo_id, h.semester, h.proficiency_rate, h.cohort_size,
                   'cohort_history' AS source
            FROM cohort_slo_history h
            JOIN slos sl ON sl.id = h.slo_id
            JOIN courses c ON c.id = sl.course_id
            WHERE c.program_id = :program_id
              AND NOT EXISTS (
                  SELECT 1 FROM slo_assessments a
                  WHERE a.slo_id = h.slo_id AND a.semester = h.semester
                    AND a.section_id IS NULL
              )
        """),
        {"program_id": program_id},
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def program_attainment(db: Session) -> dict:
    outcomes = load_program_outcomes()
    program_id = outcomes["program_id"]
    return compute_attainment(
        outcomes, _program_slos(db, program_id), _program_assessments(db, program_id)
    )


def _moderation_health(flags: list[dict]) -> StatusCode:
    if not flags:
        return StatusCode.on_track
    if any(flag["routed_item"] is None for flag in flags):
        return StatusCode.needs_attention
    return StatusCode.watch


def _attainment_health(plos_below_target: int) -> StatusCode:
    if plos_below_target == 0:
        return StatusCode.on_track
    if plos_below_target == 1:
        return StatusCode.watch
    return StatusCode.needs_attention


def _health(flags: list[dict], plos_below_target: int) -> StatusCode:
    """The header badge: whichever of the two signals is more severe."""
    return max(
        _moderation_health(flags),
        _attainment_health(plos_below_target),
        key=lambda code: status_meta[code]["severity_rank"],
    )


def _build_profile(db: Session) -> tuple[dict, dict[str, ResolverFn]]:
    flags = moderation_variance_flags(db)
    attainment = program_attainment(db)
    base = {
        "stage_summary": {
            "health": _health(flags, attainment["plos_below_target"]),
            "open_flag_count": sum(1 for f in flags if f["routed_item"] is None),
            "routed_flag_count": sum(1 for f in flags if f["routed_item"] is not None),
            "plo_count": len(attainment["plos"]),
            "plos_below_target": attainment["plos_below_target"],
            "attainment_target": attainment["attainment_target"],
        },
        "program_attainment": attainment,
        "moderation_variance_flags": flags,
    }
    resolvers: dict[str, ResolverFn] = {}
    return base, resolvers


@router.get("/profile")
async def academic_quality_profile(db: Session = Depends(get_db)):
    base, resolvers = _build_profile(db)
    paths = list(resolvers.keys())
    values = await asyncio.gather(*(resolvers[path]() for path in paths))
    for path, value in zip(paths, values):
        set_nested(base, path, value)
    return base


@router.get("/profile/stream")
async def academic_quality_profile_stream(db: Session = Depends(get_db)):
    base, resolvers = _build_profile(db)
    return StreamingResponse(stream_profile(base, resolvers), media_type="text/event-stream")
