# Betygsstatistik Sävsjö

## Syfte

Webbappen hämtar öppna PxWeb-data från Skolverket för Sävsjö kommun och visar vilka efterfrågade betygsmått som faktiskt finns tillgängliga i API:t.

Appen är byggd för två saker:

- visa statistik när ett mått finns i Skolverkets öppna PxWeb API
- visa tydlig diagnostik när ett mått saknas, har annan tabellstruktur eller blockeras av API-rate limit

## Aktuella vyer

- Pojkar/flickor, när tabellen har könsdimension.
- Meritvärde, om måttet finns i upptäckta tabeller.
- Meritvärde för elever som läser SVA, om Skolverket publicerar ett sådant mått öppet.
- Genomsnittlig betygspoäng per ämne.
- NP GAP-flik med öppna NP-/betygsnära mått.
- Uppnått kunskapskrav i alla ämnen.
- Yrkesbehörighet till gymnasiet.
- Datatäckning för betygsfördelning per skolenhet och kommun.
- Diagnostik med tabellmetadata, matchade mått, POST-querys och API-fel.

## API-struktur

Skolverkets PxWeb-listningar returnerar objekt på formen:

```json
{ "value": [ ... ], "Count": 2 }
```

Tidigare kod antog att listningen var en ren array. Nu används `response.value` när den finns.

Grundskolans öppna PxWeb-noder som appen går igenom är:

```text
/Kommunala_jamforelsetal/Grundskola/
/Underlag_for_analys_inom_det_nationella_kvalitetssystemet/Grundskola/
```

Metadata läses innan POST-querys byggs. Appen väntar kort mellan metadata- och POST-anrop för att minska risken för `429 Too Many Requests`.

Vissa tabeller, till exempel `Underlag_for_analys_inom_det_nationella_kvalitetssystemet/Grundskola/Grundskola.px`, redovisar dimensionen `huvudman/skolenhet` utan värdelista i metadata. För sådana tabeller använder appen kända nivåvärden direkt: Sävsjö huvudman och riket.

För Sävsjö huvudman används huvudmannakoden `2120000563`.

## NP-data

Den öppna PxWeb-strukturen som hittades innehåller inte komplett NP GAP för SV, engelska och matematik i årskurs 6 och 9, och ingen färdig relation mellan betyg och nationella prov.

Appen visar därför de öppna närliggande måtten som finns i `Underlag_for_analys_inom_det_nationella_kvalitetssystemet/Grundskola/Grundskola.px`:

- NP kravnivå svenska/svenska som andraspråk årskurs 3.
- NP kravnivå matematik årskurs 3.
- Lägst betyget E i svenska/svenska som andraspråk årskurs 6 och 9.
- Lägst betyget E i matematik årskurs 6 och 9.
- Lägst betyget E i samtliga ämnen årskurs 6 och 9.
- Behörighet till nationellt program i gymnasieskolan.

## Kom igång lokalt

```bash
npm install
npm run dev
```

Öppna sedan:

```text
http://localhost:3000
```

`npm run dev` startar `server.js`, som både serverar webbappen och proxyar PxWeb-anrop via `/api/pxweb`. Proxyn behövs eftersom vissa Skolverket-tabeller svarar utan webbläsarvänlig CORS-hantering trots att samma POST-query fungerar från servermiljö.

Öppna inte filen direkt som `file://`, eftersom webbläsaren då kan blockera API-anrop och proxyn inte används.

## Publicera på GitHub Pages

GitHub Pages kan bara servera statiska filer. Den publicerade versionen försöker därför läsa aggregerad JSON i följande ordning:

1. `data/processed/<läsår>/json`
2. `data/output/<läsår>/json`
3. `data/demo/<läsår>/json`

Den försöker inte använda den lokala PxWeb-proxyn i `server.js`.

Lägg granskad bearbetad data som får publiceras här:

```text
data/processed/2025-2026/json/
```

Om `data/processed/<läsår>/json` saknas kan `npm run build:pages` även paketera aggregerad JSON direkt från `data/output/<läsår>/json`. Då kopieras bara JSON-filerna under respektive `json/`-mapp, inte diagnostik, CSV eller andra arbetsfiler.

Bygg publiceringsmappen:

```bash
npm run build:pages
```

Det skapar `docs/` med:

```text
docs/index.html
docs/data/processed/
docs/data/output/
docs/data/demo/
docs/.nojekyll
```

Förhandsgranska Pages-versionen lokalt:

```bash
npm run preview:pages
```

Ställ sedan in GitHub Pages på:

```text
Branch: main
Folder: /docs
```

Publicera aldrig `data/raw`, elevdata, exporter, `.env` eller dokumentation med personuppgifter. `npm run build:pages` kopierar bara `index.html`, `app/`, `data/processed`, `data/output/*/json` och `data/demo`.

## Lokal SCB-import för årets betygsdata

Importkoden är uppdelad i mindre moduler under `src/betyg/`:

- `constants.py` för specifikationer och fasta värden
- `io.py` för filinläsning, skrivning och publiceringskopiering
- `metrics.py` för betygsberäkningar och aggregering
- `np_data.py` för NP-logik och betyg/NP-relation
- `skolenheter.py` för namnuppslag av skolenheter
- `pipeline.py` för den samlade importkörningen

CLI-ingången är fortsatt:

```text
src/scb_betyg_import.py
```

Äldre `busavsjo_*`-skript som använder `src/config_paths.py` utgår nu från läsåret `2025-2026` om inget annat anges. För att köra dem mot ett annat läsår kan du sätta miljövariabeln `BETYGSSTATISTIK_LASAR`.

Frontendlogiken är nu uppdelad i `app/`:

- `core.js` för delade konstanter, state och små hjälpfunktioner
- `local-data.js` för lokal JSON-laddning, filter och lokal rendering
- `pxweb.js` för PxWeb-upptäckt, metadata och querybygge
- `render.js` för API-fallbackrendering och diagramhjälpare
- `init.js` för uppstart och event binding

`npm run build:pages` kopierar `index.html` och `app/`, och sätter `STATIC_PAGES_BUILD = true` i publicerad `docs/app/core.js`.

Lokal SCB-import kan också skapa kontrollfilen:

```text
data/output/<läsår>/json/betygsstatistik_kontroll_betyg.json
```

Den används i fliken **Kontroll** för att visa antal giltiga betyg, tomma värden, specialkoder och ogiltiga koder per ämne.

Lägg SCB:s semikolonseparerade betygsfiler i separata mappar per läsår och årskurs:

```text
data/raw/betyg/2025-2026/ak6/*.txt
data/raw/betyg/2025-2026/ak9/*.txt
```

Om nationella prov ska läsas in separat läggs råfilerna i motsvarande NP-mappar:

```text
data/raw/np/2025-2026/ak3/
data/raw/np/2025-2026/ak6/
data/raw/np/2025-2026/ak9/
```

Kör importen:

```bash
npm run import:scb -- --lasar 2025-2026
```

För att även förbereda publiceringsbar bearbetad JSON till GitHub Pages:

```bash
npm run import:scb:publish -- --lasar 2025-2026
```

Importen läser alla `.txt` i respektive mapp, validerar antal kolumner mot SCB:s betygsspecifikation och skapar output under:

```text
data/output/2025-2026/
data/output/2025-2026/json/
data/output/2025-2026/diagnostik/
```

Vid import skapas även en Excel-fil för manuell fältkontroll:

```text
data/output/2025-2026/diagnostik/datafilsbeskrivning_jamforelse.xlsx
```

Den jämför fälten i SCB:s datafilsbeskrivningar under `data/dokumentation/` med importkodens kolumnlistor och faktisk TXT-inläsning. Bladen visar position, variabelnamn, fältinnehåll, tillåtna tecken, maxlängd, antal ifyllda/tomma värden, faktisk maxlängd, exempelvärden och status. Exempelvärden för personnummer, förnamn och efternamn maskas, men filen ligger ändå under `data/output` eftersom den bygger på rådata och inte ska publiceras.

Med `--publish` kopieras endast whitelistade aggregerade JSON-filer vidare till:

```text
data/processed/2025-2026/json/
```

Webbappen försöker först läsa publiceringsklar JSON från `data/processed/<läsår>/json`, därefter aggregerad JSON från `data/output/<läsår>/json`. Om lokal/publicerad data saknas används demodata eller befintligt PxWeb-flöde som fallback beroende på körläge.

Rådata, rensade elevfiler och genererad output ligger i `.gitignore`. Publicera inte personnummer, namn, rådata eller exporter med elevrader.

Lokal SCB-import kan visa bland annat meritvärde, betygsfördelning, andel A-E/F, gymnasiebehörighet för åk 9, uppnått alla ämnen och jämförelse mellan elever som läser svenska respektive svenska som andraspråk.

För årskurs 6 ingår nu även `Modmalbe` samt `M1_betyg` och `M2_betyg` i ämnesvyerna. De visas i JSON och UI som `Modersmål`, `Moderna språk, elevens val` respektive `Moderna språk, skolans val`.

För årskurs 9 ingår nu även `M1_betyg`, `M2_betyg` och `ML_betyg` i ämnesvyerna. De visas som `Moderna språk, elevens val`, `Moderna språk, skolans val` och `Moderna språk som språkval`. Kontroll mot `datafilsbeskrivning_betyg_ak9_2026.xlsx` och råfilerna visar att åk9-formatet inte innehåller `Modmalbe`.

## Tester

Kör de inledande regressionstesterna för importlogiken med:

```bash
python -m unittest discover -s tests -v
```

## Felsökning

1. Starta sidan via `npm run dev`.
2. Öppna fliken **Diagnostik**.
3. Kontrollera att tabellmetadata läses.
4. Kontrollera fliken **Datatäckning** för vilka önskade vyer som API:t faktiskt stödjer.
5. Om Skolverket svarar `429`, vänta en stund och klicka **Ladda om**.

## Git-arbetsflöde

- `main` = stabil/publicerad version
- `dev` = samlad utveckling
- `feature/*` = ny funktion eller ändring

## Lokal NP-import

NP-importen använder datafilsbeskrivningarna för åk 3, 6 och 9. Den skapar aggregerad JSON för andel godkända nationella prov samt relation mellan betyg och nationella prov per kommun och skolenhet när både betygsfil och NP-fil finns.

För åk 3 finns stöd både för den dokumenterade 35-kolumnsstrukturen och en kompakt 31-kolumnsvariant där `MA_G1_*` och `MA_G2_*` saknas. Den kompakta varianten normaliseras internt till samma fältnamn innan aggregering, så KPI-vyn för åk 3 kan byggas från lokal NP-data utan manuell filredigering.

När betygsmatchning saknas för åk 3 härleds kön direkt från personnumret i NP-filen, så `np_andel_godkanda.json` kan visa fördelning mellan flickor och pojkar utan att publicera personnummer.

```text
data/output/2025-2026/json/np_andel_godkanda.json
data/output/2025-2026/json/np_betyg_relation.json
data/output/2025-2026/json/skolenheter_lookup.json
```

Relationen betyg/NP beräknas bara för åk 6 och 9, eftersom åk 3 saknar terminsbetyg i betygsflödet. Personnummer används bara internt för matchning och skrivs inte till publicerad JSON.

NP-diagnostiken i `data/output/<läsår>/diagnostik/import_np_ak*.json` räknar även dokumenterade specialkoder per kolumn, till exempel `77`, `88` och `99`, så bortfall och ersättningsprov kan granskas utan att publicera elevrader.

Skolenhetsnamn hämtas från Skolverkets skolenhetsregister API v2 när importen kan nå API:t. För Sävsjös kända grundskolor finns också en lokal fallbacktabell så att sidan kan visa skolnamn även om API:t inte svarar. Om en kod fortfarande inte kan matchas visas skolenhetskoden som fallback.

