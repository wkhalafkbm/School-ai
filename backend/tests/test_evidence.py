"""
Evidence & Confidence Builder unit tests — issue #10.

Pure function tests; no database required. Fixture data loaded directly
from JSON files to stay grounded in real student scenarios.
"""
import json
from pathlib import Path

import pytest

from app.evidence import EvidenceOutput, build_evidence
from app.rules import RuleResult

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load(name: str) -> list:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# Shared signal builders
# ---------------------------------------------------------------------------

def _full_signals() -> dict:
    """Full LMS + SIS + grades + SLO + strong historical match count."""
    lms = load("lms_signals.json")
    students = load("students.json")
    enrollments = load("enrollments.json")
    slo_results = load("student_slo_results.json")

    student = next(s for s in students if s["id"] == "stu-003")
    return {
        "lms_data": [sig for sig in lms if sig["student_id"] == "stu-003"],
        "sis_data": student,
        "grades": [e for e in enrollments if e["student_id"] == "stu-003"],
        "slo_results": [r for r in slo_results if r["student_id"] == "stu-003"],
        "prerequisites": None,
        "historical_matches": 10,
        "moment": "academic_risk_engagement",
    }


def _sparse_signals() -> dict:
    """No LMS data, no SIS data, zero historical matches."""
    return {
        "lms_data": None,
        "sis_data": None,
        "grades": None,
        "slo_results": None,
        "prerequisites": None,
        "historical_matches": 0,
        "moment": "academic_risk_engagement",
    }


# ---------------------------------------------------------------------------
# Cycle 1 — full signals produce High confidence with correct output shape
# ---------------------------------------------------------------------------


def test_full_signals_return_high_confidence():
    result = build_evidence(_full_signals())
    assert result.confidence == "High"


def test_output_is_evidence_output_dataclass():
    result = build_evidence(_full_signals())
    assert isinstance(result, EvidenceOutput)
    assert hasattr(result, "rationale")
    assert hasattr(result, "evidence")
    assert hasattr(result, "confidence")


# ---------------------------------------------------------------------------
# Cycle 2 — no LMS data + 0 matches → Low confidence
# ---------------------------------------------------------------------------


def test_no_lms_and_no_sis_returns_low_confidence():
    result = build_evidence(_sparse_signals())
    assert result.confidence == "Low"


# ---------------------------------------------------------------------------
# Cycle 3 — both data sources but only 1 historical match → Low
# ---------------------------------------------------------------------------


def test_single_historical_match_returns_low_confidence():
    lms = load("lms_signals.json")
    students = load("students.json")
    student = next(s for s in students if s["id"] == "stu-003")
    signals = {
        "lms_data": [sig for sig in lms if sig["student_id"] == "stu-003"],
        "sis_data": student,
        "grades": None,
        "slo_results": None,
        "prerequisites": None,
        "historical_matches": 1,
        "moment": "academic_risk_engagement",
    }
    result = build_evidence(signals)
    assert result.confidence == "Low"


# ---------------------------------------------------------------------------
# Cycle 4 — both data sources + 3 matches → Medium
# ---------------------------------------------------------------------------


def test_moderate_historical_matches_returns_medium_confidence():
    lms = load("lms_signals.json")
    students = load("students.json")
    student = next(s for s in students if s["id"] == "stu-003")
    signals = {
        "lms_data": [sig for sig in lms if sig["student_id"] == "stu-003"],
        "sis_data": student,
        "grades": None,
        "slo_results": None,
        "prerequisites": None,
        "historical_matches": 3,
        "moment": "academic_risk_engagement",
    }
    result = build_evidence(signals)
    assert result.confidence == "Medium"


# ---------------------------------------------------------------------------
# Cycle 5 — rationale is ≤2 sentences
# ---------------------------------------------------------------------------


def test_rationale_is_at_most_two_sentences():
    result = build_evidence(_full_signals())
    sentences = [s.strip() for s in result.rationale.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    assert len(sentences) <= 2


def test_sparse_rationale_is_at_most_two_sentences():
    result = build_evidence(_sparse_signals())
    sentences = [s.strip() for s in result.rationale.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    assert len(sentences) <= 2


# ---------------------------------------------------------------------------
# Cycle 6 — rationale uses operational language
# ---------------------------------------------------------------------------

OPERATIONAL_TERMS = {
    "needs attention", "readiness gap", "support recommended",
    "at risk", "on track", "intervention", "academic support",
    "engagement gap", "progression risk",
}


def test_rationale_uses_operational_language():
    result = build_evidence(_full_signals())
    lower = result.rationale.lower()
    assert any(term in lower for term in OPERATIONAL_TERMS), (
        f"Rationale missing operational language: {result.rationale!r}"
    )


def test_sparse_rationale_uses_operational_language():
    result = build_evidence(_sparse_signals())
    lower = result.rationale.lower()
    assert any(term in lower for term in OPERATIONAL_TERMS), (
        f"Rationale missing operational language: {result.rationale!r}"
    )


# ---------------------------------------------------------------------------
# Cycle 7 — evidence block omits absent signal categories
# ---------------------------------------------------------------------------


def test_evidence_block_excludes_absent_categories():
    signals = _full_signals()
    signals["prerequisites"] = None
    signals["slo_results"] = None
    result = build_evidence(signals)
    assert "prerequisites" not in result.evidence
    assert "slo_results" not in result.evidence


def test_evidence_block_includes_present_categories():
    result = build_evidence(_full_signals())
    assert "lms_data" in result.evidence
    assert "sis_data" in result.evidence
    assert "grades" in result.evidence


# ---------------------------------------------------------------------------
# Cycle 8 — RuleResult is rejected at the boundary
# ---------------------------------------------------------------------------


def test_rule_result_raises_type_error():
    rule_result = RuleResult(passed=False, reason="Missing prerequisites: crs-001")
    with pytest.raises(TypeError, match="RuleResult"):
        build_evidence(rule_result)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cycle 9 — output shape is consistent across all five moments
# ---------------------------------------------------------------------------

MOMENTS = [
    "admissions",
    "enrollment",
    "academic_risk_engagement",
    "progression",
    "career",
]


@pytest.mark.parametrize("moment", MOMENTS)
def test_output_shape_consistent_across_moments(moment):
    signals = _full_signals()
    signals["moment"] = moment
    result = build_evidence(signals)
    assert isinstance(result.rationale, str)
    assert isinstance(result.evidence, dict)
    assert result.confidence in {"High", "Medium", "Low"}
