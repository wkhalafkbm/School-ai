"""Seed data loader — reads JSON fixtures, validates FK integrity, resets and fills the DB."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text, Boolean as SABoolean

DEFAULT_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Insertion order respects FK dependencies (parents before children).
INSERT_ORDER = [
    "programs",
    "faculty",
    "students",
    "courses",
    "schedule_sections",
    "enrollments",
    "prerequisites",
    "lms_signals",
    "onboarding_tasks",
    "support_cases",
    "interventions",
    "sponsorship_records",
    "financial_aid_records",
    "administrative_holds",
    "graduation_requirements",
    "student_course_progress",
    "career_pathways",
    "alumni_mentors",
    "workflow_items",
    "slos",
    "slo_assessments",
    "cohort_slo_history",
    "student_slo_results",
]

# FK checks: (child_table, fk_column, parent_table).
# Only non-nullable FKs need raising; nullable ones skip None values automatically.
FK_CHECKS = [
    ("students",               "program_id",              "programs"),
    ("courses",                "program_id",              "programs"),
    ("courses",                "instructor_id",           "faculty"),
    ("schedule_sections",      "course_id",               "courses"),
    ("schedule_sections",      "instructor_id",           "faculty"),
    ("enrollments",            "student_id",              "students"),
    ("enrollments",            "course_id",               "courses"),
    ("enrollments",            "section_id",              "schedule_sections"),
    ("prerequisites",          "course_id",               "courses"),
    ("prerequisites",          "prerequisite_course_id",  "courses"),
    ("lms_signals",            "student_id",              "students"),
    ("lms_signals",            "course_id",               "courses"),
    ("onboarding_tasks",       "student_id",              "students"),
    ("support_cases",          "student_id",              "students"),
    ("support_cases",          "assigned_to_faculty_id",  "faculty"),
    ("interventions",          "student_id",              "students"),
    ("interventions",          "case_id",                 "support_cases"),
    ("sponsorship_records",    "student_id",              "students"),
    ("sponsorship_records",    "program_id",              "programs"),
    ("financial_aid_records",  "student_id",              "students"),
    ("administrative_holds",   "student_id",              "students"),
    ("graduation_requirements","program_id",              "programs"),
    ("student_course_progress","student_id",              "students"),
    ("student_course_progress","program_id",              "programs"),
    ("career_pathways",        "student_id",              "students"),
    ("alumni_mentors",         "program_id",              "programs"),
    ("workflow_items",         "student_id",              "students"),
    ("slos",                   "course_id",               "courses"),
    ("slo_assessments",        "slo_id",                  "slos"),
    ("slo_assessments",        "course_id",               "courses"),
    ("cohort_slo_history",     "course_id",               "courses"),
    ("cohort_slo_history",     "slo_id",                  "slos"),
    ("student_slo_results",    "student_id",              "students"),
    ("student_slo_results",    "slo_id",                  "slos"),
    ("student_slo_results",    "course_id",               "courses"),
]


class SeedValidationError(Exception):
    """Raised when fixture referential integrity checks fail."""


def _load_fixtures(fixtures_dir: Path) -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = {}
    for table in INSERT_ORDER:
        path = fixtures_dir / f"{table}.json"
        with open(path) as f:
            data[table] = json.load(f)
    return data


def _validate(data: dict[str, list[dict]]) -> None:
    ids: dict[str, set] = {
        table: {r["id"] for r in records} for table, records in data.items()
    }
    errors: list[str] = []
    for child_table, fk_col, parent_table in FK_CHECKS:
        parent_ids = ids.get(parent_table, set())
        for i, record in enumerate(data.get(child_table, [])):
            value = record.get(fk_col)
            if value is None:
                continue
            if value not in parent_ids:
                errors.append(
                    f"{child_table}[{i}] id={record['id']!r}: "
                    f"{fk_col}={value!r} not found in {parent_table}"
                )
    if errors:
        raise SeedValidationError(
            f"Referential integrity errors ({len(errors)}):\n"
            + "\n".join(f"  • {e}" for e in errors)
        )


def _coerce_record(record: dict, table_obj) -> dict:
    """Cast fixture values to types the DB column expects."""
    bool_cols = {
        col.name
        for col in table_obj.columns
        if isinstance(col.type, SABoolean)
    }
    result = {}
    for k, v in record.items():
        if k in bool_cols and isinstance(v, str):
            result[k] = v.lower() not in ("false", "0", "")
        else:
            result[k] = v
    return result


def seed(db_url: str, fixtures_dir: Path = DEFAULT_FIXTURES_DIR) -> None:
    from app.models import Base

    data = _load_fixtures(fixtures_dir)
    _validate(data)

    engine = create_engine(db_url)

    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE TABLE " + ", ".join(INSERT_ORDER) + " CASCADE"
        ))

        for table in INSERT_ORDER:
            records = data[table]
            if not records:
                continue

            table_obj = Base.metadata.tables[table]
            known = {col.name for col in table_obj.columns}

            filtered = [
                {k: v for k, v in record.items() if k in known}
                for record in records
            ]

            # Normalize: every record must carry the same keys (union of all keys)
            all_keys = {k for r in filtered for k in r}
            filtered = [
                _coerce_record({k: r.get(k) for k in all_keys}, table_obj)
                for r in filtered
            ]

            conn.execute(table_obj.insert(), filtered)


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        sys.exit(1)

    try:
        seed(db_url)
        print("Seed complete.")
    except SeedValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
