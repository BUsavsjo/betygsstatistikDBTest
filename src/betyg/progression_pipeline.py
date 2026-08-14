from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import SPECS
from .io import read_grade_files, write_json
from .progression import (
    build_progression_document,
    match_cohort,
    source_school_year,
)


def build_progression_files(
    grade_raw: Path,
    output_dir: Path,
    ak9_lasar: str,
    ak9_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ak6_lasar = source_school_year(ak9_lasar)
    ak6_rows, source_diagnostics = read_grade_files(
        grade_raw,
        ak6_lasar,
        SPECS[6],
    )

    if not ak6_rows or not ak9_rows:
        public_document: dict[str, Any] = {
            "schema_version": 1,
            "status": "saknar_underlag",
            "source": "local_scb_progression",
            "ak6_lasar": ak6_lasar,
            "ak9_lasar": ak9_lasar,
            "sekretessgrans": 10,
            "segment": [],
        }
        diagnostics: dict[str, Any] = {
            "status": "saknar_underlag",
            "ak6_lasar": ak6_lasar,
            "ak9_lasar": ak9_lasar,
            "ak6_rader": len(ak6_rows),
            "ak9_rader": len(ak9_rows),
            "source_diagnostics": source_diagnostics,
        }
    else:
        matched_rows, match_diagnostics = match_cohort(ak6_rows, ak9_rows)
        public_document = build_progression_document(
            matched_rows,
            ak9_rows,
            ak6_lasar,
            ak9_lasar,
        )
        diagnostics = {
            "status": "ok",
            "ak6_lasar": ak6_lasar,
            "ak9_lasar": ak9_lasar,
            **match_diagnostics,
            "source_diagnostics": source_diagnostics,
        }

    write_json(
        output_dir / "json" / "betygsprogression_ak6_ak9.json",
        public_document,
    )
    write_json(
        output_dir / "diagnostik" / "progression_ak6_ak9.json",
        diagnostics,
    )
    return public_document
