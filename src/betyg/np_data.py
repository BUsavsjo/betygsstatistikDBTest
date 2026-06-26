from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .constants import GRADE_POINTS, PASSING_GRADES
from .metrics import clean, gender_from_personnr, grade, percentage, school_name, segmented_groups


def grade_relation(term_grade: str | None, np_grade: str | None) -> str | None:
    if term_grade not in GRADE_POINTS or np_grade not in GRADE_POINTS:
        return None
    delta = GRADE_POINTS[term_grade] - GRADE_POINTS[np_grade]
    if delta > 0:
        return "betyg_hogre_an_np"
    if delta < 0:
        return "betyg_lagre_an_np"
    return "betyg_lika_np"


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
            # MA_G1_PR/MA_G2_PR finns bara i fullformat; kompaktformat paddas med tomma strängar.
            # MA_G_PR är det sammansatta resultatet för delprov G och täcker båda formaten.
            "Ma": ["MA_A_PR", "MA_B_PR", "MA_C_PR", "MA_D_PR", "MA_E_PR", "MA_F_PR", "MA_G_PR"],
            # Alla åtta delprov A–H används. Nämnare: giltigt resultat (0 eller 1) på samtliga.
            "Sv/Sva": ["SV_A_PR", "SV_B_PR", "SV_C_PR", "SV_D_PR", "SV_E_PR", "SV_F_PR", "SV_G_PR", "SV_H_PR"],
        }.items():
            values = [np_passed(row.get(col)) for col in cols]
            valid = [value for value in values if value is not None]
            # Bara elever som deltagit i ALLA delprov ingår i nämnaren.
            godkand_np = all(valid) if len(valid) == len(cols) else None
            results.append({"amne": subject, "np_betyg": None, "godkand_np": godkand_np, "antal_delprov": len(valid)})
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
                # Ak 3 saknar betygsmatchning, sa kon behover kunna harledas direkt fran NP-raden.
                "kon": grade_row.get("kon") if grade_row else gender_from_personnr(np_row.get("PersonNr")),
                "sv_sva_grupp": grade_row.get("sv_sva_grupp") if grade_row else "oklar",
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
            for kon, elevgrupp, segment in segmented_groups(subject_rows):
                total = len(segment)
                passed = sum(1 for item in segment if item["godkand_np"])
                base = {
                    "lasar": lasar,
                    "arskurs": arskurs,
                    "niva": level,
                    "skolenhetskod": code,
                    "skolenhetsnamn": school_name(level, code, lookup),
                    "kon": kon,
                    "elevgrupp": elevgrupp,
                    "amne": subject,
                    "antal_np": total,
                    "antal_godkanda_np": passed,
                    "andel_godkanda_np": percentage(passed, total),
                    "antal_med_betygsmatch": sum(1 for item in segment if item["matched_grade"]),
                    "source": "local_scb_np",
                }
                result_rows.append(base)

                comparable = [item for item in segment if item["relation"]]
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
