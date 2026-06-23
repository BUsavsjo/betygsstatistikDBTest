from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_BASE = BASE_DIR / "data" / "raw" / "betyg"
NP_RAW_BASE = BASE_DIR / "data" / "raw" / "np"
OUTPUT_BASE = BASE_DIR / "data" / "output"

VALID_GRADES = {"A", "B", "C", "D", "E", "F"}
PASSING_GRADES = {"A", "B", "C", "D", "E"}
SPECIAL_CODES = {"", "2", "3", "9", "Y", "Z"}
GRADE_POINTS = {"A": 20.0, "B": 17.5, "C": 15.0, "D": 12.5, "E": 10.0, "F": 0.0}

AK6_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod", "Klass", "Fornamn", "Efternamn",
    "Bl", "En", "Hkk", "Idh", "Ma", "M1_sprak", "M1_betyg", "M2_sprak", "M2_betyg",
    "Modm_anm", "Modmalbe", "Mu", "No", "Bi", "Fy", "Ke", "So", "Ge", "Hi", "Re", "Sh",
    "Sl", "Sv", "Sva", "Tn", "Tk", "Ovr",
]

AK9_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod", "Klass", "Fornamn", "Efternamn",
    "Bl", "En", "Hkk", "Idh", "Ma", "M1_sprak", "M1_betyg", "M2_sprak", "M2_betyg",
    "ML_sprak", "ML_betyg", "Mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "Sl",
    "Sv", "Sva", "Tn", "Tk", "Ovr",
]

AK6_SUBJECTS = ["Bl", "En", "Hkk", "Idh", "Ma", "Mu", "No", "Bi", "Fy", "Ke", "So", "Ge", "Hi", "Re", "Sh", "Sl", "Sv", "Sva", "Tn", "Tk", "Ovr"]
AK9_SUBJECTS = ["Bl", "En", "Hkk", "Idh", "Ma", "Mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "Sl", "Sv", "Sva", "Tn", "Tk", "Ovr"]


@dataclass(frozen=True)
class GradeSpec:
    arskurs: int
    raw_folder: str
    columns: list[str]
    subjects: list[str]


SPECS = {
    6: GradeSpec(6, "ak6", AK6_COLUMNS, AK6_SUBJECTS),
    9: GradeSpec(9, "ak9", AK9_COLUMNS, AK9_SUBJECTS),
}

NP_AK3_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_PR", "MA_B_PR", "MA_C_PR", "MA_D_PR", "MA_E_PR", "MA_F_PR", "MA_G_PR",
    "MA_G1_PR", "MA_G2_PR", "MA_B_POANG", "MA_C_POANG", "MA_D_POANG", "MA_E_POANG",
    "MA_F_POANG", "MA_G_POANG", "MA_G1_POANG", "MA_G2_POANG",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_PR", "SV_B_PR", "SV_C_PR", "SV_D_PR", "SV_E_PR",
    "SV_F_PR", "SV_G_PR", "SV_H_PR", "SV_B_POANG", "SV_C_POANG",
]

NP_AK6_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_DELT", "MA_B_DELT", "MA_C_DELT", "MA_D_DELT", "MA_E_DELT", "MA_PROVB",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_DELT", "SV_B_DELT", "SV_C_DELT",
    "SV_A_PRP", "SV_B_PRP", "SV_C_PRP", "SV_PROVB",
    "EN_GRUPP", "EN_A_DELT", "EN_B_DELT", "EN_C_DELT", "EN_A_PRP", "EN_B_PRP", "EN_C_PRP", "EN_PROVB",
]

NP_AK9_COLUMNS = [
    "System", "Datum", "Version", "PersonNr", "Skolenhetskod",
    "MA_GRUPP", "MA_A_DELT", "MA_B_DELT", "MA_C_DELT", "MA_D_DELT", "MA_PROVB",
    "SV_GRUPP", "SV_KURSPLAN", "SV_A_PRP", "SV_B_PRP", "SV_C_PRP", "SV_PROVB",
    "EN_GRUPP", "EN_A_PRP", "EN_B_PRP", "EN_C_PRP", "EN_PROVB",
    "NO_PROV", "NO_A_DELT", "NO_B_DELT", "NO_GRUPP", "NO_PROVB",
    "SO_PROV", "SO_A_DELT", "SO_B_DELT", "SO_GRUPP", "SO_PROVB",
]


@dataclass(frozen=True)
class NpSpec:
    arskurs: int
    raw_folder: str
    columns: list[str]


NP_SPECS = {
    3: NpSpec(3, "ak3", NP_AK3_COLUMNS),
    6: NpSpec(6, "ak6", NP_AK6_COLUMNS),
    9: NpSpec(9, "ak9", NP_AK9_COLUMNS),
}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def grade(value: Any) -> str | None:
    value = clean(value).upper()
    return value if value in VALID_GRADES else None


def is_passing(value: Any) -> bool:
    return grade(value) in PASSING_GRADES


def read_text_rows(path: Path) -> list[list[str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [row for row in csv.reader(handle, delimiter=";") if any(clean(cell) for cell in row)]
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Could not decode {path}")


def read_grade_files(lasar: str, spec: GradeSpec) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    raw_dir = RAW_BASE / lasar / spec.raw_folder
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
            record = {col: clean(row[i]) for i, col in enumerate(spec.columns)}
            record["_source_file"] = path.name
            record["_source_row"] = str(row_number)
            records.append(record)

    return records, diagnostics


def read_np_files(lasar: str, spec: NpSpec) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    raw_dir = NP_RAW_BASE / lasar / spec.raw_folder
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
            record = {col: clean(row[i]) for i, col in enumerate(spec.columns)}
            record["_source_file"] = path.name
            record["_source_row"] = str(row_number)
            records.append(record)

    return records, diagnostics


def sv_sva_group(row: dict[str, str]) -> str:
    has_sv = grade(row.get("Sv")) is not None
    has_sva = grade(row.get("Sva")) is not None
    if has_sv and has_sva:
        return "SV_och_SVA"
    if has_sv:
        return "SV"
    if has_sva:
        return "SVA"
    return "oklar"


def merit(row: dict[str, str], subjects: list[str]) -> tuple[float, float]:
    points: list[float] = []
    sv_sva_points: list[float] = []
    for subject in subjects:
        g = grade(row.get(subject))
        if g is None:
            continue
        if subject in {"Sv", "Sva"}:
            sv_sva_points.append(GRADE_POINTS[g])
        else:
            points.append(GRADE_POINTS[g])
    if sv_sva_points:
        points.append(max(sv_sva_points))
    merit_16 = sum(sorted(points, reverse=True)[:16])

    language_points = [
        GRADE_POINTS[g]
        for col in ("M1_betyg", "M2_betyg")
        if (g := grade(row.get(col))) in PASSING_GRADES
    ]
    merit_17 = merit_16 + max(language_points, default=0.0)
    return round(merit_16, 2), round(merit_17, 2)


def passed_other_subjects(row: dict[str, str], subjects: list[str]) -> int:
    core = {"Sv", "Sva", "En", "Ma"}
    return sum(1 for subject in subjects if subject not in core and is_passing(row.get(subject)))


def eligibility(row: dict[str, str], subjects: list[str]) -> dict[str, bool]:
    core = (is_passing(row.get("Sv")) or is_passing(row.get("Sva"))) and is_passing(row.get("En")) and is_passing(row.get("Ma"))
    other_count = passed_other_subjects(row, subjects)
    es = core and other_count >= 9
    ek_hu_sa = es and all(is_passing(row.get(s)) for s in ("Ge", "Hi", "Re", "Sh"))
    na_te = es and all(is_passing(row.get(s)) for s in ("Bi", "Fy", "Ke"))
    return {
        "behorig_yrkesprogram": core and other_count >= 5,
        "behorig_hogskoleforberedande_es": es,
        "behorig_hogskoleforberedande_ek_hu_sa": ek_hu_sa,
        "behorig_hogskoleforberedande_na_te": na_te,
        "behorig_hogskoleforberedande_nagot_program": es or ek_hu_sa or na_te,
    }


def reached_all_subjects(row: dict[str, str], subjects: list[str]) -> bool:
    relevant = [subject for subject in subjects if subject not in {"Sv", "Sva"} and grade(row.get(subject)) is not None]
    has_sv_sva = grade(row.get("Sv")) is not None or grade(row.get("Sva")) is not None
    if not relevant and not has_sv_sva:
        return False
    return all(is_passing(row.get(subject)) for subject in relevant) and (not has_sv_sva or is_passing(row.get("Sv")) or is_passing(row.get("Sva")))


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def percentage(part: int, total: int) -> float | None:
    return round(part / total * 100, 2) if total else None


def grade_relation(term_grade: str | None, np_grade: str | None) -> str | None:
    if term_grade not in GRADE_POINTS or np_grade not in GRADE_POINTS:
        return None
    delta = GRADE_POINTS[term_grade] - GRADE_POINTS[np_grade]
    if delta > 0:
        return "betyg_hogre_an_np"
    if delta < 0:
        return "betyg_lagre_an_np"
    return "betyg_lika_np"


def skolenhet_lookup(codes: set[str]) -> dict[str, str | None]:
    lookup = {code: None for code in sorted(c for c in codes if c)}
    for code in list(lookup):
        # Skolenhetsregistrets API v2 är primär källa. Om endpointen ändras eller
        # nätet saknas behåller vi koden och låter diagnostiken visa bortfallet.
        urls = [
            f"https://api.skolverket.se/skolenhetsregistret/v2/skolenheter/{urllib.parse.quote(code)}",
            f"https://api.skolverket.se/skolenhetsregistret/v2/sok/skolenheter?skolenhetskod={urllib.parse.quote(code)}",
        ]
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=6) as response:
                    data = json.loads(response.read().decode("utf-8"))
                candidates = data if isinstance(data, list) else data.get("skolenheter") or data.get("hits") or data.get("result") or [data]
                if candidates:
                    item = candidates[0]
                    name = item.get("skolenhetsnamn") or item.get("namn") or item.get("skolEnhetsnamn")
                    if name:
                        lookup[code] = str(name)
                        break
            except Exception:
                continue
    return lookup


def school_name(level: str, code: str | None, lookup: dict[str, str | None]) -> str:
    if level == "kommun":
        return "Alla skolenheter"
    return lookup.get(code or "") or code or "Okänd skolenhet"


def base_groups(rows: list[dict[str, Any]]) -> list[tuple[str, str | None, list[dict[str, Any]]]]:
    groups = [("alla_skolenheter", None, rows)]
    by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_school[clean(row.get("Skolenhetskod"))].append(row)
    for code, subset in sorted(by_school.items()):
        groups.append(("skolenhet", code, subset))
    return groups


def overview(rows: list[dict[str, Any]], lasar: str, arskurs: int) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        merit16 = [row["meritvarde_16"] for row in subset]
        merit17 = [row["meritvarde_17"] for row in subset]
        row = {
            "lasar": lasar,
            "arskurs": arskurs,
            "niva": level,
            "skolenhetskod": school_code,
            "antal_elever": len(subset),
            "genomsnittligt_meritvarde_16": average(merit16),
            "genomsnittligt_meritvarde_17": average(merit17),
            "median_meritvarde_17": round(median(merit17), 2) if merit17 else None,
            "andel_uppnatt_alla_amnen": percentage(sum(1 for r in subset if r["uppnatt_alla_amnen"]), len(subset)),
            "source": "local_scb",
        }
        if arskurs == 9:
            row["andel_behoriga_yrkesprogram"] = percentage(sum(1 for r in subset if r["behorig_yrkesprogram"]), len(subset))
            row["andel_behoriga_hogskoleforberedande_nagot_program"] = percentage(sum(1 for r in subset if r["behorig_hogskoleforberedande_nagot_program"]), len(subset))
        result.append(row)
    return result


def grade_distribution(rows: list[dict[str, Any]], lasar: str, arskurs: int, subjects: list[str]) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        for group_name in ("Alla", "SV", "SVA", "oklar", "SV_och_SVA"):
            group_rows = subset if group_name == "Alla" else [r for r in subset if r["sv_sva_grupp"] == group_name]
            if not group_rows:
                continue
            for subject in subjects:
                grades = [g for r in group_rows if (g := grade(r.get(subject))) is not None]
                counts = Counter(grades)
                total = len(grades)
                out = {
                    "lasar": lasar,
                    "arskurs": arskurs,
                    "niva": level,
                    "skolenhetskod": school_code,
                    "elevgrupp": group_name,
                    "amne": subject,
                    "antal_betyg": total,
                    "antal_A_E": sum(counts[g] for g in PASSING_GRADES),
                    "antal_F": counts["F"],
                    "andel_A_E": percentage(sum(counts[g] for g in PASSING_GRADES), total),
                    "andel_F": percentage(counts["F"], total),
                    "source": "local_scb",
                }
                for g in ("A", "B", "C", "D", "E", "F"):
                    out[f"antal_{g}"] = counts[g]
                    out[f"andel_{g}"] = percentage(counts[g], total)
                result.append(out)
    return result


def sv_sva_summary(rows: list[dict[str, Any]], lasar: str, arskurs: int) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        for group_name in ("SV", "SVA", "oklar", "SV_och_SVA"):
            group_rows = [r for r in subset if r["sv_sva_grupp"] == group_name]
            if not group_rows:
                continue
            subject = "Sva" if group_name == "SVA" else "Sv"
            valid_subject_grades = [grade(r.get(subject)) for r in group_rows if grade(r.get(subject)) is not None]
            row = {
                "lasar": lasar,
                "arskurs": arskurs,
                "niva": level,
                "skolenhetskod": school_code,
                "elevgrupp": group_name,
                "antal_elever": len(group_rows),
                "andel_av_elever": percentage(len(group_rows), len(subset)),
                "genomsnittligt_meritvarde_16": average([r["meritvarde_16"] for r in group_rows]),
                "genomsnittligt_meritvarde_17": average([r["meritvarde_17"] for r in group_rows]),
                "median_meritvarde_17": round(median([r["meritvarde_17"] for r in group_rows]), 2),
                "andel_godkand_sv_sva": percentage(sum(1 for g in valid_subject_grades if g in PASSING_GRADES), len(valid_subject_grades)),
                "andel_uppnatt_alla_amnen": percentage(sum(1 for r in group_rows if r["uppnatt_alla_amnen"]), len(group_rows)),
                "source": "local_scb",
            }
            if arskurs == 9:
                row["andel_behoriga_yrkesprogram"] = percentage(sum(1 for r in group_rows if r["behorig_yrkesprogram"]), len(group_rows))
            result.append(row)
    return result


def np_passed(value: Any) -> bool | None:
    value = clean(value).upper()
    if value in PASSING_GRADES or value == "1":
        return True
    if value == "F" or value == "0":
        return False
    return None


def np_subject_results(row: dict[str, str], arskurs: int) -> list[dict[str, Any]]:
    if arskurs == 3:
        results = []
        for subject, cols in {
            "Ma": ["MA_A_PR", "MA_B_PR", "MA_C_PR", "MA_D_PR", "MA_E_PR", "MA_F_PR", "MA_G_PR", "MA_G1_PR", "MA_G2_PR"],
            "Sv/Sva": ["SV_A_PR", "SV_B_PR", "SV_C_PR", "SV_D_PR", "SV_E_PR", "SV_F_PR", "SV_G_PR", "SV_H_PR"],
        }.items():
            values = [np_passed(row.get(col)) for col in cols]
            valid = [value for value in values if value is not None]
            if valid:
                results.append({"amne": subject, "np_betyg": None, "godkand_np": all(valid), "antal_delprov": len(valid)})
        return results

    if arskurs == 6:
        return [
            {"amne": "Ma", "np_betyg": grade(row.get("MA_PROVB")), "godkand_np": np_passed(row.get("MA_PROVB"))},
            {"amne": "Sv/Sva", "np_betyg": grade(row.get("SV_PROVB")), "godkand_np": np_passed(row.get("SV_PROVB"))},
            {"amne": "En", "np_betyg": grade(row.get("EN_PROVB")), "godkand_np": np_passed(row.get("EN_PROVB"))},
        ]

    if arskurs == 9:
        no_map = {"BI": "Bi", "FY": "Fy", "KE": "Ke"}
        so_map = {"GE": "Ge", "HI": "Hi", "RE": "Re", "SH": "Sh"}
        no_subject = no_map.get(clean(row.get("NO_PROV")).upper(), "NO")
        so_subject = so_map.get(clean(row.get("SO_PROV")).upper(), "SO")
        return [
            {"amne": "Ma", "np_betyg": grade(row.get("MA_PROVB")), "godkand_np": np_passed(row.get("MA_PROVB"))},
            {"amne": "Sv/Sva", "np_betyg": grade(row.get("SV_PROVB")), "godkand_np": np_passed(row.get("SV_PROVB"))},
            {"amne": "En", "np_betyg": grade(row.get("EN_PROVB")), "godkand_np": np_passed(row.get("EN_PROVB"))},
            {"amne": no_subject, "np_betyg": grade(row.get("NO_PROVB")), "godkand_np": np_passed(row.get("NO_PROVB"))},
            {"amne": so_subject, "np_betyg": grade(row.get("SO_PROVB")), "godkand_np": np_passed(row.get("SO_PROVB"))},
        ]

    return []


def term_grade_for_np_subject(grade_row: dict[str, str] | None, np_row: dict[str, str], subject: str) -> str | None:
    if not grade_row:
        return None
    if subject == "Sv/Sva":
        if clean(np_row.get("SV_KURSPLAN")) == "2":
            return grade(grade_row.get("Sva"))
        return grade(grade_row.get("Sv")) or grade(grade_row.get("Sva"))
    return grade(grade_row.get(subject))


def aggregate_np(
    np_rows_by_grade: list[tuple[dict[str, str], dict[str, str] | None]],
    lasar: str,
    arskurs: int,
    lookup: dict[str, str | None],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []

    expanded: list[dict[str, Any]] = []
    for np_row, grade_row in np_rows_by_grade:
        code = clean(np_row.get("Skolenhetskod"))
        for item in np_subject_results(np_row, arskurs):
            if item.get("godkand_np") is None:
                continue
            term_grade = term_grade_for_np_subject(grade_row, np_row, item["amne"])
            relation = grade_relation(term_grade, item.get("np_betyg"))
            expanded.append({
                "skolenhetskod": code,
                "amne": item["amne"],
                "godkand_np": item["godkand_np"],
                "np_betyg": item.get("np_betyg"),
                "terminsbetyg": term_grade,
                "relation": relation,
                "matched_grade": grade_row is not None,
            })

    group_defs: list[tuple[str, str | None, list[dict[str, Any]]]] = [("kommun", None, expanded)]
    by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in expanded:
        by_school[item["skolenhetskod"]].append(item)
    group_defs.extend(("skolenhet", code, rows) for code, rows in sorted(by_school.items()))

    for level, code, subset in group_defs:
        by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in subset:
            by_subject[item["amne"]].append(item)
        for subject, subject_rows in sorted(by_subject.items()):
            total = len(subject_rows)
            passed = sum(1 for item in subject_rows if item["godkand_np"])
            base = {
                "lasar": lasar,
                "arskurs": arskurs,
                "niva": level,
                "skolenhetskod": code,
                "skolenhetsnamn": school_name(level, code, lookup),
                "amne": subject,
                "antal_np": total,
                "antal_godkanda_np": passed,
                "andel_godkanda_np": percentage(passed, total),
                "antal_med_betygsmatch": sum(1 for item in subject_rows if item["matched_grade"]),
                "source": "local_scb_np",
            }
            result_rows.append(base)

            comparable = [item for item in subject_rows if item["relation"]]
            if comparable:
                counts = Counter(item["relation"] for item in comparable)
                relation_rows.append({
                    **base,
                    "antal_jamforda": len(comparable),
                    "antal_betyg_hogre_an_np": counts["betyg_hogre_an_np"],
                    "antal_betyg_lika_np": counts["betyg_lika_np"],
                    "antal_betyg_lagre_an_np": counts["betyg_lagre_an_np"],
                    "andel_betyg_hogre_an_np": percentage(counts["betyg_hogre_an_np"], len(comparable)),
                    "andel_betyg_lika_np": percentage(counts["betyg_lika_np"], len(comparable)),
                    "andel_betyg_lagre_an_np": percentage(counts["betyg_lagre_an_np"], len(comparable)),
                })

    return result_rows, relation_rows


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
        "special_codes_by_subject": {k: dict(v) for k, v in special_counts.items() if sum(v.values())},
    }


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


def build_year(lasar: str) -> None:
    output_dir = OUTPUT_BASE / lasar
    json_dir = output_dir / "json"
    diagnostics_dir = output_dir / "diagnostik"
    all_overview: list[dict[str, Any]] = []
    all_distribution: list[dict[str, Any]] = []
    all_sv_sva: list[dict[str, Any]] = []
    all_np_pass: list[dict[str, Any]] = []
    all_np_relation: list[dict[str, Any]] = []
    manifest = {"lasar": lasar, "source": "local_scb", "arskurser": [], "np_arskurser": [], "files": []}
    grade_rows_by_key: dict[tuple[int, str, str], dict[str, str]] = {}
    school_codes: set[str] = set()

    for spec in SPECS.values():
        rows, diagnostics = read_grade_files(lasar, spec)
        for row in rows:
            m16, m17 = merit(row, spec.subjects)
            row["arskurs"] = spec.arskurs
            row["lasar"] = lasar
            row["sv_sva_grupp"] = sv_sva_group(row)
            row["meritvarde_16"] = m16
            row["meritvarde_17"] = m17
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
        diag = import_diagnostics(rows, diagnostics, spec, lasar)
        write_json(diagnostics_dir / f"import_betyg_ak{spec.arskurs}.json", diag)

        if rows:
            all_overview.extend(overview(rows, lasar, spec.arskurs))
            all_distribution.extend(grade_distribution(rows, lasar, spec.arskurs, spec.subjects))
            all_sv_sva.extend(sv_sva_summary(rows, lasar, spec.arskurs))
            manifest["arskurser"].append({"arskurs": spec.arskurs, "rows": len(rows)})
        manifest["files"].extend(d for d in diagnostics if d.get("message") == "file_read")

    np_rows_by_spec: dict[int, list[tuple[dict[str, str], dict[str, str] | None]]] = {}
    for spec in NP_SPECS.values():
        rows, diagnostics = read_np_files(lasar, spec)
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
        manifest["files"].extend({**d, "kind": f"np_ak{spec.arskurs}"} for d in diagnostics if d.get("message") == "file_read")

    lookup = skolenhet_lookup(school_codes)
    write_json(json_dir / "skolenheter_lookup.json", lookup)
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SCB grade txt files and create anonymized JSON statistics.")
    parser.add_argument("--lasar", required=True, help="School year folder, for example 2025-2026")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_year(args.lasar)
