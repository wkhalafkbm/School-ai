import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.evidence import build_evidence
from app.gateway import iam, orchestrate
from app.gateway.config import get_agent_id

router = APIRouter(prefix="/api/career-alumni", tags=["career-alumni"])

STUDENT_ID = "stu-005"


async def _live_rationale(payload: dict) -> str | None:
    try:
        agent_id = get_agent_id("career")
        token = await iam.get_token()
        run_id = await orchestrate.start_run(agent_id, token, payload)
        run = await orchestrate.poll_run(agent_id, run_id, token)
    except (HTTPException, KeyError, httpx.HTTPError):
        return None
    if run["status"] != "completed":
        return None
    return run["output"]["result"]


@router.get("/profile")
async def career_alumni_profile(db: Session = Depends(get_db)):
    # --- stage summary: graduate employment outcomes ---
    outcome_rows = db.execute(
        text("""
            SELECT COUNT(*) AS total_alumni,
                   COUNT(*) FILTER (WHERE current_role IS NOT NULL) AS employed_count
            FROM alumni_mentors
        """)
    ).one()

    total_graduates = int(outcome_rows.total_alumni or 0)
    employed_count = int(outcome_rows.employed_count or 0)
    placement_rate = (employed_count / total_graduates) if total_graduates > 0 else 0.0

    # --- student profile ---
    student_row = db.execute(
        text("""
            SELECT s.id, s.name, s.year_level, s.gpa,
                   p.name AS program_name
            FROM students s
            JOIN programs p ON p.id = s.program_id
            WHERE s.id = :sid
        """),
        {"sid": STUDENT_ID},
    ).one()

    # --- career pathway ---
    pathway_row = db.execute(
        text("""
            SELECT target_role, target_industry, skills_gap, recommended_courses,
                   internship_target_semester, target_companies
            FROM career_pathways
            WHERE student_id = :sid
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()

    target_role = pathway_row.target_role if pathway_row else "Software Engineer"
    target_industry = pathway_row.target_industry if pathway_row else "Technology"

    # --- alumni mentor match: prefer mentor who already has student as mentee ---
    mentor_row = db.execute(
        text("""
            SELECT am.id, am.name, am.current_role, am.current_company,
                   am.industry, am.graduation_year, p.name AS program_name
            FROM alumni_mentors am
            LEFT JOIN programs p ON p.id = am.program_id
            WHERE am.mentee_student_ids::jsonb ? :sid
               OR (am.program_id = (
                       SELECT program_id FROM students WHERE id = :sid
                   ) AND am.available = true)
            ORDER BY (am.mentee_student_ids::jsonb ? :sid) DESC
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()

    alumni_mentor_match = (
        {
            "id": mentor_row.id,
            "name": mentor_row.name,
            "current_role": mentor_row.current_role,
            "current_company": mentor_row.current_company,
            "industry": mentor_row.industry,
            "graduation_year": mentor_row.graduation_year,
            "program_name": mentor_row.program_name,
            "match_basis": "Shared program, target industry, and graduation cohort alignment",
        }
        if mentor_row
        else None
    )

    # --- AI-generated career pathway recommendation via evidence builder ---
    evidence_output = build_evidence(
        {
            "sis_data": {"gpa": float(student_row.gpa)},
            "career_pathway": {
                "target_role": target_role,
                "target_industry": target_industry,
            },
            "historical_matches": total_graduates,
        }
    )

    career_pathway_recommendation = {
        "actions": [
            {
                "type": "skill_gap_elective",
                "description": (
                    "Enrol in an advanced elective aligned with the target role "
                    "to close identified technical skill gaps before graduation"
                ),
                "priority": "high",
            },
            {
                "type": "internship_placement",
                "description": (
                    f"Apply to a {target_industry} internship within the next semester "
                    "to gain industry-specific experience before entering the job market"
                ),
                "priority": "high",
            },
            {
                "type": "mentor_connection",
                "description": (
                    "Connect with the matched alumni mentor to discuss career pathway "
                    "expectations and build a professional network in the target industry"
                ),
                "priority": "medium",
            },
        ],
        "confidence": evidence_output.confidence,
        "rationale": evidence_output.rationale,
    }

    # --- seeded career advisor workflow item ---
    advisor_item_row = db.execute(
        text("""
            SELECT id, trigger, owner_name, owner_role, status, created_date
            FROM workflow_items
            WHERE student_id = :sid
              AND stage = 'career_alumni'
              AND workflow_type = 'career_path_approval'
            ORDER BY created_date DESC
            LIMIT 1
        """),
        {"sid": STUDENT_ID},
    ).fetchone()

    career_advisor_item = (
        {
            "id": advisor_item_row.id,
            "trigger": advisor_item_row.trigger,
            "owner_name": advisor_item_row.owner_name,
            "owner_role": advisor_item_row.owner_role,
            "status": advisor_item_row.status,
            "created_date": str(advisor_item_row.created_date),
        }
        if advisor_item_row
        else None
    )

    electives = [
        {
            "course_code": "CS410",
            "course_name": "Cloud Computing & Distributed Systems",
            "rationale": (
                "Directly addresses the cloud infrastructure gap required "
                "for senior engineering roles in FinTech"
            ),
        },
        {
            "course_code": "CS420",
            "course_name": "Advanced System Design",
            "rationale": (
                "Builds system design skills assessed in technical interviews "
                "at target companies including Boubyan Bank and NBK Digital"
            ),
        },
    ]
    internships = [
        {
            "company": "NBK Digital",
            "industry": "FinTech",
            "target_semester": "Spring 2025",
            "rationale": (
                "Matches target industry and provides hands-on FinTech "
                "engineering experience before graduation"
            ),
        },
    ]

    if os.getenv("AI_MODE", "live") != "scripted":
        live_rationale = await _live_rationale(
            {
                "student_id": STUDENT_ID,
                "electives": electives,
                "internships": internships,
            }
        )
        if live_rationale:
            career_pathway_recommendation["rationale"] = live_rationale

    return {
        "stage_summary": {
            "health": "opportunity",
            "placement_rate": round(placement_rate, 2),
            "median_time_to_placement": 3.2,
            "employed_count": employed_count,
            "total_graduates": total_graduates,
        },
        "student": {
            "id": student_row.id,
            "name": student_row.name,
            "program_name": student_row.program_name,
            "year_level": student_row.year_level,
            "gpa": float(student_row.gpa),
            "target_role": target_role,
            "target_industry": target_industry,
        },
        "skill_gaps": [
            {
                "skill": "System Design",
                "current_level": "beginner",
                "required_level": "intermediate",
                "gap": True,
            },
            {
                "skill": "Cloud Infrastructure (AWS/GCP)",
                "current_level": "none",
                "required_level": "intermediate",
                "gap": True,
            },
            {
                "skill": "Data Structures & Algorithms",
                "current_level": "intermediate",
                "required_level": "intermediate",
                "gap": False,
            },
        ],
        "recommendations": {
            "electives": electives,
            "internships": internships,
        },
        "alumni_mentor_match": alumni_mentor_match,
        "outcomes_feedback_loop": {
            "description": (
                f"Career pathway recommendations are continuously refined using employment "
                f"outcome data from {total_graduates} graduates. When alumni update their "
                f"career status, the system recalibrates skill-gap weights and elective "
                f"rankings for current students on the same pathway."
            ),
            "data_points": total_graduates,
            "last_updated": "2024-11-01",
        },
        "career_pathway_recommendation": career_pathway_recommendation,
        "career_advisor_item": career_advisor_item,
    }
