from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LASAR = "2025-2026"


@dataclass(frozen=True)
class ProjectPaths:
    lasar: str
    base_dir: Path
    raw_dir: Path
    raw_betyg_dir: Path
    raw_franvaro_dir: Path
    output_dir: Path
    json_dir: Path
    config_dir: Path


def resolve_paths(lasar: str | None = None) -> ProjectPaths:
    selected_lasar = (lasar or os.environ.get("BETYGSSTATISTIK_LASAR") or DEFAULT_LASAR).strip()
    raw_dir = BASE_DIR / "data" / "raw"
    output_dir = BASE_DIR / "data" / "output" / selected_lasar
    return ProjectPaths(
        lasar=selected_lasar,
        base_dir=BASE_DIR,
        raw_dir=raw_dir,
        raw_betyg_dir=raw_dir / "betyg" / selected_lasar,
        raw_franvaro_dir=raw_dir / "franvaro" / selected_lasar,
        output_dir=output_dir,
        json_dir=output_dir / "json",
        config_dir=BASE_DIR / "config",
    )


PATHS = resolve_paths()

# Backward-compatible exports for older busavsjo_* scripts.
LASAR = PATHS.lasar
RAW_DIR = PATHS.raw_dir
RAW_BETYG_DIR = PATHS.raw_betyg_dir
RAW_FRANVARO_DIR = PATHS.raw_franvaro_dir
OUTPUT_DIR = PATHS.output_dir
DATA_MAPP = OUTPUT_DIR
JSON_MAPP = PATHS.json_dir
CONFIG_DIR = PATHS.config_dir
