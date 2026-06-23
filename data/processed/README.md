# Publiceringsklar bearbetad data

Lägg endast granskad, aggregerad och publiceringsklar JSON här.

Förväntad struktur:

```text
data/processed/<läsår>/json/
  manifest.json
  betygsstatistik_oversikt.json
  betygsstatistik_sv_sva.json
  betygsstatistik_betygsfordelning_amne.json
  np_andel_godkanda.json
  np_betyg_relation.json
  skolenheter_lookup.json
```

Exempel:

```text
data/processed/2025-2026/json/
```

`npm run build:pages` kopierar den här mappen till `docs/data/processed`.

Lägg aldrig rådata, elevrader, personnummer, exporter eller diagnostikfiler här.
