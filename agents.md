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

Efter varje ändring i importlogiken eller beräkningar ska dessa två steg köras i ordning:

1. Generera nya JSON-filer:
   ```
   python src/scb_betyg_import.py --lasar <läsår>
   ```
   Utdata hamnar i `data/output/<läsår>/json/`.

2. Bygg Pages-paketet:
   ```
   node scripts/build-pages.js
   ```
   Utdata hamnar i `docs/` och inkluderar JSON-filerna under `docs/data/output/<läsår>/json/`.

Committa och pusha därefter både källkoden och ändringarna i `docs/`. GitHub Pages publicerar från `docs/` på `main`-grenen.
