"""
Rules engine unit tests — issue #7.

All rules are pure functions; no database required. Tests that reference
fixture data load the JSON files directly to stay grounded in real scenarios
without spinning up a database.
"""
import json
import os
from pathlib import Path

import pytest

from app.rules import (
    RuleResult,
    check_administrative_hold,
    check_course_sequencing,
    check_credit_limit,
    check_faculty_workload,
    check_financial_hold,
    check_gpa_trend,
    gpa_trend_status,
    check_prerequisites,
    check_schedule_conflict,
    check_slo_threshold,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load(name: str) -> list:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# RuleResult contract
# ---------------------------------------------------------------------------


def test_rule_result_has_passed_and_reason():
    r = RuleResult(passed=True, reason="ok")
    assert r.passed is True
    assert r.reason == "ok"


def test_rule_result_is_immutable():
    r = RuleResult(passed=False, reason="blocked")
    with pytest.raises((AttributeError, TypeError)):
        r.passed = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# check_credit_limit
# ---------------------------------------------------------------------------


def test_credit_limit_pass_within_cap():
    result = check_credit_limit(proposed_credits=9, credit_limit=18)
    assert result.passed
    assert "9" in result.reason


def test_credit_limit_pass_at_exact_cap():
    result = check_credit_limit(proposed_credits=18, credit_limit=18)
    assert result.passed


def test_credit_limit_fail_mariam_overload_scenario():
    # Mariam Al-Kandari (stu-002) tries to register 21 credits against an 18-credit cap.
    result = check_credit_limit(proposed_credits=21, credit_limit=18)
    assert not result.passed
    assert "21" in result.reason
    assert "18" in result.reason


def test_credit_limit_fail_exceeds_by_one():
    result = check_credit_limit(proposed_credits=19, credit_limit=18)
    assert not result.passed


def test_credit_limit_zero_proposed_always_passes():
    result = check_credit_limit(proposed_credits=0, credit_limit=18)
    assert result.passed


# ---------------------------------------------------------------------------
# check_financial_hold
# ---------------------------------------------------------------------------


def test_financial_hold_pass_no_holds():
    result = check_financial_hold(holds=[])
    assert result.passed


def test_financial_hold_pass_resolved_hold():
    result = check_financial_hold(holds=[
        {"hold_type": "financial", "resolved_date": "2024-10-01",
         "blocks_registration": True, "reason": "paid"},
    ])
    assert result.passed


def test_financial_hold_pass_non_blocking_financial_hold():
    result = check_financial_hold(holds=[
        {"hold_type": "financial", "resolved_date": None,
         "blocks_registration": False, "reason": "minor fine"},
    ])
    assert result.passed


def test_financial_hold_fail_mariam_active_blocking_hold():
    # hld-001: stu-002 Mariam has a blocking financial hold for unpaid tuition.
    holds = [h for h in load("administrative_holds.json") if h["student_id"] == "stu-002"]
    result = check_financial_hold(holds=holds)
    assert not result.passed
    assert result.reason  # surfaces a reason


def test_financial_hold_fail_active_blocking_hold():
    result = check_financial_hold(holds=[
        {"hold_type": "financial", "resolved_date": None,
         "blocks_registration": True, "reason": "Pending tuition payment"},
    ])
    assert not result.passed
    assert "Pending tuition payment" in result.reason


def test_financial_hold_ignores_non_financial_holds():
    result = check_financial_hold(holds=[
        {"hold_type": "academic", "resolved_date": None,
         "blocks_registration": True, "reason": "GPA probation"},
    ])
    assert result.passed


# ---------------------------------------------------------------------------
# check_administrative_hold
# ---------------------------------------------------------------------------


def test_administrative_hold_pass_no_holds():
    result = check_administrative_hold(holds=[])
    assert result.passed


def test_administrative_hold_pass_all_holds_resolved():
    result = check_administrative_hold(holds=[
        {"hold_type": "financial", "severity": "major",
         "resolved_date": "2024-11-01", "reason": "cleared"},
        {"hold_type": "medical", "severity": "minor",
         "resolved_date": "2024-10-15", "reason": "records submitted"},
    ])
    assert result.passed


def test_administrative_hold_fail_single_unresolved_hold():
    result = check_administrative_hold(holds=[
        {"hold_type": "academic", "severity": "major",
         "resolved_date": None, "reason": "GPA below 2.0"},
    ])
    assert not result.passed
    assert "academic" in result.reason


def test_administrative_hold_fail_surfaces_all_fixture_hold_types():
    # All 5 fixture holds are unresolved; the result must surface all types present.
    all_holds = load("administrative_holds.json")
    result = check_administrative_hold(holds=all_holds)
    assert not result.passed
    hold_types = {h["hold_type"] for h in all_holds}
    for hold_type in hold_types:
        assert hold_type in result.reason


def test_administrative_hold_fail_mixed_resolved_and_active():
    result = check_administrative_hold(holds=[
        {"hold_type": "library", "severity": "minor",
         "resolved_date": "2024-10-01", "reason": "fine paid"},
        {"hold_type": "medical", "severity": "minor",
         "resolved_date": None, "reason": "missing vaccination"},
    ])
    assert not result.passed
    assert "medical" in result.reason


# ---------------------------------------------------------------------------
# check_faculty_workload
# ---------------------------------------------------------------------------


def test_faculty_workload_pass_under_limit():
    result = check_faculty_workload(current_credits=9, max_credits=15)
    assert result.passed
    assert "9" in result.reason


def test_faculty_workload_fail_at_limit():
    result = check_faculty_workload(current_credits=12, max_credits=12)
    assert not result.passed


def test_faculty_workload_fail_over_limit():
    result = check_faculty_workload(current_credits=15, max_credits=12)
    assert not result.passed
    assert "15" in result.reason
    assert "12" in result.reason


def test_faculty_workload_fail_fixture_overloaded_faculty():
    # fac-001 is configured in the fixture with current_credits > max_credits.
    faculty = load("faculty.json")
    fac001 = next(f for f in faculty if f["id"] == "fac-001")
    result = check_faculty_workload(
        current_credits=fac001["current_credits"],
        max_credits=fac001["max_credits"],
    )
    assert not result.passed


def test_faculty_workload_pass_fixture_normal_faculty():
    faculty = load("faculty.json")
    fac002 = next(f for f in faculty if f["id"] == "fac-002")
    result = check_faculty_workload(
        current_credits=fac002["current_credits"],
        max_credits=fac002["max_credits"],
    )
    assert result.passed


# ---------------------------------------------------------------------------
# check_slo_threshold
# ---------------------------------------------------------------------------


def test_slo_threshold_pass_above_target():
    result = check_slo_threshold(proficiency_rate=0.733, target_rate=0.700)
    assert result.passed
    assert "73" in result.reason  # percentage representation


def test_slo_threshold_pass_exactly_at_target():
    result = check_slo_threshold(proficiency_rate=0.700, target_rate=0.700)
    assert result.passed


def test_slo_threshold_fail_below_target():
    result = check_slo_threshold(proficiency_rate=0.500, target_rate=0.700)
    assert not result.passed
    assert "50" in result.reason
    assert "70" in result.reason


def test_slo_threshold_fail_slo002_crs001_fixture_data():
    # sla-002: SLO-002 for CS101 has proficiency_rate=0.600 — below a 0.70 target.
    assessments = load("slo_assessments.json")
    sla002 = next(a for a in assessments if a["id"] == "sla-002")
    result = check_slo_threshold(
        proficiency_rate=sla002["proficiency_rate"],
        target_rate=0.700,
    )
    assert not result.passed


def test_slo_threshold_pass_slo003_crs001_fixture_data():
    # sla-003: SLO-003 for CS101 has proficiency_rate=0.833 — above a 0.70 target.
    assessments = load("slo_assessments.json")
    sla003 = next(a for a in assessments if a["id"] == "sla-003")
    result = check_slo_threshold(
        proficiency_rate=sla003["proficiency_rate"],
        target_rate=0.700,
    )
    assert result.passed


# ---------------------------------------------------------------------------
# check_schedule_conflict
# ---------------------------------------------------------------------------

def _sec(sid, days, start, end):
    return {"section_id": sid, "days": days, "start_time": start, "end_time": end}


def test_schedule_conflict_pass_no_sections():
    result = check_schedule_conflict(sections=[])
    assert result.passed


def test_schedule_conflict_pass_single_section():
    result = check_schedule_conflict(sections=[
        _sec("sec-001", ["Sun", "Tue"], "09:00", "10:15"),
    ])
    assert result.passed


def test_schedule_conflict_pass_different_days():
    result = check_schedule_conflict(sections=[
        _sec("sec-001", ["Sun", "Tue"], "09:00", "10:15"),
        _sec("sec-002", ["Mon", "Wed"], "09:00", "10:15"),
    ])
    assert result.passed


def test_schedule_conflict_pass_same_days_non_overlapping():
    result = check_schedule_conflict(sections=[
        _sec("sec-a", ["Mon", "Wed"], "09:00", "10:15"),
        _sec("sec-b", ["Mon", "Wed"], "10:15", "11:30"),
    ])
    assert result.passed


def test_schedule_conflict_fail_sec001_and_sec003_from_fixture():
    # sec-001 (CS101): Sun,Tue 09:00-10:15
    # sec-003 (MATH101-01): Sun,Tue,Thu 09:00-09:50  → overlaps on Sun & Tue
    sections = load("schedule_sections.json")
    sec001 = next(s for s in sections if s["id"] == "sec-001")
    sec003 = next(s for s in sections if s["id"] == "sec-003")

    result = check_schedule_conflict(sections=[
        _sec(sec001["id"], sec001["days"], sec001["start_time"], sec001["end_time"]),
        _sec(sec003["id"], sec003["days"], sec003["start_time"], sec003["end_time"]),
    ])
    assert not result.passed
    assert "sec-001" in result.reason
    assert "sec-003" in result.reason


def test_schedule_conflict_fail_sec004_and_sec010_from_fixture():
    # sec-004 (CS301): Mon,Wed 09:00-10:15
    # sec-010 (IS201): Mon,Wed 09:00-10:15  → exact overlap
    sections = load("schedule_sections.json")
    sec004 = next(s for s in sections if s["id"] == "sec-004")
    sec010 = next(s for s in sections if s["id"] == "sec-010")

    result = check_schedule_conflict(sections=[
        _sec(sec004["id"], sec004["days"], sec004["start_time"], sec004["end_time"]),
        _sec(sec010["id"], sec010["days"], sec010["start_time"], sec010["end_time"]),
    ])
    assert not result.passed


def test_schedule_conflict_fail_partially_overlapping_times():
    result = check_schedule_conflict(sections=[
        _sec("sec-a", ["Mon"], "09:00", "10:30"),
        _sec("sec-b", ["Mon"], "10:00", "11:15"),
    ])
    assert not result.passed


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------


def test_prerequisites_pass_no_prerequisites_required():
    # crs-013 (EE201) has no prerequisites in fixture.
    prereqs = load("prerequisites.json")
    result = check_prerequisites(
        course_id="crs-013",
        completed_courses=[],
        prerequisites=prereqs,
    )
    assert result.passed


def test_prerequisites_pass_all_met():
    # crs-002 (CS201) requires crs-001 with min_grade D.
    prereqs = load("prerequisites.json")
    result = check_prerequisites(
        course_id="crs-002",
        completed_courses=[{"course_id": "crs-001", "grade": "C"}],
        prerequisites=prereqs,
    )
    assert result.passed


def test_prerequisites_pass_exactly_minimum_grade():
    prereqs = load("prerequisites.json")
    # pre-001: crs-002 requires crs-001 with min_grade D
    result = check_prerequisites(
        course_id="crs-002",
        completed_courses=[{"course_id": "crs-001", "grade": "D"}],
        prerequisites=prereqs,
    )
    assert result.passed


def test_prerequisites_fail_course_not_completed():
    prereqs = load("prerequisites.json")
    result = check_prerequisites(
        course_id="crs-002",
        completed_courses=[],
        prerequisites=prereqs,
    )
    assert not result.passed
    assert "crs-001" in result.reason


def test_prerequisites_fail_grade_below_minimum():
    # pre-002: crs-004 requires crs-002 with min_grade C.  F < C.
    prereqs = load("prerequisites.json")
    result = check_prerequisites(
        course_id="crs-004",
        completed_courses=[{"course_id": "crs-002", "grade": "F"}],
        prerequisites=prereqs,
    )
    assert not result.passed
    assert "crs-002" in result.reason


def test_prerequisites_fail_identifies_missing_prereq_from_fixture():
    # stu-003 completed crs-001 with C (satisfies pre-001 for crs-002).
    # Attempting crs-004 (CS301) which requires crs-002 with C.
    # stu-003 has not completed crs-002 yet (it's active, not completed).
    prereqs = load("prerequisites.json")
    enrollments = load("enrollments.json")
    completed = [
        {"course_id": e["course_id"], "grade": e["grade"]}
        for e in enrollments
        if e["student_id"] == "stu-003" and e["status"] == "completed"
    ]
    result = check_prerequisites(
        course_id="crs-004",
        completed_courses=completed,
        prerequisites=prereqs,
    )
    assert not result.passed
    assert "crs-002" in result.reason


def test_prerequisites_pass_multiple_prerequisites_all_met():
    # crs-007 (CS450 Machine Learning) requires crs-004 (C) AND crs-022 (C).
    prereqs = load("prerequisites.json")
    result = check_prerequisites(
        course_id="crs-007",
        completed_courses=[
            {"course_id": "crs-004", "grade": "B"},
            {"course_id": "crs-022", "grade": "A-"},
        ],
        prerequisites=prereqs,
    )
    assert result.passed


def test_prerequisites_fail_one_of_multiple_prerequisites_missing():
    prereqs = load("prerequisites.json")
    # crs-007 requires crs-004 AND crs-022; only crs-004 provided.
    result = check_prerequisites(
        course_id="crs-007",
        completed_courses=[{"course_id": "crs-004", "grade": "B"}],
        prerequisites=prereqs,
    )
    assert not result.passed
    assert "crs-022" in result.reason


# ---------------------------------------------------------------------------
# check_course_sequencing
# ---------------------------------------------------------------------------


def test_course_sequencing_pass_empty_plan():
    result = check_course_sequencing(
        course_plan=[],
        prerequisites=[],
    )
    assert result.passed


def test_course_sequencing_pass_plan_with_no_dependencies():
    result = check_course_sequencing(
        course_plan=["crs-013", "crs-015", "crs-017"],
        prerequisites=load("prerequisites.json"),
    )
    assert result.passed


def test_course_sequencing_pass_prerequisites_in_correct_order():
    # Plan: crs-001 then crs-002 (crs-002 requires crs-001).
    result = check_course_sequencing(
        course_plan=["crs-001", "crs-002"],
        prerequisites=load("prerequisites.json"),
    )
    assert result.passed


def test_course_sequencing_pass_prerequisites_already_completed():
    result = check_course_sequencing(
        course_plan=["crs-002"],
        prerequisites=load("prerequisites.json"),
        already_completed=["crs-001"],
    )
    assert result.passed


def test_course_sequencing_fail_prerequisite_after_dependent():
    # Putting crs-002 before crs-001 in the plan violates sequencing.
    result = check_course_sequencing(
        course_plan=["crs-002", "crs-001"],
        prerequisites=load("prerequisites.json"),
    )
    assert not result.passed
    assert "crs-002" in result.reason


def test_course_sequencing_fail_missing_prerequisite_entirely():
    # Plan includes crs-002 but omits crs-001 and it's not already completed.
    result = check_course_sequencing(
        course_plan=["crs-002"],
        prerequisites=load("prerequisites.json"),
        already_completed=[],
    )
    assert not result.passed
    assert "crs-001" in result.reason


def test_course_sequencing_fail_multi_step_chain():
    # crs-004 requires crs-002; crs-002 requires crs-001.
    # Plan: [crs-004, crs-002, crs-001] — crs-004 appears before both its deps.
    result = check_course_sequencing(
        course_plan=["crs-004", "crs-002", "crs-001"],
        prerequisites=load("prerequisites.json"),
    )
    assert not result.passed
    assert "crs-004" in result.reason


def test_course_sequencing_pass_long_valid_chain():
    # crs-001 → crs-002 → crs-004 is valid ordering.
    result = check_course_sequencing(
        course_plan=["crs-001", "crs-002", "crs-004"],
        prerequisites=load("prerequisites.json"),
    )
    assert result.passed


# ---------------------------------------------------------------------------
# GPA trend detection — issue #64
# ---------------------------------------------------------------------------


def series(*pairs) -> list[dict]:
    """Build a chronologically ordered term series from (term, term_gpa) pairs."""
    return [
        {"term": term, "term_gpa": gpa, "cumulative_gpa": gpa}
        for term, gpa in pairs
    ]


def test_gpa_trend_skips_a_student_with_a_single_term():
    result = check_gpa_trend(series(("2024-Fall", 1.4)))
    assert result.flagged is False
    assert result.rules_fired == ()


def test_gpa_trend_flags_a_sharp_drop_in_the_latest_term():
    result = check_gpa_trend(series(("2024-Fall", 3.4), ("2025-Spring", 2.7)))
    assert result.flagged is True
    assert result.rules_fired == ("sharp_drop",)
    assert result.term == "2025-Spring"


def test_gpa_trend_reason_states_the_real_numbers_and_term():
    result = check_gpa_trend(series(("2024-Fall", 3.4), ("2025-Spring", 2.7)))
    assert "3.4" in result.reason
    assert "2.7" in result.reason
    assert "2025-Spring" in result.reason


def test_gpa_trend_flags_a_drop_of_exactly_the_sharp_threshold():
    # stu-003's seeded series moves in exact -0.5 steps; a strict comparison
    # would drop the demo's headline case.
    result = check_gpa_trend(series(("2024-Spring", 1.9), ("2024-Fall", 1.4)))
    assert result.flagged is True
    assert "sharp_drop" in result.rules_fired


def test_gpa_trend_does_not_flag_a_drop_just_under_the_sharp_threshold():
    result = check_gpa_trend(series(("2024-Spring", 3.0), ("2024-Fall", 2.51)))
    assert result.flagged is False


def test_gpa_trend_flags_two_consecutive_declines_totalling_past_the_threshold():
    result = check_gpa_trend(
        series(("2023-Fall", 2.9), ("2024-Spring", 2.65), ("2024-Fall", 2.4))
    )
    assert result.flagged is True
    assert result.rules_fired == ("sustained_decline",)
    assert result.term == "2024-Fall"


def test_gpa_trend_flags_two_declines_totalling_exactly_the_threshold():
    result = check_gpa_trend(
        series(("2023-Fall", 3.0), ("2024-Spring", 2.8), ("2024-Fall", 2.6))
    )
    assert result.flagged is True
    assert "sustained_decline" in result.rules_fired


def test_gpa_trend_does_not_flag_two_tiny_declines():
    # The total-drop floor is what stops this shape from firing.
    result = check_gpa_trend(
        series(("2023-Fall", 3.72), ("2024-Spring", 3.70), ("2024-Fall", 3.68))
    )
    assert result.flagged is False


def test_gpa_trend_does_not_flag_two_declines_just_under_the_total_threshold():
    result = check_gpa_trend(
        series(("2023-Fall", 3.0), ("2024-Spring", 2.8), ("2024-Fall", 2.62))
    )
    assert result.flagged is False


def test_gpa_trend_does_not_flag_a_single_small_decline_after_a_rise():
    result = check_gpa_trend(
        series(("2023-Fall", 2.0), ("2024-Spring", 2.5), ("2024-Fall", 2.2))
    )
    assert result.flagged is False


def test_gpa_trend_fires_both_rules_when_both_conditions_hold():
    result = check_gpa_trend(
        series(("2023-Fall", 3.5), ("2024-Spring", 3.4), ("2024-Fall", 2.8))
    )
    assert result.flagged is True
    assert set(result.rules_fired) == {"sharp_drop", "sustained_decline"}
    assert "sharp drop" in result.reason
    assert "sustained decline" in result.reason


def test_gpa_trend_does_not_flag_a_dip_that_recovered():
    result = check_gpa_trend(
        series(
            ("2022-Fall", 2.6), ("2023-Spring", 2.4), ("2023-Fall", 1.9),
            ("2024-Spring", 2.4), ("2024-Fall", 2.7),
        )
    )
    assert result.flagged is False


def test_gpa_trend_does_not_flag_a_steady_low_but_flat_series():
    result = check_gpa_trend(
        series(("2023-Fall", 1.8), ("2024-Spring", 1.8), ("2024-Fall", 1.8))
    )
    assert result.flagged is False
    assert result.rules_fired == ()


def test_gpa_trend_has_no_absolute_gpa_floor():
    # A 4.0 → 3.4 fall flags even though 3.4 is objectively fine — catching the
    # decline early is the whole point over the static "< 2.5" checks.
    result = check_gpa_trend(series(("2024-Spring", 4.0), ("2024-Fall", 3.4)))
    assert result.flagged is True


def fixture_series(student_id: str) -> list[dict]:
    """The committed student_term_gpa series for a student, chronologically ordered."""
    rows = [r for r in load("student_term_gpa.json") if r["student_id"] == student_id]
    assert rows, f"{student_id} has no student_term_gpa rows"
    return sorted(rows, key=lambda r: r["term_index"])


@pytest.mark.parametrize("student_id,expected_rule", [
    ("stu-003", "sharp_drop"),          # decline through the 2.0 line
    ("stu-015", "sharp_drop"),          # single sharp drop, cumulative still healthy
    ("stu-013", "sustained_decline"),   # two gentle declines
])
def test_gpa_trend_flags_the_seeded_declining_trajectories(student_id, expected_rule):
    result = check_gpa_trend(fixture_series(student_id))
    assert result.flagged is True, f"{student_id}: {result.reason}"
    assert expected_rule in result.rules_fired


@pytest.mark.parametrize("student_id", [
    "stu-004",  # dip then recovery
    "stu-005",  # steady high
    "stu-019",  # steady but flat around 2.3
])
def test_gpa_trend_leaves_the_seeded_non_declining_trajectories_alone(student_id):
    result = check_gpa_trend(fixture_series(student_id))
    assert result.flagged is False, f"{student_id} flagged: {result.reason}"


def test_gpa_trend_status_is_none_when_no_rule_fired():
    result = check_gpa_trend(
        series(("2023-Fall", 3.5), ("2024-Spring", 3.5), ("2024-Fall", 3.5))
    )
    assert gpa_trend_status(result, term_gpa=3.5, cumulative_gpa=3.5) is None


def test_gpa_trend_status_escalates_to_urgent_below_the_probation_line():
    result = check_gpa_trend(series(("2024-Spring", 1.9), ("2024-Fall", 1.4)))
    assert gpa_trend_status(result, term_gpa=1.4, cumulative_gpa=1.9) == "urgent"


def test_gpa_trend_status_is_needs_attention_for_a_sharp_drop_from_a_healthy_gpa():
    result = check_gpa_trend(series(("2024-Spring", 3.0), ("2024-Fall", 2.4)))
    assert gpa_trend_status(result, term_gpa=2.4, cumulative_gpa=2.8) == "needs_attention"


def test_gpa_trend_status_is_watch_for_a_sustained_decline_with_a_healthy_cumulative():
    result = check_gpa_trend(
        series(("2023-Fall", 2.9), ("2024-Spring", 2.65), ("2024-Fall", 2.4))
    )
    assert gpa_trend_status(result, term_gpa=2.4, cumulative_gpa=2.65) == "watch"


def test_gpa_trend_status_escalates_a_sustained_decline_when_the_cumulative_is_low():
    result = check_gpa_trend(
        series(("2023-Fall", 2.6), ("2024-Spring", 2.4), ("2024-Fall", 2.1))
    )
    assert gpa_trend_status(result, term_gpa=2.1, cumulative_gpa=2.4) == "needs_attention"


def test_gpa_trend_status_does_not_escalate_at_exactly_the_probation_line():
    result = check_gpa_trend(series(("2024-Spring", 2.6), ("2024-Fall", 2.0)))
    assert gpa_trend_status(result, term_gpa=2.0, cumulative_gpa=2.3) == "needs_attention"


def test_gpa_trend_status_stays_watch_at_exactly_the_cumulative_threshold():
    result = check_gpa_trend(
        series(("2023-Fall", 2.9), ("2024-Spring", 2.65), ("2024-Fall", 2.4))
    )
    assert gpa_trend_status(result, term_gpa=2.4, cumulative_gpa=2.5) == "watch"
