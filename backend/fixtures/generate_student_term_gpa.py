"""Generate student_term_gpa.json — the per-semester GPA series (see issue #63).

Run from anywhere to rewrite the fixture in place:

    .venv/bin/python backend/fixtures/generate_student_term_gpa.py

Edit this script rather than the JSON. `test_committed_term_gpa_fixture_matches_
its_generator` fails if the two drift apart.

Two invariants the arithmetic guarantees:

  * Every student's latest `cumulative_gpa` equals their `students.json` `gpa`
    scalar exactly — the series and the snapshot must never disagree. Term GPAs
    are therefore built in integer hundredths, with the final term solved so the
    series averages to the scalar, so no float drift can creep in.
  * Only the six deliberate trajectories may trip a downstream trend rule.
    Filler shapes are chosen so no single drop reaches 0.50 and no run of
    consecutive declines reaches 0.40.
"""
import json
from pathlib import Path

FIXTURES = Path(__file__).parent

# Chronological term order — term strings do not sort correctly as text.
TERM_ORDER = [
    "2021-Fall", "2022-Spring", "2022-Fall", "2023-Spring",
    "2023-Fall", "2024-Spring", "2024-Fall",
]

# The series ends at the term the `gpa` scalar reflects. Students admitted in
# this term have no completed prior terms, so they get a single row.
LATEST_TERM = "2024-Fall"

FILLER_TERMS = 3

# Hand-built term-GPA series (hundredths, oldest first) for the six deliberate
# trajectories. Each sums to len * scalar so the final cumulative lands exactly.
# stu-003 is capped at 3 terms by his 2023-Fall admission.
FEATURED = {
    "stu-003": [240, 190, 140],                # decline through the 2.0 line
    "stu-015": [270, 270, 270, 300, 240],      # sharp single-term drop (-0.60)
    "stu-013": [250, 255, 290, 265, 240],      # two gentle declines (-0.25 each)
    "stu-004": [260, 240, 190, 240, 270],      # dip then recovery
    "stu-005": [350, 345, 355, 350, 350],      # steady high
    "stu-019": [230, 235, 225, 230, 230],      # steady but flat around 2.3
}

# Filler shapes: offsets (hundredths) from the scalar for every term but the
# last, which is solved. All four are trend-safe — each ends on a rise or on a
# decline too small to accumulate past the thresholds.
FILLER_SHAPES = [
    [15, -20],
    [-15, 10],
    [5, -10],
    [-5, 5],
]

GPA_SCALE_MAX = 400


def terms_for(student, cap):
    """The last `cap` terms of the student's career, ending at LATEST_TERM."""
    start = TERM_ORDER.index(student["admission_term"])
    available = TERM_ORDER[start:TERM_ORDER.index(LATEST_TERM) + 1]
    return available[-cap:]


def filler_series(scalar, n, shape):
    """Term GPAs in hundredths whose mean is exactly `scalar`."""
    if n == 1:
        return [scalar]
    head = [max(0, min(GPA_SCALE_MAX, scalar + off)) for off in shape[: n - 1]]
    return head + [scalar * n - sum(head)]


def cumulative(series):
    """Running mean of the series in hundredths, rounding halves up."""
    means = []
    for i in range(len(series)):
        total, count = sum(series[: i + 1]), i + 1
        means.append((total * 2 + count) // (count * 2))
    return means


def build_rows():
    students = json.loads((FIXTURES / "students.json").read_text())

    rows = []
    filler_index = 0
    for student in students:
        if student["status"] != "enrolled" or student["gpa"] is None:
            continue

        scalar = round(student["gpa"] * 100)

        if student["id"] in FEATURED:
            series = FEATURED[student["id"]]
            terms = terms_for(student, len(series))
            assert len(terms) == len(series), (
                f"{student['id']} admitted {student['admission_term']} supports "
                f"only {len(terms)} terms, but its trajectory needs {len(series)}"
            )
            assert sum(series) == scalar * len(series), (
                f"{student['id']} trajectory {series} averages "
                f"{sum(series) / len(series) / 100}, not its scalar "
                f"{student['gpa']}"
            )
        else:
            terms = terms_for(student, FILLER_TERMS)
            series = filler_series(
                scalar, len(terms), FILLER_SHAPES[filler_index % len(FILLER_SHAPES)]
            )
            filler_index += 1

        for i, (term, term_gpa, cum) in enumerate(
            zip(terms, series, cumulative(series)), start=1
        ):
            rows.append({
                "id": f"stg-{len(rows) + 1:03d}",
                "student_id": student["id"],
                "term": term,
                "term_index": i,
                "term_gpa": round(term_gpa / 100, 2),
                "cumulative_gpa": round(cum / 100, 2),
                "data_source": "SIS",
            })

    return rows


def main():
    rows = build_rows()
    (FIXTURES / "student_term_gpa.json").write_text(
        json.dumps(rows, indent=2) + "\n"
    )
    students = len({r["student_id"] for r in rows})
    print(f"Wrote {len(rows)} rows across {students} students.")


if __name__ == "__main__":
    main()
