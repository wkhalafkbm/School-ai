"""
Deterministic rules engine — issue #7.

Every public function is a pure function: explicit inputs, explicit output,
no side effects. Return type is always RuleResult(passed, reason).
"""
from dataclasses import dataclass

# Higher number = better grade.
_GRADE_RANK: dict[str, int] = {
    "F": 0,
    "D": 1,
    "D+": 2,
    "C-": 3,
    "C": 4,
    "C+": 5,
    "B-": 6,
    "B": 7,
    "B+": 8,
    "A-": 9,
    "A": 10,
}


@dataclass(frozen=True)
class RuleResult:
    passed: bool
    reason: str


# ---------------------------------------------------------------------------
# Prerequisite validation
# ---------------------------------------------------------------------------


def check_prerequisites(
    course_id: str,
    completed_courses: list[dict],
    prerequisites: list[dict],
) -> RuleResult:
    """
    Return PASS if every prerequisite for *course_id* is satisfied by
    *completed_courses* (list of {course_id, grade} dicts) at or above the
    required min_grade. Prerequisites data mirrors the Prerequisite fixture
    schema: {course_id, prerequisite_course_id, min_grade}.
    """
    required = [p for p in prerequisites if p["course_id"] == course_id]
    if not required:
        return RuleResult(passed=True, reason="No prerequisites required")

    completed_map = {c["course_id"]: c["grade"] for c in completed_courses}
    missing: list[str] = []

    for prereq in required:
        pid = prereq["prerequisite_course_id"]
        min_grade = prereq["min_grade"]
        if pid not in completed_map:
            missing.append(f"{pid} (not completed)")
        elif _GRADE_RANK.get(completed_map[pid], -1) < _GRADE_RANK.get(min_grade, 0):
            actual = completed_map[pid]
            missing.append(f"{pid} (grade {actual} below required {min_grade})")

    if missing:
        return RuleResult(passed=False, reason=f"Missing prerequisites: {', '.join(missing)}")
    return RuleResult(passed=True, reason="All prerequisites satisfied")


# ---------------------------------------------------------------------------
# Credit limit validation
# ---------------------------------------------------------------------------


def check_credit_limit(proposed_credits: int, credit_limit: int) -> RuleResult:
    """Return PASS if proposed_credits <= credit_limit."""
    if proposed_credits > credit_limit:
        return RuleResult(
            passed=False,
            reason=(
                f"Proposed {proposed_credits} credits exceeds semester limit of {credit_limit}"
            ),
        )
    return RuleResult(
        passed=True,
        reason=f"Proposed {proposed_credits} credits within limit of {credit_limit}",
    )


# ---------------------------------------------------------------------------
# Schedule conflict detection
# ---------------------------------------------------------------------------


def _time_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def check_schedule_conflict(sections: list[dict]) -> RuleResult:
    """
    Return PASS if no two sections in *sections* overlap.
    Each section dict must have: section_id, days (list[str]),
    start_time (HH:MM), end_time (HH:MM).
    """
    conflicts: list[str] = []

    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            a, b = sections[i], sections[j]
            shared_days = set(a["days"]) & set(b["days"])
            if not shared_days:
                continue
            a_start = _time_to_minutes(a["start_time"])
            a_end = _time_to_minutes(a["end_time"])
            b_start = _time_to_minutes(b["start_time"])
            b_end = _time_to_minutes(b["end_time"])
            if a_start < b_end and b_start < a_end:
                day_list = sorted(shared_days)
                conflicts.append(
                    f"{a['section_id']} and {b['section_id']} conflict on {day_list}"
                )

    if conflicts:
        return RuleResult(passed=False, reason=f"Schedule conflicts: {'; '.join(conflicts)}")
    return RuleResult(passed=True, reason="No schedule conflicts")


# ---------------------------------------------------------------------------
# Financial aid hold detection
# ---------------------------------------------------------------------------


def check_financial_hold(holds: list[dict]) -> RuleResult:
    """
    Return PASS if there are no active (unresolved) financial holds that
    block registration. Each hold dict: {hold_type, resolved_date,
    blocks_registration, reason}.
    """
    blocking = [
        h for h in holds
        if h["hold_type"] == "financial"
        and h.get("resolved_date") is None
        and h.get("blocks_registration", False)
    ]
    if blocking:
        reasons = [h.get("reason", h["hold_type"]) for h in blocking]
        return RuleResult(
            passed=False,
            reason=f"Financial hold(s) block registration: {'; '.join(reasons)}",
        )
    return RuleResult(passed=True, reason="No active financial holds blocking registration")


# ---------------------------------------------------------------------------
# Administrative hold detection
# ---------------------------------------------------------------------------


def check_administrative_hold(holds: list[dict]) -> RuleResult:
    """
    Return PASS if all holds are resolved. Surfaces every active hold type
    and severity in the reason string. Each hold dict: {hold_type, severity,
    resolved_date, reason}.
    """
    active = [h for h in holds if h.get("resolved_date") is None]
    if active:
        summaries = [
            f"{h['hold_type']} ({h.get('severity', 'unknown')})" for h in active
        ]
        return RuleResult(passed=False, reason=f"Active hold(s): {', '.join(summaries)}")
    return RuleResult(passed=True, reason="No active administrative holds")


# ---------------------------------------------------------------------------
# Faculty workload threshold check
# ---------------------------------------------------------------------------


def check_faculty_workload(current_credits: int, max_credits: int) -> RuleResult:
    """Return PASS if current_credits < max_credits."""
    if current_credits >= max_credits:
        return RuleResult(
            passed=False,
            reason=(
                f"Faculty teaching {current_credits} credits meets or exceeds "
                f"cap of {max_credits}"
            ),
        )
    return RuleResult(
        passed=True,
        reason=f"Faculty teaching {current_credits} of {max_credits} allowed credits",
    )


# ---------------------------------------------------------------------------
# SLO achievement threshold comparison
# ---------------------------------------------------------------------------


def check_slo_threshold(proficiency_rate: float, target_rate: float) -> RuleResult:
    """Return PASS if proficiency_rate >= target_rate."""
    pct = f"{proficiency_rate:.1%}"
    tgt = f"{target_rate:.1%}"
    if proficiency_rate >= target_rate:
        return RuleResult(
            passed=True,
            reason=f"Proficiency rate {pct} meets target of {tgt}",
        )
    return RuleResult(
        passed=False,
        reason=f"Proficiency rate {pct} is below target of {tgt}",
    )


# ---------------------------------------------------------------------------
# Course sequencing validation
# ---------------------------------------------------------------------------


def check_course_sequencing(
    course_plan: list[str],
    prerequisites: list[dict],
    already_completed: list[str] | None = None,
) -> RuleResult:
    """
    Validate that a proposed multi-course plan respects prerequisite ordering:
    for each course in *course_plan*, all its prerequisites must either appear
    earlier in the plan or be in *already_completed*.

    This is distinct from check_prerequisites (which validates a single course
    against a student's completed history); this checks a full plan's internal
    consistency across semesters.
    """
    completed: set[str] = set(already_completed or [])

    prereq_map: dict[str, list[str]] = {}
    for p in prerequisites:
        prereq_map.setdefault(p["course_id"], []).append(p["prerequisite_course_id"])

    violations: list[str] = []
    seen: set[str] = set(completed)

    for course_id in course_plan:
        required = prereq_map.get(course_id, [])
        missing = [r for r in required if r not in seen]
        if missing:
            violations.append(f"{course_id} requires {', '.join(missing)} first")
        seen.add(course_id)

    if violations:
        return RuleResult(
            passed=False,
            reason=f"Sequencing violations: {'; '.join(violations)}",
        )
    return RuleResult(passed=True, reason="Course sequence is valid")
