from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any

from .constants import GRADE_POINTS, PASSING_GRADES, VALID_GRADES


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def grade(value: Any) -> str | None:
    value = clean(value).upper()
    return value if value in VALID_GRADES else None


def is_passing(value: Any) -> bool:
    return grade(value) in PASSING_GRADES


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
        current_grade = grade(row.get(subject))
        if current_grade is None:
            continue
        if subject in {"Sv", "Sva"}:
            sv_sva_points.append(GRADE_POINTS[current_grade])
        else:
            points.append(GRADE_POINTS[current_grade])
    if sv_sva_points:
        points.append(max(sv_sva_points))
    merit_16 = sum(sorted(points, reverse=True)[:16])

    language_points = [
        GRADE_POINTS[current_grade]
        for col in ("M1_betyg", "M2_betyg")
        if (current_grade := grade(row.get(col))) in PASSING_GRADES
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
    ek_hu_sa = es and all(is_passing(row.get(subject)) for subject in ("Ge", "Hi", "Re", "Sh"))
    na_te = es and all(is_passing(row.get(subject)) for subject in ("Bi", "Fy", "Ke"))
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


def school_name(level: str, code: str | None, lookup: dict[str, str | None]) -> str:
    if level in {"kommun", "alla_skolenheter"}:
        return "Alla skolenheter"
    return lookup.get(code or "") or code or "Okand skolenhet"


def base_groups(rows: list[dict[str, Any]]) -> list[tuple[str, str | None, list[dict[str, Any]]]]:
    groups = [("alla_skolenheter", None, rows)]
    by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_school[clean(row.get("Skolenhetskod"))].append(row)
    for code, subset in sorted(by_school.items()):
        groups.append(("skolenhet", code, subset))
    return groups


def overview(rows: list[dict[str, Any]], lasar: str, arskurs: int, lookup: dict[str, str | None]) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        merit16 = [row["meritvarde_16"] for row in subset]
        merit17 = [row["meritvarde_17"] for row in subset]
        item = {
            "lasar": lasar,
            "arskurs": arskurs,
            "niva": level,
            "skolenhetskod": school_code,
            "skolenhetsnamn": school_name(level, school_code, lookup),
            "antal_elever": len(subset),
            "genomsnittligt_meritvarde_16": average(merit16),
            "genomsnittligt_meritvarde_17": average(merit17),
            "median_meritvarde_17": round(median(merit17), 2) if merit17 else None,
            "andel_uppnatt_alla_amnen": percentage(sum(1 for row in subset if row["uppnatt_alla_amnen"]), len(subset)),
            "source": "local_scb",
        }
        if arskurs == 9:
            item["andel_behoriga_yrkesprogram"] = percentage(sum(1 for row in subset if row["behorig_yrkesprogram"]), len(subset))
            item["andel_behoriga_hogskoleforberedande_nagot_program"] = percentage(sum(1 for row in subset if row["behorig_hogskoleforberedande_nagot_program"]), len(subset))
        result.append(item)
    return result


def grade_distribution(rows: list[dict[str, Any]], lasar: str, arskurs: int, subjects: list[str], lookup: dict[str, str | None]) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        for group_name in ("Alla", "SV", "SVA", "oklar", "SV_och_SVA"):
            group_rows = subset if group_name == "Alla" else [row for row in subset if row["sv_sva_grupp"] == group_name]
            if not group_rows:
                continue
            for subject in subjects:
                grades = [current_grade for row in group_rows if (current_grade := grade(row.get(subject))) is not None]
                counts = Counter(grades)
                total = len(grades)
                item = {
                    "lasar": lasar,
                    "arskurs": arskurs,
                    "niva": level,
                    "skolenhetskod": school_code,
                    "skolenhetsnamn": school_name(level, school_code, lookup),
                    "elevgrupp": group_name,
                    "amne": subject,
                    "antal_betyg": total,
                    "antal_A_E": sum(counts[grade_name] for grade_name in PASSING_GRADES),
                    "antal_F": counts["F"],
                    "andel_A_E": percentage(sum(counts[grade_name] for grade_name in PASSING_GRADES), total),
                    "andel_F": percentage(counts["F"], total),
                    "source": "local_scb",
                }
                for grade_name in ("A", "B", "C", "D", "E", "F"):
                    item[f"antal_{grade_name}"] = counts[grade_name]
                    item[f"andel_{grade_name}"] = percentage(counts[grade_name], total)
                result.append(item)
    return result


def sv_sva_summary(rows: list[dict[str, Any]], lasar: str, arskurs: int, lookup: dict[str, str | None]) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        for group_name in ("SV", "SVA", "oklar", "SV_och_SVA"):
            group_rows = [row for row in subset if row["sv_sva_grupp"] == group_name]
            if not group_rows:
                continue
            subject = "Sva" if group_name == "SVA" else "Sv"
            valid_subject_grades = [grade(row.get(subject)) for row in group_rows if grade(row.get(subject)) is not None]
            item = {
                "lasar": lasar,
                "arskurs": arskurs,
                "niva": level,
                "skolenhetskod": school_code,
                "skolenhetsnamn": school_name(level, school_code, lookup),
                "elevgrupp": group_name,
                "antal_elever": len(group_rows),
                "andel_av_elever": percentage(len(group_rows), len(subset)),
                "genomsnittligt_meritvarde_16": average([row["meritvarde_16"] for row in group_rows]),
                "genomsnittligt_meritvarde_17": average([row["meritvarde_17"] for row in group_rows]),
                "median_meritvarde_17": round(median([row["meritvarde_17"] for row in group_rows]), 2),
                "andel_godkand_sv_sva": percentage(sum(1 for current_grade in valid_subject_grades if current_grade in PASSING_GRADES), len(valid_subject_grades)),
                "andel_uppnatt_alla_amnen": percentage(sum(1 for row in group_rows if row["uppnatt_alla_amnen"]), len(group_rows)),
                "source": "local_scb",
            }
            if arskurs == 9:
                item["andel_behoriga_yrkesprogram"] = percentage(sum(1 for row in group_rows if row["behorig_yrkesprogram"]), len(group_rows))
            result.append(item)
    return result
