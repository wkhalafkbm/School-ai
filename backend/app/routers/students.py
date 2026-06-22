from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/students", tags=["students"])


def _require_student(student_id: str, db: Session) -> models.Student:
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# --- get_student_profile ---

@router.get("/{student_id}", summary="Get student profile", description="Returns core profile fields for a student: name, program, status, GPA, year level, admission term, and nationality.")
def get_student_profile(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    program_name = student.program.name if student.program else None
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "gender": student.gender,
        "nationality": student.nationality,
        "program": program_name,
        "status": student.status,
        "year_level": student.year_level,
        "credits_earned": student.credits_earned,
        "gpa": student.gpa,
        "admission_term": student.admission_term,
    }


# --- get_applicant_academic_history ---

@router.get("/{student_id}/academic-history", summary="Get applicant academic history", description="Returns the student's full enrollment history including course names, semesters, grades, and status.")
def get_academic_history(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "enrollments": [
            {
                "course_code": e.course.code if e.course else None,
                "course_name": e.course.name if e.course else None,
                "semester": e.semester,
                "status": e.status,
                "grade": e.grade,
                "credits": e.course.credits if e.course else None,
            }
            for e in enrollments
        ],
    }


# --- get_sponsorship_status ---

@router.get("/{student_id}/sponsorship", summary="Get sponsorship status", description="Returns all sponsorship records for a student including sponsor name, coverage type, amount, and approval status.")
def get_sponsorship_status(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    records = (
        db.query(models.SponsorshipRecord)
        .filter(models.SponsorshipRecord.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "records": [
            {
                "sponsor_name": r.sponsor_name,
                "sponsor_full_name": r.sponsor_full_name,
                "coverage_type": r.coverage_type,
                "status": r.status,
                "amount_per_semester": r.amount_per_semester,
                "currency": r.currency,
                "application_date": str(r.application_date) if r.application_date else None,
                "approval_date": str(r.approval_date) if r.approval_date else None,
                "notes": r.notes,
            }
            for r in records
        ],
    }


# --- get_onboarding_status ---

@router.get("/{student_id}/onboarding", summary="Get onboarding status", description="Returns all onboarding tasks for a student with completion status, category, and due dates.")
def get_onboarding_status(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    tasks = (
        db.query(models.OnboardingTask)
        .filter(models.OnboardingTask.student_id == student_id)
        .all()
    )
    completed = sum(1 for t in tasks if t.completed)
    return {
        "student_id": student_id,
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "tasks": [
            {
                "task_name": t.task_name,
                "category": t.category,
                "completed": t.completed,
                "due_date": str(t.due_date) if t.due_date else None,
                "completed_date": str(t.completed_date) if t.completed_date else None,
            }
            for t in tasks
        ],
    }


# --- get_course_registrations ---

@router.get("/{student_id}/registrations", summary="Get course registrations", description="Returns all course registrations for a student including course name, semester, status, and grade.")
def get_course_registrations(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "registrations": [
            {
                "course_code": e.course.code if e.course else None,
                "course_name": e.course.name if e.course else None,
                "semester": e.semester,
                "status": e.status,
                "grade": e.grade,
            }
            for e in enrollments
        ],
    }


# --- get_prerequisite_check ---

@router.get("/{student_id}/prerequisites", summary="Get prerequisite check", description="Returns prerequisite status for each enrolled course, indicating whether each prerequisite has been met.")
def get_prerequisite_check(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    passed_course_ids = {
        e.course_id
        for e in student.enrollments
        if e.grade and e.grade not in {"F", "W", "WF"}
    }
    enrolled_course_ids = {e.course_id for e in student.enrollments}
    prereqs = (
        db.query(models.Prerequisite)
        .filter(models.Prerequisite.course_id.in_(enrolled_course_ids))
        .all()
    )
    results = []
    for p in prereqs:
        met = p.prerequisite_course_id in passed_course_ids
        results.append({
            "course_code": p.course.code if p.course else None,
            "course_name": p.course.name if p.course else None,
            "prerequisite_code": p.prerequisite_course.code if p.prerequisite_course else None,
            "prerequisite_name": p.prerequisite_course.name if p.prerequisite_course else None,
            "min_grade": p.min_grade,
            "met": met,
        })
    return {"student_id": student_id, "prerequisites": results}


# --- get_financial_holds ---

@router.get("/{student_id}/financial-holds", summary="Get financial holds", description="Returns financial aid records for a student including aid type, amount, status, and renewal conditions.")
def get_financial_holds(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    aid = (
        db.query(models.FinancialAidRecord)
        .filter(models.FinancialAidRecord.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "financial_aid": [
            {
                "aid_type": r.aid_type,
                "amount": r.amount,
                "currency": r.currency,
                "semester": r.semester,
                "status": r.status,
                "renewable": r.renewable,
                "renewal_conditions": r.renewal_conditions,
                "applied_date": str(r.applied_date) if r.applied_date else None,
                "approved_date": str(r.approved_date) if r.approved_date else None,
                "notes": r.notes,
            }
            for r in aid
        ],
    }


# --- get_administrative_holds ---

@router.get("/{student_id}/admin-holds", summary="Get administrative holds", description="Returns all administrative holds on a student including hold type, severity, and whether they block registration or transcript release.")
def get_admin_holds(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    holds = (
        db.query(models.AdministrativeHold)
        .filter(models.AdministrativeHold.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "holds": [
            {
                "hold_type": h.hold_type,
                "reason": h.reason,
                "severity": h.severity,
                "blocks_registration": h.blocks_registration,
                "blocks_transcript": h.blocks_transcript,
                "placed_by": h.placed_by,
                "placed_date": str(h.placed_date) if h.placed_date else None,
                "resolved_date": str(h.resolved_date) if h.resolved_date else None,
            }
            for h in holds
        ],
    }


# --- get_lms_signals ---

@router.get("/{student_id}/lms-signals", summary="Get LMS signals", description="Returns LMS engagement signals per course including login frequency, assignment submission rate, quiz scores, and risk flag.")
def get_lms_signals(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    rows = (
        db.query(models.LMSSignal, models.Course)
        .join(models.Course, models.LMSSignal.course_id == models.Course.id, isouter=True)
        .filter(models.LMSSignal.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "signals": [
            {
                "course_code": course.code if course else None,
                "course_name": course.name if course else None,
                "semester": s.semester,
                "signal_date": str(s.signal_date) if s.signal_date else None,
                "login_count_last_30_days": s.login_count_last_30_days,
                "last_login_days_ago": s.last_login_days_ago,
                "assignment_submission_rate": s.assignment_submission_rate,
                "avg_quiz_score": s.avg_quiz_score,
                "video_watch_rate": s.video_watch_rate,
                "forum_posts": s.forum_posts,
                "risk_flag": s.risk_flag,
            }
            for s, course in rows
        ],
    }


# --- get_attendance (derived from LMS signals) ---

@router.get("/{student_id}/attendance", summary="Get attendance summary", description="Returns per-course attendance signals derived from LMS login activity, video watch rate, and engagement risk flag.")
def get_attendance(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    rows = (
        db.query(models.LMSSignal, models.Course)
        .join(models.Course, models.LMSSignal.course_id == models.Course.id, isouter=True)
        .filter(models.LMSSignal.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "attendance_summary": [
            {
                "course_code": course.code if course else None,
                "course_name": course.name if course else None,
                "semester": s.semester,
                "login_count_last_30_days": s.login_count_last_30_days,
                "last_login_days_ago": s.last_login_days_ago,
                "video_watch_rate": s.video_watch_rate,
                "engagement_risk": s.risk_flag,
            }
            for s, course in rows
        ],
    }


# --- get_early_grades ---

@router.get("/{student_id}/early-grades", summary="Get early grades", description="Returns SLO assessment results for a student indicating early performance signals, proficiency, and attempt number per course.")
def get_early_grades(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    slo_results = (
        db.query(models.StudentSLOResult)
        .filter(models.StudentSLOResult.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "early_grades": [
            {
                "course_code": r.slo.course.code if r.slo and r.slo.course else None,
                "course_name": r.slo.course.name if r.slo and r.slo.course else None,
                "slo_code": r.slo.code if r.slo else None,
                "semester": r.semester,
                "score": r.score,
                "proficient": r.proficient,
                "attempt_number": r.attempt_number,
            }
            for r in slo_results
        ],
    }


# --- get_support_history ---

@router.get("/{student_id}/support-history", summary="Get support history", description="Returns all support cases for a student including case type, subject, priority, status, and resolution.")
def get_support_history(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    cases = (
        db.query(models.SupportCase)
        .filter(models.SupportCase.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "cases": [
            {
                "case_type": c.case_type,
                "subject": c.subject,
                "description": c.description,
                "priority": c.priority,
                "status": c.status,
                "opened_date": str(c.opened_date) if c.opened_date else None,
                "closed_date": str(c.closed_date) if c.closed_date else None,
                "resolution": c.resolution,
            }
            for c in cases
        ],
    }


# --- get_risk_summary ---

@router.get("/{student_id}/risk-summary", summary="Get risk summary", description="Returns a synthesised risk level (high/medium/low/none) and list of risk factors derived from LMS signals, support cases, and administrative holds.")
def get_risk_summary(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    signals = student.lms_signals
    cases = student.support_cases
    holds = student.administrative_holds

    risk_factors = []
    high_signals = [s for s in signals if s.risk_flag == "high"]
    if high_signals:
        risk_factors.append(f"{len(high_signals)} high-risk LMS signal(s)")
    open_cases = [c for c in cases if c.status == "open"]
    if open_cases:
        risk_factors.append(f"{len(open_cases)} open support case(s)")
    blocking_holds = [h for h in holds if h.blocks_registration and not h.resolved_date]
    if blocking_holds:
        risk_factors.append(f"{len(blocking_holds)} registration-blocking hold(s)")

    if high_signals or (open_cases and student.gpa and student.gpa < 2.0):
        level = "high"
    elif open_cases or blocking_holds:
        level = "medium"
    elif risk_factors:
        level = "low"
    else:
        level = "none"

    return {
        "student_id": student_id,
        "student_name": student.name,
        "risk_level": level,
        "risk_factors": risk_factors,
        "open_support_cases": len(open_cases),
        "high_lms_signals": len(high_signals),
        "blocking_holds": len(blocking_holds),
    }


# --- get_transcript ---

@router.get("/{student_id}/transcript", summary="Get transcript", description="Returns the student's full academic transcript including all courses, credits, grades, and cumulative GPA.")
def get_transcript(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )
    return {
        "student_id": student_id,
        "student_name": student.name,
        "gpa": student.gpa,
        "credits_earned": student.credits_earned,
        "courses": [
            {
                "course_code": e.course.code if e.course else None,
                "course_name": e.course.name if e.course else None,
                "credits": e.course.credits if e.course else None,
                "semester": e.semester,
                "grade": e.grade,
                "status": e.status,
            }
            for e in enrollments
        ],
    }


# --- get_skill_profile ---

@router.get("/{student_id}/skills", summary="Get skill profile", description="Returns the student's career pathway including target role, skills gap, recommended courses, target companies, and internship timeline.")
def get_skill_profile(student_id: str, db: Session = Depends(get_db)):
    student = _require_student(student_id, db)
    pathways = (
        db.query(models.CareerPathway)
        .filter(models.CareerPathway.student_id == student_id)
        .all()
    )
    if pathways:
        pathway = pathways[0]
        return {
            "student_id": student_id,
            "target_role": pathway.target_role,
            "target_industry": pathway.target_industry,
            "skills_gap": pathway.skills_gap or [],
            "recommended_courses": pathway.recommended_courses or [],
            "target_companies": pathway.target_companies or [],
            "internship_target_semester": pathway.internship_target_semester,
            "status": pathway.status,
        }
    return {
        "student_id": student_id,
        "target_role": None,
        "target_industry": None,
        "skills_gap": [],
        "recommended_courses": [],
        "target_companies": [],
        "internship_target_semester": None,
        "status": None,
    }
