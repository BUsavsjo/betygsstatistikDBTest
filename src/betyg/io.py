from __future__ import annotations

import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .constants import GradeSpec, NpSpec, PUBLIC_JSON_FILES
from .metrics import clean


PUBLIC_MINIMUM_COUNT = 10
PUBLIC_COUNT_FIELDS = {
    "betygsstatistik_oversikt.json": "antal_elever",
    "betygsstatistik_sv_sva.json": "antal_elever",
    "betygsstatistik_betygsfordelning_amne.json": "antal_betyg",
    "betygsstatistik_kontroll_betyg.json": "antal_giltiga_betyg",
    "np_andel_godkanda.json": "antal_np",
    "np_betyg_relation.json": "antal_jamforda",
}


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
    if not source_dir.exists():
        raise FileNotFoundError(f"Saknar JSON-output: {source_dir}")

    target_dir = processed_base / lasar / "json"
    with tempfile.TemporaryDirectory(prefix="betyg-publicering-") as tmp_dir:
        staging_dir = Path(tmp_dir)
        for filename in PUBLIC_JSON_FILES:
            source = source_dir / filename
            if source.exists():
                count_field = PUBLIC_COUNT_FIELDS.get(filename)
                if count_field is None:
                    shutil.copy2(source, staging_dir / filename)
                    continue

                with source.open("r", encoding="utf-8") as handle:
                    rows = json.load(handle)
                if not isinstance(rows, list):
                    raise ValueError(f"Förväntade en lista i {source}")

                # Intern output behålls komplett för analys. Bara grupper med minst
                # tio observationer skrivs till den publika processed-mappen.
                public_rows = []
                for row in rows:
                    try:
                        count = int(row.get(count_field, 0))
                    except (AttributeError, TypeError, ValueError):
                        count = 0
                    if count >= PUBLIC_MINIMUM_COUNT:
                        public_rows.append(row)
                write_json(staging_dir / filename, public_rows)

        # OneDrive kan vägra att ta bort själva json-mappen. Rensa därför dess
        # innehåll och kopiera sedan in den färdigbyggda whitelisten.
        target_dir.mkdir(parents=True, exist_ok=True)
        for stale_path in target_dir.iterdir():
            if stale_path.is_dir():
                shutil.rmtree(stale_path)
            else:
                stale_path.unlink()
        for public_file in staging_dir.iterdir():
            shutil.copy2(public_file, target_dir / public_file.name)

    return target_dir
