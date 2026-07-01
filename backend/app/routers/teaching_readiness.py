import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.gateway import iam, orchestrate
from app.gateway.config import get_agent_id
from app.status import StatusCode

router = APIRouter(prefix="/api/teaching-readiness", tags=["teaching-readiness"])

FEATURED_COURSE_ID = "crs-001"
FEATURED_COURSE_CODE = "CS101"
SEMESTERS = ["2023-Fall", "2024-Spring", "2024-Fall"]
FAILURE_THRESHOLD = 0.30
_SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}


def _sem_key(sem: str) -> tuple:
    year, season = sem.split("-")
    return (int(year), _SEASON_ORDER.get(season, 99))


def _readiness_health(overloaded_count: int, avg_score: float) -> str:
    if overloaded_count > 0:
        return StatusCode.needs_attention
    if avg_score < 60:
        return StatusCode.urgent
    if avg_score < 70:
        return StatusCode.watch
    return StatusCode.on_track


async def _live_rationale(stage: str, payload: dict) -> str | None:
    try:
        agent_id = get_agent_id(stage)
        token = await iam.get_token()
        run_id = await orchestrate.start_run(agent_id, token, payload)
        run = await orchestrate.poll_run(agent_id, run_id, token)
    except (HTTPException, KeyError, httpx.HTTPError):
        return None
    if run["status"] != "completed":
        return None
    return run["output"]["result"]


@router.get("/profile")
async def teaching_readiness_profile(db: Session = Depends(get_db)):
    # --- cohort size (students enrolled in featured course's current semester) ---
    cohort_size = db.execute(
        text("""
            SELECT COALESCE(MAX(cohort_size), 30)
            FROM cohort_slo_history
            WHERE course_id = :cid AND semester = :sem
        """),
        {"cid": FEATURED_COURSE_ID, "sem": SEMESTERS[-1]},
    ).scalar() or 30

    # --- SLO trends for featured course across 3 semesters ---
    slo_rows = db.execute(
        text("""
            SELECT s.id, s.code, s.description,
                   h.semester, h.proficiency_rate
            FROM slos s
            JOIN cohort_slo_history h ON h.slo_id = s.id
            WHERE s.course_id = :cid
              AND h.semester = ANY(:sems)
            ORDER BY s.id, h.semester
        """),
        {"cid": FEATURED_COURSE_ID, "sems": SEMESTERS},
    ).fetchall()

    slo_map: dict = {}
    for row in slo_rows:
        sid, code, desc, sem, rate = row
        if sid not in slo_map:
            slo_map[sid] = {"slo_code": code, "description": desc, "semesters": []}
        slo_map[sid]["semesters"].append(
            {"semester": sem, "proficiency_rate": round(float(rate), 3)}
        )
    for entry in slo_map.values():
        entry["semesters"].sort(key=lambda s: _sem_key(s["semester"]))
    slo_trends = list(slo_map.values())

    # --- aggregate readiness score (avg proficiency in latest semester, as %) ---
    latest_rates = db.execute(
        text("""
            SELECT AVG(proficiency_rate)
            FROM cohort_slo_history
            WHERE course_id = :cid AND semester = :sem
        """),
        {"cid": FEATURED_COURSE_ID, "sem": SEMESTERS[-1]},
    ).scalar() or 0.0
    aggregate_readiness_score = round(float(latest_rates) * 100, 1)

    # --- assessment failure rates per SLO (latest semester) ---
    assess_rows = db.execute(
        text("""
            SELECT s.code, s.description, h.proficiency_rate
            FROM slos s
            JOIN cohort_slo_history h ON h.slo_id = s.id
            WHERE s.course_id = :cid AND h.semester = :sem
            ORDER BY s.id
        """),
        {"cid": FEATURED_COURSE_ID, "sem": SEMESTERS[-1]},
    ).fetchall()

    assessment_failure_rates = []
    for code, desc, rate in assess_rows:
        failure_rate = round(1.0 - float(rate), 3)
        result = "fail" if failure_rate >= FAILURE_THRESHOLD else "pass"
        assessment_failure_rates.append(
            {
                "slo_code": code,
                "description": desc,
                "failure_rate": failure_rate,
                "rules_engine_result": result,
            }
        )

    # --- faculty workload ---
    fac_rows = db.execute(
        text("""
            SELECT id, name, department, current_credits, max_credits
            FROM faculty
            ORDER BY name
        """)
    ).fetchall()

    faculty_workload = []
    overloaded_count = 0
    for fac_id, name, dept, current, max_cr in fac_rows:
        if current is None or max_cr is None:
            continue
        overloaded = current > max_cr
        if overloaded:
            overloaded_count += 1
            status = StatusCode.urgent
        elif current == max_cr:
            status = StatusCode.needs_attention
        else:
            status = StatusCode.on_track
        faculty_workload.append(
            {
                "id": fac_id,
                "name": name,
                "department": dept,
                "current_credits": current,
                "max_credits": max_cr,
                "overloaded": overloaded,
                "status": status,
            }
        )

    workload_threshold_result = "fail" if overloaded_count > 0 else "pass"

    # --- workload balancing rationale ---
    overloaded_faculty = [f for f in faculty_workload if f["overloaded"]]
    if overloaded_faculty:
        names = ", ".join(f["name"] for f in overloaded_faculty)
        workload_rationale = (
            f"Faculty workload analysis flags {len(overloaded_faculty)} instructor(s) exceeding "
            f"their credit cap: {names}. Recommend reassigning sections to available faculty "
            "before the semester registration deadline to prevent burnout and maintain teaching quality."
        )
    else:
        workload_rationale = (
            f"Faculty workload is within capacity across {len(faculty_workload)} instructors; "
            "no immediate rebalancing needed."
        )

    # --- course name ---
    course_name = db.execute(
        text("SELECT name FROM courses WHERE id = :cid LIMIT 1"),
        {"cid": FEATURED_COURSE_ID},
    ).scalar() or "Introduction to Programming"

    # --- cohort readiness rationale ---
    weakest = max(assessment_failure_rates, key=lambda r: r["failure_rate"], default=None)
    cohort_rationale = (
        f"Cohort SLO assessment for {FEATURED_COURSE_CODE} shows {aggregate_readiness_score}% "
        f"aggregate proficiency in {SEMESTERS[-1]}."
    )
    if weakest:
        cohort_rationale += (
            f" {weakest['slo_code']} ({weakest['description']}) is the area of greatest "
            f"concern, with a {round(weakest['failure_rate'] * 100)}% failure rate. "
            "Recommend adjusting instructional strategy and scheduling a mid-semester cohort review."
        )

    if os.getenv("AI_MODE", "live") != "scripted":
        live_cohort_rationale = await _live_rationale(
            "teaching_readiness_cohort", {"course_id": FEATURED_COURSE_ID}
        )
        if live_cohort_rationale:
            cohort_rationale = live_cohort_rationale

        live_workload_rationale = await _live_rationale(
            "teaching_readiness_workload", {"course_id": FEATURED_COURSE_ID}
        )
        if live_workload_rationale:
            workload_rationale = live_workload_rationale

    return {
        "stage_summary": {
            "health": _readiness_health(overloaded_count, aggregate_readiness_score),
            "cohort_size": cohort_size,
            "aggregate_readiness_score": aggregate_readiness_score,
        },
        "featured_course": {
            "code": FEATURED_COURSE_CODE,
            "name": course_name,
            "slo_trends": slo_trends,
            "rationale": cohort_rationale,
        },
        "assessment_failure_rates": assessment_failure_rates,
        "faculty_workload": faculty_workload,
        "workload_threshold_result": workload_threshold_result,
        "workload_rationale": workload_rationale,
    }
