from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Läsåret som analyseras
LASAR = "2024-2025"

RAW_DIR = BASE_DIR / "data" / "raw"
RAW_BETYG_DIR = RAW_DIR / "betyg" / LASAR
RAW_FRANVARO_DIR = RAW_DIR / "franvaro" / LASAR

OUTPUT_DIR = BASE_DIR / "data" / "output" / LASAR
DATA_MAPP = OUTPUT_DIR
JSON_MAPP = BASE_DIR / "data" /"output" / "json" / LASAR 

CONFIG_DIR = BASE_DIR / "config"
