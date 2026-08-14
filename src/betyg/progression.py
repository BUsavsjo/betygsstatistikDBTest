from __future__ import annotations

import re
from typing import Any

from .constants import AK9_SUBJECTS
from .metrics import clean, gender_from_personnr, grade, merit, subject_name, sv_sva_group


SOURCE_AND_KEY_FIELDS = {"PersonNr", "_source_file", "_source_row"}
FORBIDDEN_PUBLIC_KEYS = {"PersonNr", "Fornamn", "Efternamn", "Klass", "_source_file", "_source_row"}
GRADE_RANK = {"F": 0, "E": 1, "D": 2, "C": 3, "B": 4, "A": 5}
COMPARABLE_SUBJECTS = (
    "Bl",
    "En",
    "Hkk",
    "Idh",
    "Ma",
    "Mu",
    "Bi",
    "Fy",
    "Ke",
    "Ge",
    "Hi",
    "Re",
    "Sh",
    "Sl",
    "Sv/Sva",
    "Tn",
    "Tk",
)
PROGRESSION_SCHOOLS = {
    "59983229": "Hofgårdsskolan",
    "74170440": "Rörviks skola",
}


def source_school_year(ak9_lasar: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{4})", ak9_lasar)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise ValueError(f"Ogiltigt läsår: {ak9_lasar}")
    return f"{int(match.group(1)) - 3:04d}-{int(match.group(2)) - 3:04d}"


def normalize_personnr(value: object) -> str | None:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) == 12:
        digits = digits[-10:]
    return digits if len(digits) == 10 else None


def _row_signature(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (key, str(value))
            for key, value in row.items()
            if key not in SOURCE_AND_KEY_FIELDS
        )
    )


def deduplicate_rows(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    invalid_keys = 0
    for row in rows:
        key = normalize_personnr(row.get("PersonNr"))
        if key is None:
            invalid_keys += 1
            continue
        grouped.setdefault(key, []).append(row)

    unique: dict[str, dict[str, Any]] = {}
    identical_duplicates = 0
    conflicting_duplicates = 0
    for key, candidates in grouped.items():
        signatures = {_row_signature(row) for row in candidates}
        if len(signatures) == 1:
            unique[key] = candidates[0]
            identical_duplicates += len(candidates) - 1
        else:
            conflicting_duplicates += 1

    return unique, {
        "ogiltiga_nycklar": invalid_keys,
        "identiska_dubbletter": identical_duplicates,
        "motstridiga_dubbletter": conflicting_duplicates,
    }


def match_cohort(
    ak6_rows: list[dict[str, Any]],
    ak9_rows: list[dict[str, Any]],
) -> tuple[
    list[tuple[dict[str, Any], dict[str, Any]]],
    dict[str, Any],
]:
    ak6_unique, ak6_diagnostics = deduplicate_rows(ak6_rows)
    ak9_unique, ak9_diagnostics = deduplicate_rows(ak9_rows)
    pairs = [
        (ak6_unique[key], ak9_row)
        for key, ak9_row in ak9_unique.items()
        if key in ak6_unique
    ]
    return pairs, {
        "ak6_giltiga": len(ak6_unique),
        "ak9_giltiga": len(ak9_unique),
        "matchade": len(pairs),
        "ak6_omatchade": len(ak6_unique) - len(pairs),
        "ak9_omatchade": len(ak9_unique) - len(pairs),
        "ak6_dubbletter": ak6_diagnostics,
        "ak9_dubbletter": ak9_diagnostics,
    }


def _sv_sva_grade(row: dict[str, Any]) -> str | None:
    values = [
        current_grade
        for key in ("Sv", "Sva")
        if (current_grade := grade(row.get(key))) is not None
    ]
    return values[0] if len(values) == 1 else None


def compare_subject(
    ak6_row: dict[str, Any],
    ak9_row: dict[str, Any],
    subject: str,
) -> tuple[int, int] | None:
    if subject == "Sv/Sva":
        ak6_grade = _sv_sva_grade(ak6_row)
        ak9_grade = _sv_sva_grade(ak9_row)
    else:
        ak6_grade = grade(ak6_row.get(subject))
        ak9_grade = grade(ak9_row.get(subject))
    if ak6_grade is None or ak9_grade is None:
        return None
    return GRADE_RANK[ak6_grade], GRADE_RANK[ak9_grade]


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        rank = (start + end + 2) / 2
        for position in range(start, end + 1):
            ranks[order[position]] = rank
        start = end + 1
    return ranks


def spearman(values_x: list[float], values_y: list[float]) -> float | None:
    if len(values_x) != len(values_y) or len(values_x) < 2:
        return None
    x_ranks = _average_ranks(values_x)
    y_ranks = _average_ranks(values_y)
    mean_x = sum(x_ranks) / len(x_ranks)
    mean_y = sum(y_ranks) / len(y_ranks)
    numerator = sum(
        (x_value - mean_x) * (y_value - mean_y)
        for x_value, y_value in zip(x_ranks, y_ranks)
    )
    denominator = (
        sum((value - mean_x) ** 2 for value in x_ranks)
        * sum((value - mean_y) ** 2 for value in y_ranks)
    ) ** 0.5
    return round(numerator / denominator, 3) if denominator else None


def _average(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return round(sum(valid) / len(valid), 2) if valid else None


def _percentage(part: int, total: int) -> float | None:
    return round(part / total * 100, 2) if total else None


def _subject_display_name(subject: str) -> str:
    if subject == "Sv/Sva":
        return "Svenska/Svenska som andraspråk"
    return subject_name(subject)


def _subject_rows(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    threshold: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for subject in COMPARABLE_SUBJECTS:
        comparisons = [
            comparison
            for ak6_row, ak9_row in pairs
            if (comparison := compare_subject(ak6_row, ak9_row, subject)) is not None
        ]
        base = {
            "amne": subject,
            "amnesnamn": _subject_display_name(subject),
        }
        if len(comparisons) < threshold:
            result.append(
                {
                    **base,
                    "undertryckt": True,
                    "antal_elever": None,
                    "genomsnitt_ak6": None,
                    "genomsnitt_ak9": None,
                    "genomsnittlig_forandring": None,
                    "andel_hojda": None,
                    "andel_oforandrade": None,
                    "andel_sankta": None,
                    "andel_f_till_godkant": None,
                    "andel_godkant_till_f": None,
                    "korrelation": None,
                }
            )
            continue

        ak6_values = [comparison[0] for comparison in comparisons]
        ak9_values = [comparison[1] for comparison in comparisons]
        differences = [ak9 - ak6 for ak6, ak9 in comparisons]
        result.append(
            {
                **base,
                "undertryckt": False,
                "antal_elever": len(comparisons),
                "genomsnitt_ak6": _average(ak6_values),
                "genomsnitt_ak9": _average(ak9_values),
                "genomsnittlig_forandring": _average(differences),
                "andel_hojda": _percentage(sum(value > 0 for value in differences), len(differences)),
                "andel_oforandrade": _percentage(sum(value == 0 for value in differences), len(differences)),
                "andel_sankta": _percentage(sum(value < 0 for value in differences), len(differences)),
                "andel_f_till_godkant": _percentage(
                    sum(ak6 == 0 and ak9 > 0 for ak6, ak9 in comparisons),
                    len(comparisons),
                ),
                "andel_godkant_till_f": _percentage(
                    sum(ak6 > 0 and ak9 == 0 for ak6, ak9 in comparisons),
                    len(comparisons),
                ),
                "korrelation": spearman(ak6_values, ak9_values),
            }
        )
    return result


def _student_indices(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[tuple[float, float, float | None]]:
    indices: list[tuple[float, float, float | None]] = []
    for ak6_row, ak9_row in pairs:
        comparisons = [
            comparison
            for subject in COMPARABLE_SUBJECTS
            if (comparison := compare_subject(ak6_row, ak9_row, subject)) is not None
        ]
        if len(comparisons) < 5:
            continue
        ak6_index = sum(value[0] for value in comparisons) / len(comparisons)
        ak9_index = sum(value[1] for value in comparisons) / len(comparisons)
        merit_16, _ = merit(ak9_row, AK9_SUBJECTS, require_passing=True)
        indices.append((ak6_index, ak9_index, merit_16))
    return indices


def _suppressed_segment(
    level: str,
    school_code: str | None,
    school_label: str,
    gender: str,
    group: str,
) -> dict[str, Any]:
    return {
        "niva": level,
        "skolenhetskod": school_code,
        "skolenhetsnamn": school_label,
        "kon": gender,
        "elevgrupp": group,
        "undertryckt": True,
        "matchning": None,
        "oversikt": None,
        "merit_ak9": None,
        "amnen": None,
    }


def _aggregate_segment(
    level: str,
    school_code: str | None,
    school_label: str,
    gender: str,
    group: str,
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    eligible_ak9: list[dict[str, Any]],
    threshold: int,
) -> dict[str, Any]:
    if len(pairs) < threshold:
        return _suppressed_segment(level, school_code, school_label, gender, group)

    comparisons = [
        comparison
        for ak6_row, ak9_row in pairs
        for subject in COMPARABLE_SUBJECTS
        if (comparison := compare_subject(ak6_row, ak9_row, subject)) is not None
    ]
    ak6_values = [comparison[0] for comparison in comparisons]
    ak9_values = [comparison[1] for comparison in comparisons]
    differences = [ak9 - ak6 for ak6, ak9 in comparisons]
    indices = _student_indices(pairs)
    merits = [merit(ak9_row, AK9_SUBJECTS, require_passing=True) for _, ak9_row in pairs]
    merit_16_values = [value[0] for value in merits]
    merit_17_values = [value[1] for value in merits]
    index_merit_pairs = [
        (ak6_index, merit_16)
        for ak6_index, _, merit_16 in indices
        if merit_16 is not None
    ]

    return {
        "niva": level,
        "skolenhetskod": school_code,
        "skolenhetsnamn": school_label,
        "kon": gender,
        "elevgrupp": group,
        "undertryckt": False,
        "matchning": {
            "antal_ak9": len(eligible_ak9),
            "antal_matchade": len(pairs),
            "matchningsgrad": _percentage(len(pairs), len(eligible_ak9)),
        },
        "oversikt": {
            "antal_betygspar": len(comparisons),
            "genomsnitt_ak6": _average(ak6_values),
            "genomsnitt_ak9": _average(ak9_values),
            "genomsnittlig_forandring": _average(differences),
            "andel_hojda_betyg": _percentage(sum(value > 0 for value in differences), len(differences)),
            "andel_oforandrade_betyg": _percentage(sum(value == 0 for value in differences), len(differences)),
            "andel_sankta_betyg": _percentage(sum(value < 0 for value in differences), len(differences)),
            "andel_f_till_godkant": _percentage(
                sum(ak6 == 0 and ak9 > 0 for ak6, ak9 in comparisons),
                len(comparisons),
            ),
            "andel_godkant_till_f": _percentage(
                sum(ak6 > 0 and ak9 == 0 for ak6, ak9 in comparisons),
                len(comparisons),
            ),
            "korrelation": spearman(
                [value[0] for value in indices],
                [value[1] for value in indices],
            ),
        },
        "merit_ak9": {
            "genomsnitt_merit_16": _average(merit_16_values),
            "genomsnitt_merit_17": _average(merit_17_values),
            "korrelation_ak6_index_merit_16": spearman(
                [value[0] for value in index_merit_pairs],
                [value[1] for value in index_merit_pairs],
            ),
        },
        "amnen": _subject_rows(pairs, threshold),
    }


def _suppress(segment: dict[str, Any]) -> None:
    segment.update(
        {
            "undertryckt": True,
            "matchning": None,
            "oversikt": None,
            "merit_ak9": None,
            "amnen": None,
        }
    )


def _apply_secondary_suppression(segments: list[dict[str, Any]]) -> None:
    school_keys = {(row["niva"], row["skolenhetskod"]) for row in segments}
    for level, school_code in school_keys:
        for group in ("Alla", "SV", "SVA"):
            gender_rows = [
                row
                for row in segments
                if row["niva"] == level
                and row["skolenhetskod"] == school_code
                and row["elevgrupp"] == group
                and row["kon"] in {"Flickor", "Pojkar"}
            ]
            if len(gender_rows) == 2 and any(row["undertryckt"] for row in gender_rows):
                for row in gender_rows:
                    _suppress(row)
        for gender in ("Alla", "Flickor", "Pojkar"):
            course_rows = [
                row
                for row in segments
                if row["niva"] == level
                and row["skolenhetskod"] == school_code
                and row["kon"] == gender
                and row["elevgrupp"] in {"SV", "SVA"}
            ]
            if len(course_rows) == 2 and any(row["undertryckt"] for row in course_rows):
                for row in course_rows:
                    _suppress(row)


def _assert_public_document(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_PUBLIC_KEYS.intersection(value)
        if forbidden:
            raise ValueError(f"Otillåtna publika nycklar: {sorted(forbidden)}")
        for child in value.values():
            _assert_public_document(child)
    elif isinstance(value, list):
        for child in value:
            _assert_public_document(child)


def build_progression_document(
    matched_rows: list[tuple[dict[str, Any], dict[str, Any]]],
    ak9_rows: list[dict[str, Any]],
    ak6_lasar: str,
    ak9_lasar: str,
    privacy_threshold: int = 10,
) -> dict[str, Any]:
    ak9_unique, _ = deduplicate_rows(ak9_rows)
    eligible_rows = [
        row
        for row in ak9_unique.values()
        if clean(row.get("Skolenhetskod")) in PROGRESSION_SCHOOLS
    ]
    eligible_pairs = [
        pair
        for pair in matched_rows
        if clean(pair[1].get("Skolenhetskod")) in PROGRESSION_SCHOOLS
    ]
    schools = [
        ("huvudman", None, "Sävsjö kommun"),
        *(
            ("skolenhet", school_code, school_label)
            for school_code, school_label in PROGRESSION_SCHOOLS.items()
        ),
    ]
    segments: list[dict[str, Any]] = []
    for level, school_code, school_label in schools:
        school_pairs = [
            pair
            for pair in eligible_pairs
            if school_code is None or clean(pair[1].get("Skolenhetskod")) == school_code
        ]
        school_ak9 = [
            row
            for row in eligible_rows
            if school_code is None or clean(row.get("Skolenhetskod")) == school_code
        ]
        for gender in ("Alla", "Flickor", "Pojkar"):
            for group in ("Alla", "SV", "SVA"):
                pairs = [
                    pair
                    for pair in school_pairs
                    if (gender == "Alla" or gender_from_personnr(pair[1].get("PersonNr")) == gender)
                    and (group == "Alla" or sv_sva_group(pair[1]) == group)
                ]
                group_ak9 = [
                    row
                    for row in school_ak9
                    if (gender == "Alla" or gender_from_personnr(row.get("PersonNr")) == gender)
                    and (group == "Alla" or sv_sva_group(row) == group)
                ]
                segments.append(
                    _aggregate_segment(
                        level,
                        school_code,
                        school_label,
                        gender,
                        group,
                        pairs,
                        group_ak9,
                        privacy_threshold,
                    )
                )

    _apply_secondary_suppression(segments)
    document = {
        "schema_version": 1,
        "status": "ok",
        "source": "local_scb_progression",
        "ak6_lasar": ak6_lasar,
        "ak9_lasar": ak9_lasar,
        "sekretessgrans": privacy_threshold,
        "segment": segments,
    }
    _assert_public_document(document)
    return document
