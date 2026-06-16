
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

## Säkerhet

- Lägg aldrig personuppgifter, elevdata, `.env`, rådata eller exporter i Git.
- Använd endast offentlig eller anonymiserad testdata.

## Git

- `main` är stabil/publicerad version.
- `dev` är arbetsgren.
- `feature/*` används för nya funktioner.