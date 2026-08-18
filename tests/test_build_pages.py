from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BuildPagesPrivacyTests(unittest.TestCase):
    def test_pages_package_does_not_include_internal_output_json(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js saknas")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "scripts").mkdir()
            (root / "app").mkdir()
            (root / "data" / "processed" / "2025-2026" / "json").mkdir(parents=True)
            (root / "data" / "output" / "2025-2026" / "json").mkdir(parents=True)
            shutil.copy2(PROJECT_ROOT / "scripts" / "build-pages.js", root / "scripts" / "build-pages.js")
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "app" / "core.js").write_text(
                "const STATIC_PAGES_BUILD = false;", encoding="utf-8"
            )
            (root / "data" / "processed" / "2025-2026" / "json" / "safe.json").write_text(
                "[]", encoding="utf-8"
            )
            (root / "data" / "output" / "2025-2026" / "json" / "small-group.json").write_text(
                '[{"antal_betyg":1}]', encoding="utf-8"
            )

            subprocess.run([node, str(root / "scripts" / "build-pages.js")], check=True)

            self.assertTrue(root.joinpath("docs", "data", "processed", "2025-2026", "json", "safe.json").exists())
            self.assertFalse(root.joinpath("docs", "data", "output").exists())


if __name__ == "__main__":
    unittest.main()
