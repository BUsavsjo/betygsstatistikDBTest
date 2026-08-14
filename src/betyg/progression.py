from __future__ import annotations

import re
from typing import Any


SOURCE_AND_KEY_FIELDS = {"PersonNr", "_source_file", "_source_row"}


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
