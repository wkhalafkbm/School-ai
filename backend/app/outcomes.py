"""
Program Learning Outcomes (PLOs) and the SLO → CLO → PLO attainment chain —
issue #97.

The deck's evidence chain runs Assessment → SLO → CLO → PLO → program
effectiveness. The bottom of that chain is data (SLO assessments); the top is
curriculum design, so it lives in a config file rather than a table: which
PLOs a program declares and which course SLOs feed each one. The CLO level is
not configured at all — it is the course-level roll-up of the SLOs a course
contributes to a PLO.

The arithmetic, top down:

* an SLO's rate is the proficiency rate of its most recent assessment;
* a course's roll-up for a PLO (the CLO level) is the mean of the rates of the
  SLOs it contributes to that PLO; a course whose SLOs are all unassessed has
  no roll-up;
* a PLO's attainment is the mean of its course roll-ups;
* every level is on target when its rate is at or above the program's
  attainment target.
"""

import json
from pathlib import Path
from statistics import mean

CONFIG_PATH = Path(__file__).parent.parent / "config" / "program_learning_outcomes.json"

_SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}


def load_program_outcomes(path: Path = CONFIG_PATH) -> dict:
    """
    The configured program, its attainment target and its PLOs, each with the
    SLO codes that feed it:

        {"program_id", "program_name", "attainment_target",
         "plos": [{"code", "title", "description", "slo_codes": [...]}, ...]}
    """
    return json.loads(path.read_text())


def semester_key(semester: str) -> tuple[int, int]:
    """Chronological sort key for '2024-Fall'-style semester names."""
    year, season = semester.split("-")
    return int(year), _SEASON_ORDER.get(season, 99)


def _round(rate: float | None) -> float | None:
    return None if rate is None else round(rate, 3)


def _slo_entry(slo: dict, assessments: list[dict], target: float) -> dict:
    history = sorted(assessments, key=lambda a: semester_key(a["semester"]))
    latest = history[-1] if history else None
    rate = float(latest["proficiency_rate"]) if latest else None
    return {
        "slo_id": slo["slo_id"],
        "slo_code": slo["slo_code"],
        "description": slo["description"],
        "proficiency_rate": _round(rate),
        "on_target": None if rate is None else rate >= target,
        "last_assessed_semester": latest["semester"] if latest else None,
        "assessed_students": latest.get("assessed_students") if latest else None,
        "source": latest.get("source") if latest else None,
        "history": [
            {"semester": a["semester"], "proficiency_rate": _round(float(a["proficiency_rate"]))}
            for a in history
        ],
    }


def compute_attainment(outcomes: dict, slos: list[dict], assessments: list[dict]) -> dict:
    """
    Roll fixture-shaped rows up the chain.

    ``slos`` rows carry slo_id, slo_code, description, course_id, course_code,
    course_name. ``assessments`` rows carry slo_id, semester, proficiency_rate
    and optionally assessed_students and source (where the rate came from).
    """
    target = float(outcomes["attainment_target"])
    slo_by_code = {row["slo_code"]: row for row in slos}
    assessments_by_slo: dict[str, list[dict]] = {}
    for row in assessments:
        assessments_by_slo.setdefault(row["slo_id"], []).append(row)

    plos = []
    for plo in outcomes["plos"]:
        courses: dict[str, dict] = {}
        for code in plo["slo_codes"]:
            slo = slo_by_code.get(code)
            if slo is None:
                continue
            course = courses.setdefault(
                slo["course_id"],
                {
                    "course_id": slo["course_id"],
                    "course_code": slo["course_code"],
                    "course_name": slo["course_name"],
                    "attainment": None,
                    "on_target": None,
                    "slos": [],
                },
            )
            course["slos"].append(_slo_entry(slo, assessments_by_slo.get(slo["slo_id"], []), target))

        for course in courses.values():
            rates = [s["proficiency_rate"] for s in course["slos"] if s["proficiency_rate"] is not None]
            if rates:
                rollup = mean(rates)
                course["attainment"] = _round(rollup)
                course["on_target"] = rollup >= target

        rollups = [c["attainment"] for c in courses.values() if c["attainment"] is not None]
        plo_rate = mean(rollups) if rollups else None
        slo_entries = [s for c in courses.values() for s in c["slos"]]
        plos.append(
            {
                "code": plo["code"],
                "title": plo["title"],
                "description": plo["description"],
                "attainment": _round(plo_rate),
                "on_target": None if plo_rate is None else plo_rate >= target,
                "slo_count": len(slo_entries),
                "assessed_slo_count": sum(1 for s in slo_entries if s["proficiency_rate"] is not None),
                "courses": sorted(courses.values(), key=lambda c: c["course_code"]),
            }
        )

    semesters = {a["semester"] for a in assessments}
    return {
        "program_id": outcomes["program_id"],
        "program_name": outcomes["program_name"],
        "attainment_target": target,
        "latest_semester": max(semesters, key=semester_key) if semesters else None,
        "plos_below_target": sum(1 for p in plos if p["on_target"] is False),
        "plos": plos,
    }
