# Agentinstruktioner

## Arbetssätt

- Gör små, testbara ändringar.
- Bevara diagnostikfliken tills API-strukturen är säkrad.
- Läs tabellmetadata innan nya PxWeb-querys byggs.
- Uppdatera README när körsätt eller API-struktur ändras.

## Kodstil

- Använd tydliga namn.
- Kommentera varför något görs, särskilt kring API-fallbacks.
- Undvik onödiga beroenden.

## Tecken och språk

- Använd UTF-8 i textfiler som innehåller svenska tecken.
- UI-text ska visas med korrekta svenska tecken som `å`, `ä` och `ö`.
- Om en fil redan innehåller felkodade svenska tecken ska de rättas när filen ändå ändras.

## Säkerhet

- Lägg aldrig personuppgifter, elevdata, `.env`, rådata eller exporter i Git.
- Använd endast offentlig eller anonymiserad testdata.

## Git

- `main` är stabil/publicerad version.
- `dev` är arbetsgren.
- `feature/*` används för nya funktioner.

## Publicering på GitHub Pages

Efter varje ändring i importlogiken eller beräkningar ska dessa tre steg köras i ordning:

1. Generera nya JSON-filer och kopiera till `data/processed/`:
   ```
   python src/scb_betyg_import.py --lasar <läsår> --publish
   ```
   `--publish` krävs alltid. Utan den uppdateras bara `data/output/` men
   inte `data/processed/`, och appen prioriterar `data/processed/` – både
   på localhost:3000 och på GitHub Pages. Gamla värden visas annars.

2. Bygg Pages-paketet:
   ```
   node scripts/build-pages.js
   ```
   Kopierar `data/processed/` och `data/output/*/json/` till `docs/`.
   Eftersom appen läser `processed/` före `output/` måste steg 1 köras
   med `--publish` innan detta steg.

3. Committa och pusha `docs/` och `data/processed/` tillsammans med
   källkoden. GitHub Pages publicerar från `docs/` på `main`-grenen.
