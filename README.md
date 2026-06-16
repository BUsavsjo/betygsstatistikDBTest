# Betygsstatistik Sävsjö

## Syfte

Webbappen hämtar statistik från Skolverkets öppna API:er och visar status för datainhämtningen. Den här versionen är gjord för felsökning först: den visar vilka PxWeb-tabeller som hittas, vilken metadata de har och vilka POST-anrop som faktiskt ger data.

## Vad som är ändrat

- `index.html` är nu huvudfilen. Ingen separat redirect behövs.
- Tidigare tysta fel i `catch(e){}` visas i fliken **Diagnostik**.
- Sidan läser PxWeb-metadata innan den bygger query.
- Skolenhetsregistret testas mot v2 först och v1 som fallback.
- Felmeddelanden skiljer på CORS/nätverk, kategori-fel, metadata-fel och query-fel.

## Kom igång lokalt

```bash
npm install
npm run dev
```

Öppna sedan:

```text
http://localhost:3000
```

Öppna inte filen direkt som `file://` eftersom webbläsaren då kan blockera API-anrop.

## Projektstruktur

```text
betygsstatistik-fixed/
├── index.html
├── package.json
├── README.md
├── TODO.md
├── DATA-SAFETY.md
├── AGENTS.md
└── .github/
    └── workflows/
        └── deploy-pages.yml
```

## Felsökning

1. Starta sidan via `npm run dev`.
2. Öppna fliken **Diagnostik**.
3. Kontrollera först om PxWeb-kategorierna läses.
4. Kontrollera sedan vilka tabeller som får `metadata ok`.
5. Om metadata fungerar men POST misslyckas: kopiera queryn från diagnostiken och jämför med PxWeb:s webbgränssnitt.

## Git-arbetsflöde

- `main` = stabil/publicerad version
- `dev` = samlad utveckling
- `feature/*` = ny funktion eller ändring

Förslag på branch:

```text
feature/busavsjo-felsok-pxweb-betygsstatistik
```

Förslag på commit:

```text
fix: lade till robust pxweb-diagnostik
```

TODO.md
# TODO