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

Issue #99 adds Agent 10's narration. The agent does none of the arithmetic:
one read tool (``/api/programs/{id}/outcome-attainment``) hands it the chain
and the flags above, and the profile streams its paragraph in as ``diagnosis``,
with a canned paragraph standing in for scripted mode and for any failure.
"""

import asyncio
from itertools import combinations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.gateway import fallback, iam, orchestrate
from app.gateway.config import get_agent_id
from app.outcomes import compute_attainment, load_program_outcomes
from app.stages import Stage
from app.status import StatusCode, status_meta
from app.streaming import ResolverFn, resolve_or_fallback, set_nested, stream_profile

router = APIRouter(prefix="/api/academic-quality", tags=["academic-quality"])

# The read tool Agent 10 calls (#99). It lives under /api/programs like the
# other program-level read tools, but the arithmetic is this module's.
tool_router = APIRouter(prefix="/api/programs", tags=["programs"])

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
    feeds = _plos_fed_by_slo()
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
                    "feeds_plos": feeds.get(high.slo_code, []),
                }
            )
    return flags


def _plos_fed_by_slo() -> dict[str, list[str]]:
    """SLO code → the PLO codes it feeds, from the outcomes config."""
    feeds: dict[str, list[str]] = {}
    for plo in load_program_outcomes()["plos"]:
        for code in plo["slo_codes"]:
            feeds.setdefault(code, []).append(plo["code"])
    return feeds


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


def _program_course_ids(db: Session, program_id: str) -> set[str]:
    rows = db.execute(
        text("SELECT id FROM courses WHERE program_id = :program_id"), {"program_id": program_id}
    ).fetchall()
    return {row.id for row in rows}


@tool_router.get(
    "/{program_id}/outcome-attainment",
    summary="Get program outcome attainment and marking variance flags",
    description=(
        "Returns the program's learning outcome (PLO) attainment chain against its "
        "target — each PLO with its attainment rate, the courses feeding it and each "
        "course's SLO rates — plus any marking variance flags: pairs of sections of one "
        "course whose proficiency on the same SLO in the same semester differ by the "
        "moderation threshold or more, with both sections' instructors and rates, the "
        "gap in points, the PLOs the flagged SLO feeds, and whether the flag has already "
        "been routed for moderation."
    ),
)
def get_outcome_attainment(program_id: str, db: Session = Depends(get_db)):
    outcomes = load_program_outcomes()
    if program_id != outcomes["program_id"]:
        known = db.execute(
            text("SELECT 1 FROM programs WHERE id = :program_id"), {"program_id": program_id}
        ).first()
        if known is None:
            raise HTTPException(status_code=404, detail="Program not found")
        raise HTTPException(status_code=404, detail="No outcome attainment configured for program")
    course_ids = _program_course_ids(db, program_id)
    attainment = program_attainment(db)
    attainment["moderation_variance_flags"] = [
        flag for flag in moderation_variance_flags(db) if flag["course_id"] in course_ids
    ]
    return attainment


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


async def _live_diagnosis(payload: str) -> str | None:
    """Ask Agent 10 to narrate; None means the caller should fall back."""
    try:
        agent_id = get_agent_id("academic_quality")
        token = await iam.get_token()
        run_id = await orchestrate.start_run(agent_id, token, payload)
        run = await orchestrate.poll_run(agent_id, run_id, token)
    except (HTTPException, KeyError, httpx.HTTPError):
        return None
    if run["status"] != "completed":
        return None
    return run["output"]["result"]


def diagnosis_request(attainment: dict, flags: list[dict]) -> str:
    """
    The plain-sentence brief Agent 10 receives. It carries the ids the agent's
    tools take and the names the narration has to use; the numbers themselves
    come back through the tools, never from here.
    """
    program = attainment["program_name"]
    lines = [
        f"The program_id is {attainment['program_id']} ({program}). "
        f"Read its outcome attainment and marking variance flags with your tool, "
        f"then narrate the quality diagnosis for the programme quality lead in one short paragraph."
    ]
    if not flags:
        lines.append(
            "No marking variance is flagged this semester; explain which PLOs sit below "
            "target and which course SLO the lead should look at first."
        )
    for flag in flags:
        sections = " and ".join(
            f"{s['section_code']} ({s['instructor_name'] or 'unassigned instructor'})"
            for s in flag["sections"]
        )
        plos = ", ".join(flag["feeds_plos"]) or "no configured PLO"
        lines.append(
            f"The flagged course is {flag['course_code']} (course_id {flag['course_id']}), "
            f"SLO {flag['slo_code']}, semester {flag['semester']}, between sections {sections}; "
            f"that SLO feeds {plos}. Explain why this SLO matters for its PLO, whether the "
            f"section gap looks like marking inconsistency or a genuine cohort difference, and "
            f"what to moderate first. Name the course, the SLO and both sections."
        )
    return " ".join(lines)


def _build_profile(db: Session) -> tuple[dict, dict[str, ResolverFn]]:
    flags = moderation_variance_flags(db)
    attainment = program_attainment(db)
    canned_diagnosis = fallback.get(Stage.academic_quality)["result"]
    request = diagnosis_request(attainment, flags)
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
        # Agent 10's narration (#99). The canned paragraph is what the page
        # shows until the agent answers, and what it keeps if the agent cannot.
        "diagnosis": canned_diagnosis,
    }

    async def resolve_diagnosis() -> str:
        return await resolve_or_fallback(canned_diagnosis, lambda: _live_diagnosis(request))

    resolvers: dict[str, ResolverFn] = {"diagnosis": resolve_diagnosis}
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
