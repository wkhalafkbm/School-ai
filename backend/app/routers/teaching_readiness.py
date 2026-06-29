from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
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


@router.get("/profile")
def teaching_readiness_profile(db: Session = Depends(get_db)):
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

    # --- course name ---
    course_name = db.execute(
        text("SELECT name FROM courses WHERE id = :cid LIMIT 1"),
        {"cid": FEATURED_COURSE_ID},
    ).scalar() or "Introduction to Programming"

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
        },
        "assessment_failure_rates": assessment_failure_rates,
        "faculty_workload": faculty_workload,
        "workload_threshold_result": workload_threshold_result,
    }
