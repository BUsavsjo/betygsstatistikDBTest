from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from .constants import GradeSpec, NpSpec, PUBLIC_JSON_FILES
from .metrics import clean


def read_text_rows(path: Path) -> list[list[str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [row for row in csv.reader(handle, delimiter=";") if any(clean(cell) for cell in row)]
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Could not decode {path}")


def read_grade_files(raw_base: Path, lasar: str, spec: GradeSpec) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    raw_dir = raw_base / lasar / spec.raw_folder
    diagnostics: list[dict[str, Any]] = []
    records: list[dict[str, str]] = []

    if not raw_dir.exists():
        diagnostics.append({"level": "warning", "message": "raw_folder_missing", "folder": str(raw_dir)})
        return records, diagnostics

    for path in sorted(raw_dir.glob("*.txt")):
        rows = read_text_rows(path)
        diagnostics.append({"level": "info", "message": "file_read", "file": path.name, "rows": len(rows)})
        for row_number, row in enumerate(rows, start=1):
            if len(row) != len(spec.columns):
                diagnostics.append({
                    "level": "error",
                    "message": "wrong_column_count",
                    "file": path.name,
                    "row": row_number,
                    "expected": len(spec.columns),
                    "actual": len(row),
                })
                continue
            record = {col: clean(row[index]) for index, col in enumerate(spec.columns)}
            record["_source_file"] = path.name
            record["_source_row"] = str(row_number)
            records.append(record)

    return records, diagnostics


def read_np_files(raw_base: Path, lasar: str, spec: NpSpec) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    raw_dir = raw_base / lasar / spec.raw_folder
    diagnostics: list[dict[str, Any]] = []
    records: list[dict[str, str]] = []

    if not raw_dir.exists():
        diagnostics.append({"level": "warning", "message": "raw_folder_missing", "folder": str(raw_dir)})
        return records, diagnostics

    for path in sorted(raw_dir.glob("*.txt")):
        rows = read_text_rows(path)
        diagnostics.append({"level": "info", "message": "file_read", "file": path.name, "rows": len(rows)})
        for row_number, row in enumerate(rows, start=1):
            normalized_row = normalize_np_row(spec, row)
            if normalized_row is None:
                diagnostics.append({
                    "level": "error",
                    "message": "wrong_column_count",
                    "file": path.name,
                    "row": row_number,
                    "expected": len(spec.columns),
                    "actual": len(row),
                })
                continue
            record = {col: clean(normalized_row[index]) for index, col in enumerate(spec.columns)}
            record["_source_file"] = path.name
            record["_source_row"] = str(row_number)
            records.append(record)

    return records, diagnostics


def normalize_np_row(spec: NpSpec, row: list[str]) -> list[str] | None:
    if len(row) == len(spec.columns):
        return row
    for candidate in spec.alternate_columns or []:
        if len(row) == len(candidate):
            values = {col: clean(row[index]) for index, col in enumerate(candidate)}
            return [values.get(col, "") for col in spec.columns]
    return None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def publish_processed_json(output_base: Path, processed_base: Path, lasar: str) -> Path:
    source_dir = output_base / lasar / "json"
    target_dir = processed_base / lasar / "json"
    if not source_dir.exists():
        raise FileNotFoundError(f"Saknar JSON-output: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in PUBLIC_JSON_FILES:
        source = source_dir / filename
        if source.exists():
            shutil.copy2(source, target_dir / filename)

    return target_dir
