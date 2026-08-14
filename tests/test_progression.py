from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from betyg.progression import deduplicate_rows, match_cohort, normalize_personnr, source_school_year


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


if __name__ == "__main__":
    unittest.main()
