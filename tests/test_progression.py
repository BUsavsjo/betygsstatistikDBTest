from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from betyg.progression import (
    build_progression_document,
    compare_subject,
    deduplicate_rows,
    match_cohort,
    normalize_personnr,
    source_school_year,
    spearman,
)


def progression_pair(
    index: int,
    *,
    school: str = "59983229",
    gender_digit: int = 0,
    sva: bool = False,
) -> tuple[dict[str, str], dict[str, str]]:
    person = f"100101{index % 100:02d}{gender_digit}{index % 10}"
    ak6 = {
        "PersonNr": person,
        "Ma": "E",
        "En": "D",
        "Sv": "C",
        "Sva": "",
    }
    ak9 = {
        "PersonNr": person,
        "Skolenhetskod": school,
        "Ma": "C",
        "En": "D",
        "Sv": "" if sva else "B",
        "Sva": "B" if sva else "",
    }
    return ak6, ak9


class ProgressionIdentityTests(unittest.TestCase):
    def test_source_school_year_moves_both_years_back_three(self) -> None:
        self.assertEqual(source_school_year("2025-2026"), "2022-2023")

    def test_source_school_year_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "Ogiltigt läsår"):
            source_school_year("2025")

    def test_normalize_personnr_accepts_ten_or_twelve_digits_only(self) -> None:
        self.assertEqual(normalize_personnr("2010-01-02-1234"), "1001021234")
        self.assertEqual(normalize_personnr("100102-1234"), "1001021234")
        self.assertIsNone(normalize_personnr("0102-1234"))
        self.assertIsNone(normalize_personnr(""))


class ProgressionMatchingTests(unittest.TestCase):
    def test_identical_duplicates_collapse_but_conflicts_are_excluded(self) -> None:
        identical = {"PersonNr": "1001021234", "Ma": "C", "_source_file": "a.txt"}
        rows = [
            identical,
            {**identical, "_source_file": "b.txt"},
            {"PersonNr": "1001031235", "Ma": "C"},
            {"PersonNr": "1001031235", "Ma": "D"},
        ]

        unique, diagnostics = deduplicate_rows(rows)

        self.assertEqual(list(unique), ["1001021234"])
        self.assertEqual(
            diagnostics,
            {"ogiltiga_nycklar": 0, "identiska_dubbletter": 1, "motstridiga_dubbletter": 1},
        )

    def test_match_uses_personnr_not_school_code(self) -> None:
        ak6 = [{"PersonNr": "100102-1234", "Skolenhetskod": "OLD", "Ma": "E"}]
        ak9 = [{"PersonNr": "201001021234", "Skolenhetskod": "59983229", "Ma": "C"}]

        matched, diagnostics = match_cohort(ak6, ak9)

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0][1]["Skolenhetskod"], "59983229")
        self.assertEqual(diagnostics["matchade"], 1)


class ProgressionMetricTests(unittest.TestCase):
    def test_compare_subject_returns_rank_pair_for_valid_grades(self) -> None:
        self.assertEqual(compare_subject({"Ma": "E"}, {"Ma": "C"}, "Ma"), (1, 3))
        self.assertIsNone(compare_subject({"Ma": "2"}, {"Ma": "C"}, "Ma"))

    def test_sv_sva_uses_valid_course_grade_in_each_year(self) -> None:
        self.assertEqual(
            compare_subject(
                {"Sv": "D", "Sva": ""},
                {"Sv": "", "Sva": "C"},
                "Sv/Sva",
            ),
            (2, 3),
        )
        self.assertIsNone(
            compare_subject(
                {"Sv": "D", "Sva": "C"},
                {"Sv": "", "Sva": "C"},
                "Sv/Sva",
            )
        )

    def test_spearman_handles_ties_and_requires_variation(self) -> None:
        self.assertEqual(spearman([1, 2, 2, 4], [1, 2, 2, 4]), 1.0)
        self.assertIsNone(spearman([1, 1, 1], [1, 2, 3]))


class ProgressionAggregationTests(unittest.TestCase):
    def test_document_groups_by_ak9_school_gender_and_sva(self) -> None:
        matched = [
            progression_pair(index, gender_digit=index % 2, sva=index < 10)
            for index in range(20)
        ]
        unmatched_ak9 = [progression_pair(index + 40)[1] for index in range(4)]

        document = build_progression_document(
            matched,
            [pair[1] for pair in matched] + unmatched_ak9,
            "2022-2023",
            "2025-2026",
        )

        total = next(
            row
            for row in document["segment"]
            if row["niva"] == "huvudman"
            and row["kon"] == "Alla"
            and row["elevgrupp"] == "Alla"
        )
        sva = next(
            row
            for row in document["segment"]
            if row["niva"] == "huvudman"
            and row["kon"] == "Alla"
            and row["elevgrupp"] == "SVA"
        )
        self.assertEqual(total["matchning"]["antal_ak9"], 24)
        self.assertEqual(total["matchning"]["antal_matchade"], 20)
        self.assertEqual(total["matchning"]["matchningsgrad"], 83.33)
        self.assertFalse(sva["undertryckt"])
        self.assertGreater(total["oversikt"]["andel_hojda_betyg"], 0)

    def test_document_contains_no_identifying_keys(self) -> None:
        matched = [progression_pair(index) for index in range(10)]
        document = build_progression_document(
            matched,
            [pair[1] for pair in matched],
            "2022-2023",
            "2025-2026",
        )
        self.assertNotIn("PersonNr", str(document))
        self.assertNotIn("_source_file", str(document))


class ProgressionPrivacyTests(unittest.TestCase):
    def test_small_segment_contains_no_counts_or_metrics(self) -> None:
        matched = [progression_pair(index) for index in range(9)]

        document = build_progression_document(
            matched,
            [pair[1] for pair in matched],
            "2022-2023",
            "2025-2026",
        )

        total = next(
            row
            for row in document["segment"]
            if row["niva"] == "huvudman"
            and row["kon"] == "Alla"
            and row["elevgrupp"] == "Alla"
        )
        self.assertTrue(total["undertryckt"])
        self.assertIsNone(total["matchning"])
        self.assertIsNone(total["oversikt"])
        self.assertIsNone(total["merit_ak9"])

    def test_counterpart_is_suppressed_when_split_would_reveal_small_group(self) -> None:
        matched = [
            progression_pair(index, gender_digit=0)
            for index in range(12)
        ] + [
            progression_pair(index + 20, gender_digit=1)
            for index in range(8)
        ]

        document = build_progression_document(
            matched,
            [pair[1] for pair in matched],
            "2022-2023",
            "2025-2026",
        )

        gender_rows = [
            row
            for row in document["segment"]
            if row["niva"] == "huvudman"
            and row["elevgrupp"] == "Alla"
            and row["kon"] in {"Flickor", "Pojkar"}
        ]
        self.assertEqual({row["undertryckt"] for row in gender_rows}, {True})
        self.assertTrue(all(row["matchning"] is None for row in gender_rows))


if __name__ == "__main__":
    unittest.main()
