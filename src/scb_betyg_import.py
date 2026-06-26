from __future__ import annotations

import argparse
from datetime import date

from betyg.pipeline import build_year


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SCB grade txt files and create anonymized JSON statistics.")
    parser.add_argument("--lasar", required=True, help="School year folder, for example 2025-2026")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Copy approved aggregate JSON from data/output to data/processed for GitHub Pages.",
    )
    parser.add_argument(
        "--import-date",
        default=date.today().isoformat(),
        help="Date when source data was exported from the school system (YYYY-MM-DD). Defaults to today.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_year(args.lasar, publish=args.publish, import_date=args.import_date)
