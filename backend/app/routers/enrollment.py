from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.status import StatusCode

router = APIRouter(prefix="/api/enrollment", tags=["enrollment"])

STUDENT_ID = "stu-002"
SEMESTER = "2024-Fall"
CREDIT_LIMIT = 12


def _enrollment_health(blocked: int, total: int) -> str:
    if total == 0:
        return StatusCode.on_track
    ratio = blocked / total
    if ratio <= 0.05:
        return StatusCode.on_track
    if ratio <= 0.20:
        return StatusCode.watch
    if ratio <= 0.50:
        return StatusCode.needs_attention
    return StatusCode.urgent


def _time_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _sections_overlap(a: dict, b: dict) -> bool:
    shared_days = set(a["days"] or []) & set(b["days"] or [])
    if not shared_days:
        return False
    a_start = _time_to_minutes(a["start_time"])
    a_end = _time_to_minutes(a["end_time"])
    b_start = _time_to_minutes(b["start_time"])
    b_end = _time_to_minutes(b["end_time"])
    return a_start < b_end and b_start < a_end


@router.get("/profile")
def enrollment_profile(db: Session = Depends(get_db)):
    # --- stage summary ---
    total_enrolled = db.execute(
        text("SELECT COUNT(*) FROM students WHERE status = 'enrolled'")
    ).scalar() or 0

    blocked_count = db.execute(
        text("""
            SELECT COUNT(DISTINCT student_id) FROM administrative_holds
            WHERE blocks_registration = true AND resolved_date IS NULL
        """)
    ).scalar() or 0

    pending_count = db.execute(
        text("""
            SELECT COUNT(*) FROM workflow_items
            WHERE stage = 'registration' AND status IN ('pending', 'in_review')
        """)
    ).scalar() or 0

    complete_count = max(0, int(total_enrolled) - int(blocked_count) - int(pending_count))
    health = _enrollment_health(int(blocked_count), max(int(total_enrolled), 1))

    # --- student profile ---
    row = db.execute(
        text("""
            SELECT s.id, s.name, s.year_level, s.gpa,
                   p.name AS program_name
            FROM students s
            JOIN programs p ON p.id = s.program_id
            WHERE s.id = :sid
        """),
        {"sid": STUDENT_ID},
    ).one()

    # --- onboarding tasks ---
    task_rows = db.execute(
        text("""
            SELECT task_name, category, completed, due_date
            FROM onboarding_tasks
            WHERE student_id = :sid
            ORDER BY due_date
        """),
        {"sid": STUDENT_ID},
    ).fetchall()

    onboarding_tasks = [
        {
            "task_name": t.task_name,
            "category": t.category,
            "completed": t.completed,
            "due_date": str(t.due_date) if t.due_date else None,
        }
        for t in task_rows
    ]

    # --- registration blockers ---
    blockers = []

    # 1. financial_aid_hold
    fin_hold = db.execute(
        text("""
            SELECT reason FROM administrative_holds
            WHERE student_id = :sid AND hold_type = 'financial'
              AND blocks_registration = true AND resolved_date IS NULL
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()
    if fin_hold:
        blockers.append({
            "type": "financial_aid_hold",
            "description": fin_hold.reason,
            "rules_engine_result": "fail",
        })

    # 2. prerequisite — active enrollments where prereq not yet completed
    prereq_violations = db.execute(
        text("""
            SELECT c.code AS course_code, c.name AS course_name,
                   pc.code AS prereq_code, pc.name AS prereq_name,
                   pr.min_grade
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            JOIN prerequisites pr ON pr.course_id = e.course_id
            JOIN courses pc ON pc.id = pr.prerequisite_course_id
            WHERE e.student_id = :sid AND e.semester = :sem AND e.status = 'active'
              AND NOT EXISTS (
                SELECT 1 FROM enrollments ce
                WHERE ce.student_id = :sid
                  AND ce.course_id = pr.prerequisite_course_id
                  AND ce.status = 'completed'
              )
        """),
        {"sid": STUDENT_ID, "sem": SEMESTER},
    ).fetchall()
    if prereq_violations:
        v = prereq_violations[0]
        blockers.append({
            "type": "prerequisite",
            "description": (
                f"{v.course_code} requires completion of {v.prereq_code} "
                f"({v.prereq_name}, min. grade {v.min_grade})"
            ),
            "rules_engine_result": "fail",
        })

    # 3. credit_limit — total active credits this semester
    total_credits = db.execute(
        text("""
            SELECT COALESCE(SUM(c.credits), 0)
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.student_id = :sid AND e.semester = :sem AND e.status = 'active'
        """),
        {"sid": STUDENT_ID, "sem": SEMESTER},
    ).scalar() or 0

    if int(total_credits) > CREDIT_LIMIT:
        blockers.append({
            "type": "credit_limit",
            "description": (
                f"{total_credits} credits exceeds the {CREDIT_LIMIT}-credit limit "
                f"for first-year students"
            ),
            "rules_engine_result": "fail",
        })

    # 4. conflict — detect overlapping sections
    section_rows = db.execute(
        text("""
            SELECT c.code AS course_code, ss.section_code,
                   ss.days, ss.start_time, ss.end_time
            FROM enrollments e
            JOIN schedule_sections ss ON ss.id = e.section_id
            JOIN courses c ON c.id = e.course_id
            WHERE e.student_id = :sid AND e.semester = :sem AND e.status = 'active'
        """),
        {"sid": STUDENT_ID, "sem": SEMESTER},
    ).fetchall()

    sections = [
        {
            "course_code": s.course_code,
            "section_code": s.section_code,
            "days": s.days,
            "start_time": s.start_time,
            "end_time": s.end_time,
        }
        for s in section_rows
    ]

    conflict_found = False
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            if _sections_overlap(sections[i], sections[j]):
                a, b = sections[i], sections[j]
                blockers.append({
                    "type": "conflict",
                    "description": (
                        f"{a['section_code']} ({'/'.join(a['days'])} "
                        f"{a['start_time']}–{a['end_time']}) conflicts with "
                        f"{b['section_code']} ({'/'.join(b['days'])} "
                        f"{b['start_time']}–{b['end_time']})"
                    ),
                    "rules_engine_result": "fail",
                })
                conflict_found = True
                break
        if conflict_found:
            break

    # 5. admin_hold
    admin_hold = db.execute(
        text("""
            SELECT reason FROM administrative_holds
            WHERE student_id = :sid AND hold_type = 'administrative'
              AND resolved_date IS NULL
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()
    if admin_hold:
        blockers.append({
            "type": "admin_hold",
            "description": admin_hold.reason,
            "rules_engine_result": "fail",
        })

    # 6. missing_document — incomplete documentation/health onboarding tasks
    missing_doc = db.execute(
        text("""
            SELECT task_name FROM onboarding_tasks
            WHERE student_id = :sid AND completed = false
              AND category IN ('documentation', 'health')
            ORDER BY due_date
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()
    if missing_doc:
        blockers.append({
            "type": "missing_document",
            "description": f"Required document not submitted: {missing_doc.task_name}",
            "rules_engine_result": "fail",
        })

    # --- suggested schedule ---
    suggested_schedule = {
        "sections": [
            {
                "course": "CS101",
                "section": "CS101-01",
                "days": ["Sun", "Tue"],
                "time": "09:00–10:15",
                "room": "B101",
            },
            {
                "course": "MATH101",
                "section": "MATH101-02",
                "days": ["Mon", "Wed"],
                "time": "09:00–10:15",
                "room": "A202",
            },
            {
                "course": "IS201",
                "section": "IS201-01",
                "days": ["Mon", "Wed"],
                "time": "09:00–10:15",
                "room": "D101",
                "note": "Pending prerequisite clearance",
            },
        ],
        "note": (
            "Switch MATH101 from section 01 (Sun/Tue) to section 02 (Mon/Wed) "
            "to resolve the time conflict with CS101. IS201 registration pending "
            "completion of CS101 prerequisite."
        ),
    }

    return {
        "stage_summary": {
            "health": health,
            "registration_complete": int(complete_count),
            "registration_pending": int(pending_count),
            "registration_blocked": int(blocked_count),
        },
        "student": {
            "id": row.id,
            "name": row.name,
            "program_name": row.program_name,
            "year_level": row.year_level,
            "gpa": row.gpa,
            "onboarding_tasks": onboarding_tasks,
        },
        "registration_blockers": blockers,
        "suggested_schedule": suggested_schedule,
    }
