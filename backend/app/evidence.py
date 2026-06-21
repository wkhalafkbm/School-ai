"""
Evidence & Confidence Builder — issue #10.

Converts raw student signals into the three-layer evidence structure used
across all AI recommendation moments: a short rationale, an expandable
evidence block, and a qualitative confidence label.

Deterministic rule results (RuleResult) bypass this module entirely and
must NOT be passed here.
"""
from dataclasses import dataclass

from app.rules import RuleResult

# Minimum historical matches required to avoid Low confidence penalty.
_LOW_MATCH_THRESHOLD = 2
# Minimum historical matches for High confidence.
_HIGH_MATCH_THRESHOLD = 5

_SIGNAL_KEYS = ("lms_data", "sis_data", "grades", "slo_results", "prerequisites")


@dataclass(frozen=True)
class EvidenceOutput:
    rationale: str
    evidence: dict
    confidence: str  # "High", "Medium", or "Low"


def build_evidence(signals: dict) -> EvidenceOutput:
    """
    Build the three-layer evidence structure from raw student signals.

    Raises TypeError if a RuleResult is passed — deterministic rule outputs
    bypass this module and must be returned directly to the caller.
    """
    if isinstance(signals, RuleResult):
        raise TypeError(
            "RuleResult must not pass through the Evidence Builder. "
            "Return rule results directly to the caller."
        )

    lms_data = signals.get("lms_data")
    sis_data = signals.get("sis_data")
    historical_matches = signals.get("historical_matches", 0)

    confidence = _compute_confidence(lms_data, sis_data, historical_matches)
    rationale = _build_rationale(signals, confidence)
    evidence = _build_evidence_block(signals)

    return EvidenceOutput(
        rationale=rationale,
        evidence=evidence,
        confidence=confidence,
    )


def _compute_confidence(lms_data, sis_data, historical_matches: int) -> str:
    if lms_data is None or sis_data is None or historical_matches < _LOW_MATCH_THRESHOLD:
        return "Low"
    if historical_matches >= _HIGH_MATCH_THRESHOLD:
        return "High"
    return "Medium"


def _build_rationale(signals: dict, confidence: str) -> str:
    lms_data = signals.get("lms_data")
    sis_data = signals.get("sis_data")

    if confidence == "High":
        if lms_data and any(s.get("risk_flag") in ("high", "medium") for s in lms_data):
            return (
                "Student engagement signals indicate an academic support need. "
                "Intervention is recommended based on strong corroborating evidence."
            )
        gpa = sis_data.get("gpa") if sis_data else None
        if gpa is not None and gpa < 2.5:
            return (
                "Student shows a readiness gap relative to academic benchmarks. "
                "Support recommended based on complete LMS and SIS signal alignment."
            )
        return (
            "Student profile is well-documented and evidence supports a confident recommendation. "
            "Review the expanded evidence block for full signal detail."
        )

    if confidence == "Medium":
        return (
            "Partial signals suggest the student may need attention, "
            "though limited historical similarity reduces certainty."
        )

    # Low confidence
    if lms_data is None and sis_data is None:
        return (
            "Insufficient data is available to make a confident assessment. "
            "Academic support is recommended as a precautionary measure."
        )
    if lms_data is None:
        return (
            "LMS engagement data is unavailable for this student. "
            "A manual review is recommended to identify any progression risk."
        )
    if sis_data is None:
        return (
            "SIS record is missing for this student. "
            "Academic support is recommended until full data can be obtained."
        )
    return (
        "Too few analogous student records exist to derive a reliable comparison. "
        "Treat this as a needs attention case pending additional data collection."
    )


def _build_evidence_block(signals: dict) -> dict:
    return {
        key: signals[key]
        for key in _SIGNAL_KEYS
        if signals.get(key) is not None
    }
