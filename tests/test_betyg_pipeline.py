from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_paths import DEFAULT_LASAR, resolve_paths
from betyg.constants import AK9_SUBJECTS
from betyg.io import publish_processed_json
from betyg.metrics import eligibility, gender_from_personnr, merit, overview, sv_sva_group
from betyg.pipeline import control_rows


class MetricsTests(unittest.TestCase):
    def test_gender_from_personnr_uses_second_last_digit(self) -> None:
        self.assertEqual(gender_from_personnr("20100101-1234"), "Pojkar")
        self.assertEqual(gender_from_personnr("20100101-1244"), "Flickor")
        self.assertEqual(gender_from_personnr(""), "okänt")

    def test_sv_sva_group_prefers_distinct_states(self) -> None:
        self.assertEqual(sv_sva_group({"Sv": "C", "Sva": ""}), "SV")
        self.assertEqual(sv_sva_group({"Sv": "", "Sva": "B"}), "SVA")
        self.assertEqual(sv_sva_group({"Sv": "A", "Sva": "B"}), "SV_och_SVA")
        self.assertEqual(sv_sva_group({"Sv": "", "Sva": ""}), "oklar")

    def test_merit_uses_best_sv_sva_and_best_modern_language(self) -> None:
        row = {subject: "E" for subject in AK9_SUBJECTS if subject not in {"Sv", "Sva"}}
        row.update({"Sv": "C", "Sva": "A", "M1_betyg": "B", "M2_betyg": "D"})
        merit16, merit17 = merit(row, AK9_SUBJECTS)
        self.assertEqual(merit16, 170.0)
        self.assertEqual(merit17, 187.5)

    def test_eligibility_requires_core_subjects(self) -> None:
        row = {subject: "E" for subject in AK9_SUBJECTS}
        row["Sv"] = "F"
        row["Sva"] = ""
        result = eligibility(row, AK9_SUBJECTS)
        self.assertFalse(result["behorig_yrkesprogram"])
        self.assertFalse(result["behorig_hogskoleforberedande_nagot_program"])


class PublishTests(unittest.TestCase):
    def test_publish_processed_json_copies_only_whitelisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_base = root / "output"
            processed_base = root / "processed"
            source_dir = output_base / "2025-2026" / "json"
            source_dir.mkdir(parents=True)
            (source_dir / "manifest.json").write_text("{}", encoding="utf-8")
            (source_dir / "betygsstatistik_oversikt.json").write_text("[]", encoding="utf-8")
            (source_dir / "secret.json").write_text("{}", encoding="utf-8")

            target_dir = publish_processed_json(output_base, processed_base, "2025-2026")

            self.assertTrue((target_dir / "manifest.json").exists())
            self.assertTrue((target_dir / "betygsstatistik_oversikt.json").exists())
            self.assertFalse((target_dir / "secret.json").exists())


class ControlRowsTests(unittest.TestCase):
    def test_overview_includes_gender_and_sv_sva_segments(self) -> None:
        rows = [
            {
                "Skolenhetskod": "123",
                "kon": "Pojkar",
                "sv_sva_grupp": "SV",
                "meritvarde_16": 160,
                "meritvarde_17": 170,
                "uppnatt_alla_amnen": True,
                "behorig_yrkesprogram": True,
                "behorig_hogskoleforberedande_nagot_program": False,
            },
            {
                "Skolenhetskod": "123",
                "kon": "Flickor",
                "sv_sva_grupp": "SVA",
                "meritvarde_16": 180,
                "meritvarde_17": 190,
                "uppnatt_alla_amnen": False,
                "behorig_yrkesprogram": False,
                "behorig_hogskoleforberedande_nagot_program": False,
            },
        ]
        result = overview(rows, "2025-2026", 9, {"123": "Testskolan"})

        segments = {(row["niva"], row["kon"], row["elevgrupp"]) for row in result}
        self.assertIn(("skolenhet", "Alla", "Alla"), segments)
        self.assertIn(("skolenhet", "Pojkar", "Alla"), segments)
        self.assertIn(("skolenhet", "Flickor", "Alla"), segments)
        self.assertIn(("skolenhet", "Alla", "SV"), segments)
        self.assertIn(("skolenhet", "Alla", "SVA"), segments)

    def test_control_rows_counts_valid_and_special_codes(self) -> None:
        rows = [
            {"Skolenhetskod": "123", "kon": "Pojkar", "sv_sva_grupp": "SV", "Sv": "A", "Ma": "F"},
            {"Skolenhetskod": "123", "kon": "Flickor", "sv_sva_grupp": "SV", "Sv": "2", "Ma": ""},
            {"Skolenhetskod": "123", "kon": "Flickor", "sv_sva_grupp": "SVA", "Sv": "", "Ma": "Y"},
        ]
        lookup = {"123": "Testskolan"}
        result = control_rows(rows, "2025-2026", 9, ["Sv", "Ma"], lookup)
        sv_all = next(row for row in result if row["niva"] == "alla_skolenheter" and row["elevgrupp"] == "Alla" and row["amne"] == "Sv")
        self.assertEqual(sv_all["antal_giltiga_betyg"], 1)
        self.assertEqual(sv_all["specialkod_2"], 1)
        self.assertEqual(sv_all["antal_tomma"], 1)
        ma_sv = next(row for row in result if row["niva"] == "skolenhet" and row["elevgrupp"] == "SV" and row["amne"] == "Ma")
        self.assertEqual(ma_sv["antal_F"], 1)
        self.assertEqual(ma_sv["antal_tomma"], 1)


class ConfigPathsTests(unittest.TestCase):
    def test_resolve_paths_uses_default_project_year(self) -> None:
        paths = resolve_paths()
        self.assertEqual(paths.lasar, DEFAULT_LASAR)
        self.assertEqual(paths.output_dir, Path(paths.base_dir) / "data" / "output" / DEFAULT_LASAR)
        self.assertEqual(paths.json_dir, paths.output_dir / "json")

    def test_resolve_paths_allows_environment_override(self) -> None:
        with patch.dict("os.environ", {"BETYGSSTATISTIK_LASAR": "2024-2025"}, clear=False):
            paths = resolve_paths()
        self.assertEqual(paths.lasar, "2024-2025")
        self.assertEqual(paths.raw_betyg_dir, paths.raw_dir / "betyg" / "2024-2025")


if __name__ == "__main__":
    unittest.main()
