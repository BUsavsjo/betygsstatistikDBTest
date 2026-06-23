from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .constants import GradeSpec, NP_SPECS, SPECIAL_CODES, SPECS, VALID_GRADES
from .io import publish_processed_json, read_grade_files, read_np_files, write_csv, write_json
from .metrics import clean, eligibility, grade, grade_distribution, merit, overview, reached_all_subjects, sv_sva_group, sv_sva_summary
from .np_data import aggregate_np
from .skolenheter import skolenhet_lookup


def import_diagnostics(rows: list[dict[str, Any]], diagnostics: list[dict[str, Any]], spec: GradeSpec, lasar: str) -> dict[str, Any]:
    invalid_codes: list[dict[str, Any]] = []
    special_counts: dict[str, Counter[str]] = {subject: Counter() for subject in spec.subjects}
    for row in rows:
        for subject in spec.subjects + ["M1_betyg", "M2_betyg"]:
            value = clean(row.get(subject)).upper()
            if value in SPECIAL_CODES:
                special_counts.setdefault(subject, Counter())[value] += 1
            elif value and value not in VALID_GRADES:
                invalid_codes.append({
                    "source_file": row.get("_source_file"),
                    "source_row": row.get("_source_row"),
                    "column": subject,
                    "value": value,
                })
    return {
        "lasar": lasar,
        "arskurs": spec.arskurs,
        "source": "local_scb",
        "expected_columns": len(spec.columns),
        "imported_rows": len(rows),
        "diagnostics": diagnostics,
        "invalid_grade_codes": invalid_codes[:500],
        "invalid_grade_code_count": len(invalid_codes),
        "sv_sva_groups": Counter(row["sv_sva_grupp"] for row in rows),
        "special_codes_by_subject": {key: dict(value) for key, value in special_counts.items() if sum(value.values())},
    }


def build_year(
    lasar: str,
    *,
    publish: bool = False,
    base_dir: Path | None = None,
    raw_base: Path | None = None,
    np_raw_base: Path | None = None,
    output_base: Path | None = None,
    processed_base: Path | None = None,
) -> None:
    root = base_dir or Path(__file__).resolve().parent.parent.parent
    grade_raw = raw_base or root / "data" / "raw" / "betyg"
    np_raw = np_raw_base or root / "data" / "raw" / "np"
    output_root = output_base or root / "data" / "output"
    processed_root = processed_base or root / "data" / "processed"

    output_dir = output_root / lasar
    json_dir = output_dir / "json"
    diagnostics_dir = output_dir / "diagnostik"
    all_overview: list[dict[str, Any]] = []
    all_distribution: list[dict[str, Any]] = []
    all_sv_sva: list[dict[str, Any]] = []
    all_np_pass: list[dict[str, Any]] = []
    all_np_relation: list[dict[str, Any]] = []
    grade_batches: list[tuple[GradeSpec, list[dict[str, Any]], list[dict[str, Any]]]] = []
    manifest = {"lasar": lasar, "source": "local_scb", "arskurser": [], "np_arskurser": [], "files": []}
    grade_rows_by_key: dict[tuple[int, str, str], dict[str, str]] = {}
    school_codes: set[str] = set()

    for spec in SPECS.values():
        rows, diagnostics = read_grade_files(grade_raw, lasar, spec)
        for row in rows:
            merit16, merit17 = merit(row, spec.subjects)
            row["arskurs"] = spec.arskurs
            row["lasar"] = lasar
            row["sv_sva_grupp"] = sv_sva_group(row)
            row["meritvarde_16"] = merit16
            row["meritvarde_17"] = merit17
            row["uppnatt_alla_amnen"] = reached_all_subjects(row, spec.subjects)
            if spec.arskurs == 9:
                row.update(eligibility(row, spec.subjects))
            key = (spec.arskurs, clean(row.get("PersonNr")).upper(), clean(row.get("Skolenhetskod")))
            grade_rows_by_key[key] = row
            school_codes.add(clean(row.get("Skolenhetskod")))

        write_csv(output_dir / f"betyg_ak{spec.arskurs}_rensad.csv", rows, spec.columns + [
            "arskurs", "lasar", "sv_sva_grupp", "meritvarde_16", "meritvarde_17", "uppnatt_alla_amnen",
            "behorig_yrkesprogram", "behorig_hogskoleforberedande_es",
            "behorig_hogskoleforberedande_ek_hu_sa", "behorig_hogskoleforberedande_na_te",
            "behorig_hogskoleforberedande_nagot_program",
        ])
        write_json(diagnostics_dir / f"import_betyg_ak{spec.arskurs}.json", import_diagnostics(rows, diagnostics, spec, lasar))
        grade_batches.append((spec, rows, diagnostics))

    np_rows_by_spec: dict[int, list[tuple[dict[str, str], dict[str, str] | None]]] = {}
    for spec in NP_SPECS.values():
        rows, diagnostics = read_np_files(np_raw, lasar, spec)
        matched = 0
        linked_rows: list[tuple[dict[str, str], dict[str, str] | None]] = []
        for row in rows:
            school_codes.add(clean(row.get("Skolenhetskod")))
            key = (spec.arskurs, clean(row.get("PersonNr")).upper(), clean(row.get("Skolenhetskod")))
            grade_row = grade_rows_by_key.get(key)
            if grade_row:
                matched += 1
            linked_rows.append((row, grade_row))
        np_rows_by_spec[spec.arskurs] = linked_rows
        write_json(diagnostics_dir / f"import_np_ak{spec.arskurs}.json", {
            "lasar": lasar,
            "arskurs": spec.arskurs,
            "source": "local_scb_np",
            "expected_columns": len(spec.columns),
            "imported_rows": len(rows),
            "matched_grade_rows": matched,
            "diagnostics": diagnostics,
        })
        if rows:
            manifest["np_arskurser"].append({"arskurs": spec.arskurs, "rows": len(rows), "matched_grade_rows": matched})
        manifest["files"].extend({**diagnostic, "kind": f"np_ak{spec.arskurs}"} for diagnostic in diagnostics if diagnostic.get("message") == "file_read")

    lookup = skolenhet_lookup(school_codes)
    write_json(json_dir / "skolenheter_lookup.json", lookup)
    for spec, rows, diagnostics in grade_batches:
        if rows:
            all_overview.extend(overview(rows, lasar, spec.arskurs, lookup))
            all_distribution.extend(grade_distribution(rows, lasar, spec.arskurs, spec.subjects, lookup))
            all_sv_sva.extend(sv_sva_summary(rows, lasar, spec.arskurs, lookup))
            manifest["arskurser"].append({"arskurs": spec.arskurs, "rows": len(rows)})
        manifest["files"].extend(diagnostic for diagnostic in diagnostics if diagnostic.get("message") == "file_read")
    for arskurs, linked_rows in np_rows_by_spec.items():
        np_pass, np_relation = aggregate_np(linked_rows, lasar, arskurs, lookup)
        all_np_pass.extend(np_pass)
        all_np_relation.extend(np_relation)

    write_json(json_dir / "manifest.json", manifest)
    write_json(json_dir / "betygsstatistik_oversikt.json", all_overview)
    write_json(json_dir / "betygsstatistik_betygsfordelning_amne.json", all_distribution)
    write_json(json_dir / "betygsstatistik_sv_sva.json", all_sv_sva)
    write_json(json_dir / "np_andel_godkanda.json", all_np_pass)
    write_json(json_dir / "np_betyg_relation.json", all_np_relation)
    print(f"Created local grade statistics in {json_dir}")
    if publish:
        processed_dir = publish_processed_json(output_root, processed_root, lasar)
        print(f"Copied public processed JSON to {processed_dir}")
