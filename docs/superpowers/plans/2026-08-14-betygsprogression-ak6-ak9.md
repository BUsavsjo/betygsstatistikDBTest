# Betygsprogression åk 6–9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bygga en publik, anonymiserad progressionsvy som matchar samma elever lokalt mellan åk 6 och åk 9 och visar resultat för huvudmannen, Hofgårdsskolan och Rörviks skola.

**Architecture:** En ny ren Pythonmodul ansvarar för kohortmatchning, beräkningar och sekretess. Den befintliga importpipelinen läser historisk åk 6-data, anropar modulen och skriver ett uttryckligen whitelistat JSON-aggregat. En separat frontendmodul laddar aggregatet och renderar en egen flik med egna filter.

**Tech Stack:** Python 3 standardbibliotek, befintlig SCB-import, JavaScript utan nya ramverk, Chart.js, `unittest`, Playwright och statisk GitHub Pages-publicering.

## Global Constraints

- Rådata, personnummer, hashade personnummer, namn, klass och elevrader får aldrig publiceras eller läggas i Git.
- Minsta publicerbara grupp är exakt 10 matchade elever; sekundär undertryckning ska hindra baklängesberäkning.
- Skolgruppering ska utgå från skolenheten i åk 9: Hofgårdsskolan `59983229` och Rörviks skola `74170440`.
- SV/SVA och kön ska utgå från elevens åk 9-rad.
- Meritvärde ska vara ett sekundärt slutmått och får inte beskrivas som direkt progression mellan åk 6 och åk 9.
- UI-text ska vara UTF-8 och ha korrekta svenska tecken.
- Inga nya externa Python- eller JavaScriptberoenden ska införas.
- Diagnostikfliken och befintliga datavyer ska bevaras.
- Efter import- eller beräkningsändringar ska `python src/scb_betyg_import.py --lasar <slutläsår> --publish` köras före `node scripts/build-pages.js` när källdatan finns på plats.

---

### Task 1: Kohortår, personnummer och säker matchning

**Files:**
- Create: `src/betyg/progression.py`
- Create: `tests/test_progression.py`

**Interfaces:**
- Produces: `source_school_year(ak9_lasar: str) -> str`
- Produces: `normalize_personnr(value: object) -> str | None`
- Produces: `deduplicate_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]`
- Produces: `match_cohort(ak6_rows: list[dict[str, Any]], ak9_rows: list[dict[str, Any]]) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, int]]`

- [ ] **Step 1: Skriv testet som fångar fel källläsår och osäker nyckelnormalisering**

```python
import unittest

from betyg.progression import normalize_personnr, source_school_year


class ProgressionIdentityTests(unittest.TestCase):
    def test_source_school_year_moves_both_years_back_three(self) -> None:
        self.assertEqual(source_school_year("2025-2026"), "2022-2023")

    def test_normalize_personnr_accepts_ten_or_twelve_digits_only(self) -> None:
        self.assertEqual(normalize_personnr("2010-01-02-1234"), "1001021234")
        self.assertEqual(normalize_personnr("100102-1234"), "1001021234")
        self.assertIsNone(normalize_personnr("0102-1234"))
        self.assertIsNone(normalize_personnr(""))
```

- [ ] **Step 2: Kör testet och verifiera rött felorsak**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: FAIL med `ModuleNotFoundError: No module named 'betyg.progression'`.

- [ ] **Step 3: Implementera minsta års- och personnummerfunktioner**

```python
from __future__ import annotations

import re
from typing import Any


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
```

- [ ] **Step 4: Kör testet och verifiera grönt**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: 2 tests, PASS.

- [ ] **Step 5: Skriv tester som fångar felaktig dubblett- och skolmatchning**

```python
from betyg.progression import deduplicate_rows, match_cohort


class ProgressionMatchingTests(unittest.TestCase):
    def test_identical_duplicates_collapse_but_conflicts_are_excluded(self) -> None:
        identical = {"PersonNr": "1001021234", "Ma": "C", "_source_file": "a.txt"}
        rows = [identical, {**identical, "_source_file": "b.txt"}, {"PersonNr": "1001031235", "Ma": "C"}, {"PersonNr": "1001031235", "Ma": "D"}]
        unique, diagnostics = deduplicate_rows(rows)
        self.assertEqual(list(unique), ["1001021234"])
        self.assertEqual(diagnostics, {"ogiltiga_nycklar": 0, "identiska_dubbletter": 1, "motstridiga_dubbletter": 1})

    def test_match_uses_personnr_not_school_code(self) -> None:
        ak6 = [{"PersonNr": "100102-1234", "Skolenhetskod": "OLD", "Ma": "E"}]
        ak9 = [{"PersonNr": "201001021234", "Skolenhetskod": "59983229", "Ma": "C"}]
        matched, diagnostics = match_cohort(ak6, ak9)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0][1]["Skolenhetskod"], "59983229")
        self.assertEqual(diagnostics["matchade"], 1)
```

- [ ] **Step 6: Kör och verifiera att de nya testerna faller på saknade funktioner**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: FAIL med importfel för `deduplicate_rows` eller `match_cohort`.

- [ ] **Step 7: Implementera dubblettkontroll och matchning utan identifierande diagnostik**

Implementera jämförelse av rader utan `_source_file` och `_source_row`. Motstridiga dubbletter ska tas bort helt. Diagnostiken ska endast innehålla heltal och aldrig nyckelvärden.

```python
SOURCE_FIELDS = {"_source_file", "_source_row"}


def _row_signature(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(value)) for key, value in row.items() if key not in SOURCE_FIELDS))


def deduplicate_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    invalid = 0
    for row in rows:
        key = normalize_personnr(row.get("PersonNr"))
        if key is None:
            invalid += 1
        else:
            grouped.setdefault(key, []).append(row)
    unique: dict[str, dict[str, Any]] = {}
    identical = conflicts = 0
    for key, candidates in grouped.items():
        signatures = {_row_signature(row) for row in candidates}
        if len(signatures) == 1:
            unique[key] = candidates[0]
            identical += len(candidates) - 1
        else:
            conflicts += 1
    return unique, {"ogiltiga_nycklar": invalid, "identiska_dubbletter": identical, "motstridiga_dubbletter": conflicts}


def match_cohort(ak6_rows, ak9_rows):
    ak6, ak6_diagnostics = deduplicate_rows(ak6_rows)
    ak9, ak9_diagnostics = deduplicate_rows(ak9_rows)
    pairs = [(ak6[key], row) for key, row in ak9.items() if key in ak6]
    return pairs, {
        "ak6_giltiga": len(ak6), "ak9_giltiga": len(ak9), "matchade": len(pairs),
        "ak6_omatchade": len(ak6) - len(pairs), "ak9_omatchade": len(ak9) - len(pairs),
        "ak6_dubbletter": ak6_diagnostics, "ak9_dubbletter": ak9_diagnostics,
    }
```

- [ ] **Step 8: Kör progressionstester och hela Python-sviten**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: PASS.

Run: `python -m unittest discover -s tests -v`

Expected: alla tester PASS.

- [ ] **Step 9: Commit**

```text
git add src/betyg/progression.py tests/test_progression.py
git commit -m "feat: matcha elevkullar for progression"
```

### Task 2: Ämnesprogression, samband och sekretess

**Files:**
- Modify: `src/betyg/progression.py`
- Modify: `tests/test_progression.py`

**Interfaces:**
- Consumes: `match_cohort(...)` från Task 1
- Produces: `compare_subject(ak6_row: dict[str, Any], ak9_row: dict[str, Any], subject: str) -> tuple[int, int] | None`
- Produces: `spearman(values_x: list[float], values_y: list[float]) -> float | None`
- Produces: `build_progression_document(matched_rows: list[tuple[dict[str, Any], dict[str, Any]]], ak9_rows: list[dict[str, Any]], ak6_lasar: str, ak9_lasar: str, privacy_threshold: int = 10) -> dict[str, Any]`
- Internal: `_aggregate_segment(level: str, school_code: str | None, school_name: str, gender: str, group: str, pairs: list[tuple[dict[str, Any], dict[str, Any]]], eligible_ak9: list[dict[str, Any]], threshold: int) -> dict[str, Any]`
- Internal: `_apply_secondary_suppression(segments: list[dict[str, Any]]) -> None`
- Internal: `_assert_public_document(value: Any) -> None`

- [ ] **Step 1: Skriv tester för samma ämne, SV/SVA och betygsövergångar**

```python
from betyg.progression import compare_subject


class ProgressionMetricTests(unittest.TestCase):
    def test_compare_subject_returns_rank_pair_for_valid_grades(self) -> None:
        self.assertEqual(compare_subject({"Ma": "E"}, {"Ma": "C"}, "Ma"), (1, 3))
        self.assertIsNone(compare_subject({"Ma": "2"}, {"Ma": "C"}, "Ma"))

    def test_sv_sva_uses_valid_course_grade_in_each_year(self) -> None:
        self.assertEqual(compare_subject({"Sv": "D", "Sva": ""}, {"Sv": "", "Sva": "C"}, "Sv/Sva"), (2, 3))
```

- [ ] **Step 2: Kör och verifiera rött failure**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: FAIL eftersom `compare_subject` saknas.

- [ ] **Step 3: Implementera betygsrang och explicit lista över jämförbara ämnen**

Använd `GRADE_RANK = {"F": 0, "E": 1, "D": 2, "C": 3, "B": 4, "A": 5}` och en fast `COMPARABLE_SUBJECTS` enligt designspecifikationen. För `Sv/Sva` ska ett giltigt kursbetyg användas; dubbla giltiga kursbetyg ska uteslutas ur den specifika ämnesjämförelsen och räknas i diagnostik senare.

```python
GRADE_RANK = {"F": 0, "E": 1, "D": 2, "C": 3, "B": 4, "A": 5}
COMPARABLE_SUBJECTS = ("Bl", "En", "Hkk", "Idh", "Ma", "Mu", "Bi", "Fy", "Ke", "Ge", "Hi", "Re", "Sh", "Sl", "Sv/Sva", "Tn", "Tk")


def _sv_sva_grade(row: dict[str, Any]) -> str | None:
    values = [value for key in ("Sv", "Sva") if (value := grade(row.get(key))) is not None]
    return values[0] if len(values) == 1 else None


def compare_subject(ak6_row, ak9_row, subject):
    ak6_grade = _sv_sva_grade(ak6_row) if subject == "Sv/Sva" else grade(ak6_row.get(subject))
    ak9_grade = _sv_sva_grade(ak9_row) if subject == "Sv/Sva" else grade(ak9_row.get(subject))
    if ak6_grade is None or ak9_grade is None:
        return None
    return GRADE_RANK[ak6_grade], GRADE_RANK[ak9_grade]
```

- [ ] **Step 4: Kör och verifiera grönt**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: PASS.

- [ ] **Step 5: Skriv tester för rangkorrelation och segmentens observerbara kontrakt**

```python
from betyg.progression import build_progression_document, spearman


def progression_pair(index: int, *, school: str = "59983229", gender_digit: int = 0, sva: bool = False):
    person = f"1001{index % 9 + 1:02d}{index % 99:02d}{gender_digit}{index % 10}"
    ak6 = {"PersonNr": person, "Ma": "E", "En": "D", "Sv": "C", "Sva": ""}
    ak9 = {"PersonNr": person, "Skolenhetskod": school, "Ma": "C", "En": "D", "Sv": "" if sva else "B", "Sva": "B" if sva else ""}
    return ak6, ak9


class ProgressionAggregationTests(unittest.TestCase):
    def test_spearman_handles_ties_and_requires_variation(self) -> None:
        self.assertEqual(spearman([1, 2, 2, 4], [1, 2, 2, 4]), 1.0)
        self.assertIsNone(spearman([1, 1, 1], [1, 2, 3]))

    def test_document_groups_by_ak9_school_gender_and_sva(self) -> None:
        matched = [progression_pair(index, gender_digit=index % 2, sva=index < 10) for index in range(20)]
        document = build_progression_document(matched, [pair[1] for pair in matched], "2022-2023", "2025-2026")
        total = next(row for row in document["segment"] if row["niva"] == "huvudman" and row["kon"] == "Alla" and row["elevgrupp"] == "Alla")
        sva = next(row for row in document["segment"] if row["niva"] == "huvudman" and row["kon"] == "Alla" and row["elevgrupp"] == "SVA")
        self.assertEqual(total["matchning"]["antal_matchade"], 20)
        self.assertFalse(sva["undertryckt"])
        self.assertGreater(total["oversikt"]["andel_hojda_betyg"], 0)
```

- [ ] **Step 6: Kör och verifiera att aggregeringstesterna faller**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: FAIL eftersom `spearman` eller `build_progression_document` saknas.

- [ ] **Step 7: Implementera rangkorrelation och segmentaggregering**

Implementera med standardbiblioteket: genomsnittsranger för lika värden och Pearsonkorrelation på rangerna. Bygg segment för huvudman och de två skolorna, därefter Alla/Flickor/Pojkar och Alla/SV/SVA utifrån åk 9-raden. Använd befintliga `gender_from_personnr`, `sv_sva_group` och `merit` för konsekventa definitioner.

```python
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
    x, y = _average_ranks(values_x), _average_ranks(values_y)
    mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    denominator = (sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y)) ** 0.5
    return round(numerator / denominator, 3) if denominator else None


def build_progression_document(matched_rows, ak9_rows, ak6_lasar, ak9_lasar, privacy_threshold=10):
    schools = (("huvudman", None, "Sävsjö kommun"), ("skolenhet", "59983229", "Hofgårdsskolan"), ("skolenhet", "74170440", "Rörviks skola"))
    segments = []
    for level, school_code, school_name in schools:
        school_pairs = [pair for pair in matched_rows if school_code is None or clean(pair[1].get("Skolenhetskod")) == school_code]
        for gender in ("Alla", "Flickor", "Pojkar"):
            for group in ("Alla", "SV", "SVA"):
                pairs = [pair for pair in school_pairs if (gender == "Alla" or gender_from_personnr(pair[1].get("PersonNr")) == gender) and (group == "Alla" or sv_sva_group(pair[1]) == group)]
                eligible_ak9 = [row for row in ak9_rows if (school_code is None or clean(row.get("Skolenhetskod")) == school_code) and (gender == "Alla" or gender_from_personnr(row.get("PersonNr")) == gender) and (group == "Alla" or sv_sva_group(row) == group)]
                segments.append(_aggregate_segment(level, school_code, school_name, gender, group, pairs, eligible_ak9, privacy_threshold))
    _apply_secondary_suppression(segments)
    document = {"schema_version": 1, "status": "ok", "source": "local_scb_progression", "ak6_lasar": ak6_lasar, "ak9_lasar": ak9_lasar, "sekretessgrans": privacy_threshold, "segment": segments}
    _assert_public_document(document)
    return document
```

Implementera `_aggregate_segment` genom att skapa alla `compare_subject`-par, beräkna bokstavsrang, övergångar, andelar, elevindex med minst fem ämnen, ämnesrader samt åk 9-merit med den befintliga `merit`-funktionen. Alla procenttal avrundas till två decimaler och korrelationer till tre.

- [ ] **Step 8: Skriv tester för primär och sekundär undertryckning**

```python
class ProgressionPrivacyTests(unittest.TestCase):
    def test_small_segment_contains_no_counts_or_metrics(self) -> None:
        matched = [progression_pair(index) for index in range(9)]
        document = build_progression_document(matched, [pair[1] for pair in matched], "2022-2023", "2025-2026")
        total = next(row for row in document["segment"] if row["niva"] == "huvudman" and row["kon"] == "Alla" and row["elevgrupp"] == "Alla")
        self.assertTrue(total["undertryckt"])
        self.assertIsNone(total["matchning"])
        self.assertIsNone(total["oversikt"])
        self.assertIsNone(total["merit_ak9"])

    def test_counterpart_is_suppressed_when_binary_split_would_reveal_small_group(self) -> None:
        matched = [progression_pair(index, gender_digit=0) for index in range(12)] + [progression_pair(index + 20, gender_digit=1) for index in range(8)]
        document = build_progression_document(matched, [pair[1] for pair in matched], "2022-2023", "2025-2026")
        gender_rows = [row for row in document["segment"] if row["niva"] == "huvudman" and row["elevgrupp"] == "Alla" and row["kon"] in {"Flickor", "Pojkar"}]
        self.assertEqual({row["undertryckt"] for row in gender_rows}, {True})
        self.assertTrue(all(row["matchning"] is None for row in gender_rows))
```

- [ ] **Step 9: Kör och verifiera rött sekretessfailure**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: minst ett privacy-test FAIL innan undertryckningen finns.

- [ ] **Step 10: Implementera undertryckning och säkerhetsskanning**

Undertryck hela segment under 10. Om en köns- eller SV/SVA-del i en publicerad partition undertrycks ska dess synliga motpart också undertryckas. Undertryck ämnesrader separat när de har färre än 10 jämförbara elever. Avsluta dokumentbyggandet med en rekursiv kontroll som avvisar nycklarna `PersonNr`, `Fornamn`, `Efternamn`, `Klass`, `_source_file` och `_source_row`.

```python
FORBIDDEN_PUBLIC_KEYS = {"PersonNr", "Fornamn", "Efternamn", "Klass", "_source_file", "_source_row"}


def _suppress(segment: dict[str, Any]) -> None:
    segment.update({"undertryckt": True, "matchning": None, "oversikt": None, "merit_ak9": None, "amnen": None})


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
```

- [ ] **Step 11: Kör progressionstester och hela Python-sviten**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: PASS.

Run: `python -m unittest discover -s tests -v`

Expected: alla tester PASS.

- [ ] **Step 12: Commit**

```text
git add src/betyg/progression.py tests/test_progression.py
git commit -m "feat: berakna anonymiserad betygsprogression"
```

### Task 3: Importflöde, diagnostik och publiceringswhitelist

**Files:**
- Create: `src/betyg/progression_pipeline.py`
- Modify: `src/betyg/pipeline.py`
- Modify: `src/betyg/constants.py`
- Modify: `tests/test_progression.py`
- Modify: `tests/test_betyg_pipeline.py`

**Interfaces:**
- Consumes: `source_school_year`, `match_cohort` och `build_progression_document`
- Produces: `build_progression_files(grade_raw: Path, output_dir: Path, ak9_lasar: str, ak9_rows: list[dict[str, Any]]) -> dict[str, Any]`
- Produces files: `json/betygsprogression_ak6_ak9.json` och `diagnostik/progression_ak6_ak9.json`

- [ ] **Step 1: Skriv integrationstestet för historisk källmapp och saknat underlag**

```python
import tempfile
from pathlib import Path

from betyg.progression_pipeline import build_progression_files


class ProgressionPipelineTests(unittest.TestCase):
    def test_missing_historical_source_writes_safe_unavailable_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = build_progression_files(root / "raw", root / "output", "2025-2026", [])
            self.assertEqual(result["status"], "saknar_underlag")
            public_path = root / "output" / "json" / "betygsprogression_ak6_ak9.json"
            self.assertTrue(public_path.exists())
            self.assertNotIn("PersonNr", public_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Kör och verifiera importfelet**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: FAIL eftersom `betyg.progression_pipeline` saknas.

- [ ] **Step 3: Implementera isolerad filorkestrering**

`build_progression_files` ska använda `read_grade_files(grade_raw, source_school_year(ak9_lasar), SPECS[6])`, skapa säker diagnostik och alltid skriva ett publikt statusdokument. När källdatan finns matchar den historiska rader mot de redan inlästa åk 9-raderna.

```python
def build_progression_files(grade_raw: Path, output_dir: Path, ak9_lasar: str, ak9_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ak6_lasar = source_school_year(ak9_lasar)
    ak6_rows, source_diagnostics = read_grade_files(grade_raw, ak6_lasar, SPECS[6])
    if not ak6_rows or not ak9_rows:
        public = {
            "schema_version": 1, "status": "saknar_underlag", "source": "local_scb_progression",
            "ak6_lasar": ak6_lasar, "ak9_lasar": ak9_lasar, "sekretessgrans": 10, "segment": [],
        }
        diagnostics = {"status": "saknar_underlag", "ak6_lasar": ak6_lasar, "ak9_lasar": ak9_lasar, "ak6_rader": len(ak6_rows), "ak9_rader": len(ak9_rows), "source_diagnostics": source_diagnostics}
    else:
        matched, match_diagnostics = match_cohort(ak6_rows, ak9_rows)
        public = build_progression_document(matched, ak9_rows, ak6_lasar, ak9_lasar)
        diagnostics = {"status": "ok", "ak6_lasar": ak6_lasar, "ak9_lasar": ak9_lasar, **match_diagnostics, "source_diagnostics": source_diagnostics}
    write_json(output_dir / "json" / "betygsprogression_ak6_ak9.json", public)
    write_json(output_dir / "diagnostik" / "progression_ak6_ak9.json", diagnostics)
    return public
```

- [ ] **Step 4: Kör och verifiera grönt**

Run: `python -m unittest discover -s tests -p "test_progression.py" -v`

Expected: PASS.

- [ ] **Step 5: Skriv pipeline- och whitelisttest före koppling till produktion**

Utöka befintligt `PublishTests.test_publish_processed_json_copies_only_whitelisted_files` med en källfil `betygsprogression_ak6_ak9.json` och förvänta att den kopieras. Lägg dessutom ett temporärt `build_year`-test som verifierar att saknad historisk data inte hindrar `manifest.json` och att progressionsfilen får `status: "saknar_underlag"`.

- [ ] **Step 6: Kör och verifiera att whitelisttestet faller**

Run: `python -m unittest discover -s tests -p "test_betyg_pipeline.py" -v`

Expected: FAIL eftersom progressionsfilen inte finns i `PUBLIC_JSON_FILES` eller inte skapas av `build_year`.

- [ ] **Step 7: Koppla progressionsmodulen till befintlig pipeline**

Samla den aktuella åk 9-batchen i `build_year`, anropa `build_progression_files` efter betygsinläsningen och lägg endast status och antal i manifestet. Lägg `betygsprogression_ak6_ak9.json` i `PUBLIC_JSON_FILES`. Ett progressionsfel ska ge ett säkert statusdokument och diagnostik men inte stoppa ordinarie import; programmeringsfel ska fortfarande synas i testerna och får inte döljas med en bred `except Exception`.

```python
# constants.py
PUBLIC_JSON_FILES = [
    "manifest.json",
    "betygsstatistik_oversikt.json",
    "betygsstatistik_sv_sva.json",
    "betygsstatistik_betygsfordelning_amne.json",
    "betygsstatistik_kontroll_betyg.json",
    "np_andel_godkanda.json",
    "np_betyg_relation.json",
    "skolenheter_lookup.json",
    "betygsprogression_ak6_ak9.json",
]

# pipeline.py, efter betygsbatcherna men före manifestet skrivs
ak9_rows = next((rows for spec, rows, _ in grade_batches if spec.arskurs == 9), [])
progression = build_progression_files(grade_raw, output_dir, lasar, ak9_rows)
manifest["progression"] = {
    "status": progression["status"],
    "ak6_lasar": progression["ak6_lasar"],
    "ak9_lasar": progression["ak9_lasar"],
}
```

- [ ] **Step 8: Kör all Pythonverifiering**

Run: `python -m unittest discover -s tests -v`

Expected: alla tester PASS utan personuppgifter i terminalutskriften.

- [ ] **Step 9: Commit**

```text
git add src/betyg/progression_pipeline.py src/betyg/pipeline.py src/betyg/constants.py tests/test_progression.py tests/test_betyg_pipeline.py
git commit -m "feat: importera och publicera progressionsdata"
```

### Task 4: Progressionsflik, filter och visualisering

**Files:**
- Create: `app/progression.js`
- Modify: `app/local-data.js`
- Modify: `app/init.js`
- Modify: `index.html`
- Create: `tests/fixtures/betygsprogression_ak6_ak9.json`
- Modify: `tests/e2e/filter-vyer-tabeller.spec.js`

**Interfaces:**
- Consumes: `local.progression` från `tryLoadLocalSource`
- Produces: `initializeProgressionView(progression: object) -> void`
- Produces: `renderProgressionView() -> void`
- Internal: `populateProgressionFilters()`, `updateProgressionFilters()`, `selectedProgressionSegment()`, `renderProgressionUnavailable()`, `renderProgressionSuppressed()`, `renderProgressionCards()`, `renderProgressionCharts()` och `renderProgressionTable()`
- Produces DOM ids: `progressionCohortFilter`, `progressionSchoolFilter`, `progressionGenderFilter`, `progressionGroupFilter`, `progressionStatus`, `progressionCards`, `progressionChangeChart`, `progressionGradeChart`, `progressionRows`

- [ ] **Step 1: Skapa anonym testfixture**

Skapa ett JSON-dokument med `schema_version: 1`, en publicerbar huvudmannarad, en publicerbar skolrad, en undertryckt skolrad samt två ämnesrader. Fixturen ska endast innehålla aggregat och inga elevliknande identifierare.

```json
{
  "schema_version": 1,
  "status": "ok",
  "source": "test_fixture",
  "ak6_lasar": "2022-2023",
  "ak9_lasar": "2025-2026",
  "sekretessgrans": 10,
  "segment": [
    {
      "niva": "huvudman", "skolenhetskod": null, "skolenhetsnamn": "Sävsjö kommun", "kon": "Alla", "elevgrupp": "Alla", "undertryckt": false,
      "matchning": {"antal_ak9": 40, "antal_matchade": 36, "matchningsgrad": 90.0},
      "oversikt": {"antal_betygspar": 102, "genomsnittlig_forandring": 0.4, "andel_hojda_betyg": 50.0, "andel_oforandrade_betyg": 35.0, "andel_sankta_betyg": 15.0, "korrelation": 0.62},
      "merit_ak9": {"genomsnitt_merit_16": 218.5, "genomsnitt_merit_17": 231.0, "korrelation_ak6_index_merit_16": 0.59},
      "amnen": [
        {"amne": "Ma", "amnesnamn": "Matematik", "undertryckt": false, "antal_elever": 35, "genomsnitt_ak6": 2.1, "genomsnitt_ak9": 2.7, "genomsnittlig_forandring": 0.6, "andel_hojda": 55.0, "andel_oforandrade": 30.0, "andel_sankta": 15.0, "korrelation": 0.64},
        {"amne": "En", "amnesnamn": "Engelska", "undertryckt": false, "antal_elever": 34, "genomsnitt_ak6": 2.5, "genomsnitt_ak9": 2.8, "genomsnittlig_forandring": 0.3, "andel_hojda": 45.0, "andel_oforandrade": 40.0, "andel_sankta": 15.0, "korrelation": 0.71}
      ]
    },
    {"niva": "skolenhet", "skolenhetskod": "59983229", "skolenhetsnamn": "Hofgårdsskolan", "kon": "Alla", "elevgrupp": "SVA", "undertryckt": true, "matchning": null, "oversikt": null, "merit_ak9": null, "amnen": null},
    {"niva": "skolenhet", "skolenhetskod": "74170440", "skolenhetsnamn": "Rörviks skola", "kon": "Alla", "elevgrupp": "Alla", "undertryckt": true, "matchning": null, "oversikt": null, "merit_ak9": null, "amnen": null}
  ]
}
```

- [ ] **Step 2: Skriv det fallande Playwrighttestet för flik och filter**

```javascript
test('visar anonymiserad progression och filtrerar skola, kön och SVA', async ({ page }) => {
  await page.route('**/betygsprogression_ak6_ak9.json', route =>
    route.fulfill({path: require('path').join(__dirname, '..', 'fixtures', 'betygsprogression_ak6_ak9.json')}),
  );
  await waitForAppReady(page);
  await page.locator('[data-tab="progression"]').click();
  await expect(page.locator('#tab-progression')).toHaveClass(/active/);
  await expect(page.locator('#progressionCards')).toContainText('Matchade elever');
  await page.locator('#progressionSchoolFilter').selectOption('59983229');
  await page.locator('#progressionGroupFilter').selectOption('SVA');
  await expect(page.locator('#progressionStatus')).toContainText(/Hofgårdsskolan|gruppen är för liten/);
});
```

- [ ] **Step 3: Kör och verifiera rött UI-failure**

Run: `npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"`

Expected: FAIL eftersom fliken eller dess DOM-element saknas.

- [ ] **Step 4: Ladda progressionsfilen valfritt utan fallback till demo**

Utöka `tryLoadLocalSource` med `fetchJsonOptional(`${base}/betygsprogression_ak6_ak9.json`, null)` och returnera `progression`. Progressionsvyn ska använda filen från samma valda bas som ordinarie lokaldata; den får inte hämta progressionsdata från en svagare demo- eller PxWeb-källa.

```javascript
const [control, npPass, npRelation, progression] = await Promise.all([
  fetchJsonOptional(`${base}/betygsstatistik_kontroll_betyg.json`, []),
  fetchJsonOptional(`${base}/np_andel_godkanda.json`, []),
  fetchJsonOptional(`${base}/np_betyg_relation.json`, []),
  fetchJsonOptional(`${base}/betygsprogression_ak6_ak9.json`, null),
]);
return {base, sourceKind, isDemo, manifest, overview, svSva, distribution, control, npPass, npRelation, progression};
```

- [ ] **Step 5: Lägg till flikens semantiska HTML**

Lägg till fliken `data-tab="progression"`, separata labelkopplade select-element, statusyta, fyra sammanfattningskort, två canvas-element, merit-/sambandsförklaring, tabell och metodruta. Använd exakt texten **Resultatet visas inte eftersom gruppen är för liten.** för undertryckta segment.

```html
<div class="tab" data-tab="progression">Progression åk 6–9</div>
<section id="tab-progression" class="panel">
  <div class="box">
    <h2>Progression åk 6–9</h2>
    <div class="filters progression-filters">
      <label>Elevkull <select id="progressionCohortFilter"></select></label>
      <label>Skola <select id="progressionSchoolFilter"></select></label>
      <label>Kön <select id="progressionGenderFilter"></select></label>
      <label>Kursplan <select id="progressionGroupFilter"></select></label>
    </div>
    <p id="progressionStatus" class="small"></p>
  </div>
  <section id="progressionCards" class="grid"></section>
  <div class="box"><h2>Förändring per ämne</h2><div class="chart"><canvas id="progressionChangeChart"></canvas></div></div>
  <div class="box"><h2>Genomsnittligt betyg</h2><div class="chart"><canvas id="progressionGradeChart"></canvas></div></div>
  <div class="box"><div class="tw"><table><thead><tr><th>Ämne</th><th>Elever</th><th>Åk 6</th><th>Åk 9</th><th>Förändring</th><th>Höjt</th><th>Oförändrat</th><th>Sänkt</th><th>Samband</th></tr></thead><tbody id="progressionRows"></tbody></table></div></div>
  <div id="progressionMethod" class="box"></div>
</section>
```

- [ ] **Step 6: Implementera `app/progression.js`**

Håll ett separat filterstate med kohort, skola, kön och elevgrupp. Matcha ett enda färdigaggregerat segment, rendera aldrig nullvärden som noll och förstör tidigare Chart.js-instans innan omritning. Undertryckta segment ska endast visa sekretessmeddelandet. `status: "saknar_underlag"` ska visa var de två källmapparna förväntas finnas utan att visa tekniska personuppgifter.

```javascript
const progressionState = {data:null, school:'huvudman', gender:'Alla', group:'Alla'};

function initializeProgressionView(progression){
  progressionState.data = progression;
  populateProgressionFilters();
  renderProgressionView();
}

function selectedProgressionSegment(){
  const data = progressionState.data;
  if(!data || data.status !== 'ok') return null;
  return data.segment.find(row =>
    (progressionState.school === 'huvudman' ? row.niva === 'huvudman' : row.skolenhetskod === progressionState.school)
    && row.kon === progressionState.gender
    && row.elevgrupp === progressionState.group
  ) || null;
}

function renderProgressionView(){
  const data = progressionState.data;
  if(!data || data.status === 'saknar_underlag') return renderProgressionUnavailable(data);
  const segment = selectedProgressionSegment();
  if(!segment || segment.undertryckt) return renderProgressionSuppressed();
  renderProgressionCards(segment);
  renderProgressionCharts(segment.amnen || []);
  renderProgressionTable(segment.amnen || []);
}
```

Implementera de fyra renderingshjälparna med befintliga `esc`, `fmt` och `makeChart`. `renderProgressionSuppressed` ska tömma kort, tabell och diagram innan sekretessmeddelandet visas.

- [ ] **Step 7: Koppla initiering och filterhändelser**

Lägg `app/progression.js` efter `app/local-data.js` i `index.html`. Anropa `initializeProgressionView(local.progression)` från `renderLocalData`. Registrera `change` för de fyra progressionsfiltren i `app/init.js` och anropa `renderProgressionView`.

```javascript
['progressionCohortFilter','progressionSchoolFilter','progressionGenderFilter','progressionGroupFilter'].forEach(id => {
  $(id).addEventListener('change', updateProgressionFilters);
});

// renderLocalData(local)
initializeProgressionView(local.progression);
```

- [ ] **Step 8: Kör Playwrighttestet till grönt**

Run: `npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"`

Expected: PASS.

- [ ] **Step 9: Skriv och kör testet för undertryckt grupp och saknat underlag**

Utöka Playwrighttestet med val av den undertryckta skolraden och verifiera sekretessmeddelandet samt att `progressionRows` inte innehåller numeriska resultat. Lägg ett separat test där progressionsanropet returnerar `status: "saknar_underlag"` och verifiera att ordinarie översikt fortfarande fungerar.

Run: `npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "progression"`

Expected: PASS.

- [ ] **Step 10: Kör hela UI-sviten**

Run: `npm run test:e2e`

Expected: alla Playwrighttester PASS.

- [ ] **Step 11: Commit**

```text
git add app/progression.js app/local-data.js app/init.js index.html tests/fixtures/betygsprogression_ak6_ak9.json tests/e2e/filter-vyer-tabeller.spec.js
git commit -m "feat: visa progression mellan ak 6 och 9"
```

### Task 5: Dokumentation, Pages-paket och källdatagräns

**Files:**
- Modify: `README.md`
- Modify generated Pages files under: `docs/`
- Verify: `data/processed/<slutläsår>/json/betygsprogression_ak6_ak9.json`

**Interfaces:**
- Consumes: befintligt CLI `python src/scb_betyg_import.py --lasar <slutläsår> --publish`
- Produces: dokumenterat källäge och ett Pages-paket som innehåller progressionsmodulen och endast godkänd JSON

- [ ] **Step 1: Uppdatera README med källmapp och tolkning**

Dokumentera exemplet:

```text
data/raw/betyg/2022-2023/ak6/*.txt
data/raw/betyg/2025-2026/ak9/*.txt
python src/scb_betyg_import.py --lasar 2025-2026 --publish
node scripts/build-pages.js
```

Beskriv matchning på personnummer lokalt, gruppering efter åk 9-skola, sekretessgräns 10, SV/SVA- och könsfilter samt varför meritvärdedifferens inte är huvudmått.

- [ ] **Step 2: Kör alla automatiska tester före källdatagaten**

Run: `python -m unittest discover -s tests -v`

Expected: alla Python-tester PASS.

Run: `npm run test:e2e`

Expected: alla Playwrighttester PASS.

- [ ] **Step 3: Bygg Pages-paketet utan att kräva elevdata**

Run: `node scripts/build-pages.js`

Expected: exit code 0, `docs/app/progression.js` finns och sidan visar ett tydligt saknat-underlagstillstånd om progressionsfil saknas.

- [ ] **Step 4: Stanna vid källdatagaten och instruera användaren**

Begär först nu att de historiska SCB-filerna läggs i `data/raw/betyg/2022-2023/ak6/`. Kontrollera aldrig in innehållet i Git och visa inga elevrader i verktygsutskrift.

- [ ] **Step 5: När källdatan finns, kör obligatorisk import och Pages-bygg i rätt ordning**

Run: `python src/scb_betyg_import.py --lasar 2025-2026 --publish`

Expected: progressionsdiagnostik anger matchade aggregat och `data/processed/2025-2026/json/betygsprogression_ak6_ak9.json` saknar identifierande fält.

Run: `node scripts/build-pages.js`

Expected: exit code 0 och motsvarande JSON finns under `docs/data/processed/2025-2026/json/`.

- [ ] **Step 6: Kör slutverifiering efter riktig import**

Run: `python -m unittest discover -s tests -v`

Expected: alla Python-tester PASS.

Run: `npm run test:e2e`

Expected: alla Playwrighttester PASS.

Run: `git diff --check`

Expected: ingen output och exit code 0.

- [ ] **Step 7: Granska publiceringsdiffen för personuppgifter**

Kontrollera staged/publicerbara filnamn och JSON-nycklar. Använd inte sökningar som skriver ut råa personnummer eller elevrader. Bekräfta att `data/raw/` och `data/output/` fortfarande är ignorerade.

- [ ] **Step 8: Commit**

```text
git add README.md docs data/processed/2025-2026/json/betygsprogression_ak6_ak9.json
git commit -m "docs: publicera anonymiserad progressionsvy"
```
