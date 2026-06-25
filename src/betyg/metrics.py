from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any

from .constants import GRADE_POINTS, PASSING_GRADES, VALID_GRADES


SUBJECT_DISPLAY_NAMES = {
    "Bl": "Bild",
    "En": "Engelska",
    "Hkk": "Hem- och konsumentkunskap",
    "Idh": "Idrott och hälsa",
    "Ma": "Matematik",
    "M1_betyg": "Moderna språk, elevens val",
    "M2_betyg": "Moderna språk, skolans val",
    "ML_betyg": "Moderna språk som språkval",
    "Modmalbe": "Modersmål",
    "Mu": "Musik",
    "No": "Naturorienterande ämnen (blockbetyg)",
    "Bi": "Biologi",
    "Fy": "Fysik",
    "Ke": "Kemi",
    "So": "Samhällsorienterande ämnen (blockbetyg)",
    "Ge": "Geografi",
    "Hi": "Historia",
    "Re": "Religionskunskap",
    "Sh": "Samhällskunskap",
    "Sl": "Slöjd",
    "Sv": "Svenska",
    "Sva": "Svenska som andraspråk",
    "Tn": "Teckenspråk",
    "Tk": "Teknik",
    "Ovr": "Övrigt ämne",
}

EXTRA_LANGUAGE_SUBJECTS = {"M1_betyg", "M2_betyg", "ML_betyg"}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def subject_name(subject: str) -> str:
    return SUBJECT_DISPLAY_NAMES.get(subject, subject)


def grade(value: Any) -> str | None:
    value = clean(value).upper()
    return value if value in VALID_GRADES else None


def is_passing(value: Any) -> bool:
    return grade(value) in PASSING_GRADES


def gender_from_personnr(value: Any) -> str:
    digits = "".join(ch for ch in clean(value) if ch.isdigit())
    if len(digits) < 2:
        return "okänt"
    gender_digit = int(digits[-2])
    return "Pojkar" if gender_digit % 2 else "Flickor"


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


def merit(row: dict[str, str], subjects: list[str], *, require_passing: bool = False) -> tuple[float | None, float | None]:
    points: list[float] = []
    sv_sva_points: list[float] = []
    has_passing_grade = False
    for subject in subjects:
        if subject in EXTRA_LANGUAGE_SUBJECTS:
            continue
        current_grade = grade(row.get(subject))
        if current_grade is None:
            continue
        if current_grade in PASSING_GRADES:
            has_passing_grade = True
        if subject in {"Sv", "Sva"}:
            sv_sva_points.append(GRADE_POINTS[current_grade])
        else:
            points.append(GRADE_POINTS[current_grade])
    if sv_sva_points:
        points.append(max(sv_sva_points))
    if require_passing and not has_passing_grade:
        return None, None
    merit_16 = sum(sorted(points, reverse=True)[:16])

    language_points = [
        GRADE_POINTS[current_grade]
        for col in ("M1_betyg", "M2_betyg", "ML_betyg")
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


def average(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return round(sum(valid) / len(valid), 2) if valid else None


def median_value(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return round(median(valid), 2) if valid else None


def percentage(part: int, total: int) -> float | None:
    return round(part / total * 100, 2) if total else None


def kolada_grade6_all_subjects_percentage(passed: int, total: int) -> float | None:
    """Match Kolada/Siris display rule for grade 6 all-subjects attainment.

    If 40 or more students are in the group and only 1-4 students did not
    reach the criteria in all subjects they study, the displayed value should
    be 95 instead of the exact percentage.
    """
    if not total:
        return None
    failed = total - passed
    if total >= 40 and 1 <= failed <= 4:
        return 95.0
    return percentage(passed, total)


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


def segmented_groups(rows: list[dict[str, Any]]) -> list[tuple[str, str, list[dict[str, Any]]]]:
    segments: list[tuple[str, str, list[dict[str, Any]]]] = [("Alla", "Alla", rows)]
    genders = ["Pojkar", "Flickor"]
    group_names = ["SV", "SVA", "oklar", "SV_och_SVA"]

    for gender_name in genders:
        gender_rows = [row for row in rows if row.get("kon") == gender_name]
        if gender_rows:
            segments.append((gender_name, "Alla", gender_rows))

    for group_name in group_names:
        group_rows = [row for row in rows if row["sv_sva_grupp"] == group_name]
        if group_rows:
            segments.append(("Alla", group_name, group_rows))
        for gender_name in genders:
            gender_group_rows = [row for row in group_rows if row.get("kon") == gender_name]
            if gender_group_rows:
                segments.append((gender_name, group_name, gender_group_rows))

    return segments


def overview(rows: list[dict[str, Any]], lasar: str, arskurs: int, lookup: dict[str, str | None]) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        for kon, elevgrupp, segment in segmented_groups(subset):
            merit16 = [row["meritvarde_16"] for row in segment]
            merit17 = [row["meritvarde_17"] for row in segment]
            passed_all_subjects = sum(1 for row in segment if row["uppnatt_alla_amnen"])
            item = {
                "lasar": lasar,
                "arskurs": arskurs,
                "niva": level,
                "skolenhetskod": school_code,
                "skolenhetsnamn": school_name(level, school_code, lookup),
                "kon": kon,
                "elevgrupp": elevgrupp,
                "antal_elever": len(segment),
                "genomsnittligt_meritvarde_16": average(merit16),
                "genomsnittligt_meritvarde_17": average(merit17),
                "median_meritvarde_17": median_value(merit17),
                "andel_uppnatt_alla_amnen": kolada_grade6_all_subjects_percentage(passed_all_subjects, len(segment)) if arskurs == 6 else percentage(passed_all_subjects, len(segment)),
                "source": "local_scb",
            }
            if arskurs == 9:
                item["andel_behoriga_yrkesprogram"] = percentage(sum(1 for row in segment if row["behorig_yrkesprogram"]), len(segment))
                item["andel_behoriga_hogskoleforberedande_nagot_program"] = percentage(sum(1 for row in segment if row["behorig_hogskoleforberedande_nagot_program"]), len(segment))
            result.append(item)
    return result


def grade_distribution(rows: list[dict[str, Any]], lasar: str, arskurs: int, subjects: list[str], lookup: dict[str, str | None]) -> list[dict[str, Any]]:
    result = []
    for level, school_code, subset in base_groups(rows):
        for kon, elevgrupp, segment in segmented_groups(subset):
            for subject in subjects:
                grades = [current_grade for row in segment if (current_grade := grade(row.get(subject))) is not None]
                counts = Counter(grades)
                total = len(grades)
                item = {
                    "lasar": lasar,
                    "arskurs": arskurs,
                    "niva": level,
                    "skolenhetskod": school_code,
                    "skolenhetsnamn": school_name(level, school_code, lookup),
                    "kon": kon,
                    "elevgrupp": elevgrupp,
                    "amne": subject,
                    "amnesnamn": subject_name(subject),
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
        for kon, group_name, group_rows in segmented_groups(subset):
            if group_name == "Alla":
                continue
            subject = "Sva" if group_name == "SVA" else "Sv"
            valid_subject_grades = [grade(row.get(subject)) for row in group_rows if grade(row.get(subject)) is not None]
            item = {
                "lasar": lasar,
                "arskurs": arskurs,
                "niva": level,
                "skolenhetskod": school_code,
                "skolenhetsnamn": school_name(level, school_code, lookup),
                "kon": kon,
                "elevgrupp": group_name,
                "antal_elever": len(group_rows),
                "andel_av_elever": percentage(len(group_rows), len(subset)),
                "genomsnittligt_meritvarde_16": average([row["meritvarde_16"] for row in group_rows]),
                "genomsnittligt_meritvarde_17": average([row["meritvarde_17"] for row in group_rows]),
                "median_meritvarde_17": median_value([row["meritvarde_17"] for row in group_rows]),
                "andel_godkand_sv_sva": percentage(sum(1 for current_grade in valid_subject_grades if current_grade in PASSING_GRADES), len(valid_subject_grades)),
                "andel_uppnatt_alla_amnen": kolada_grade6_all_subjects_percentage(sum(1 for row in group_rows if row["uppnatt_alla_amnen"]), len(group_rows)) if arskurs == 6 else percentage(sum(1 for row in group_rows if row["uppnatt_alla_amnen"]), len(group_rows)),
                "source": "local_scb",
            }
            if arskurs == 9:
                item["andel_behoriga_yrkesprogram"] = percentage(sum(1 for row in group_rows if row["behorig_yrkesprogram"]), len(group_rows))
            result.append(item)
    return result
