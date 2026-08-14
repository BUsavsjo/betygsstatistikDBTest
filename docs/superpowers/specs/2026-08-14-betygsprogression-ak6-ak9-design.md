# Betygsprogression åk 6–9 – design

## Syfte

Funktionen ska visa hur betygen utvecklas för elever som kan följas från årskurs 6 till slutbetyget i årskurs 9. Den ska ge Hofgårdsskolan, Rörviks skola och huvudmannen ett gemensamt analysunderlag utan att publicera elevuppgifter.

Analysen visar förändring och statistiska samband. Den ska inte beskriva samband som orsaker eller tillskriva en skola hela elevens utveckling.

## Omfattning

Första versionen omfattar:

- progression mellan samma elevs betyg i åk 6 och åk 9
- huvudmannen, Hofgårdsskolan och Rörviks skola
- filter för elevkull, skola, kön och kursplanen SV/SVA
- förändring i jämförbara ämnesbetyg
- rangkorrelation mellan åk 6 och åk 9
- meritvärde i åk 9 som kompletterande slutmått
- publicering av anonymiserade aggregat på GitHub Pages

Första versionen omfattar inte analys efter avlämnande åk 6-skola, individvyer, orsaksanalys eller publicering av elevrader.

## Källdata och mappstruktur

En elevkull definieras av slutläsåret i åk 9. Källäsåret för åk 6 räknas fram genom att flytta båda årtalen tre år bakåt.

Exempel för slutläsåret 2025–2026:

```text
data/raw/betyg/2022-2023/ak6/*.txt
data/raw/betyg/2025-2026/ak9/*.txt
```

Filerna ska följa projektets befintliga SCB-format. Befintliga specifikationer `AK6_COLUMNS` och `AK9_COLUMNS` ska användas vid inläsning och validering. `data/raw/` förblir ignorerad av Git.

Den vanliga importen ska vara ingången:

```text
python src/scb_betyg_import.py --lasar 2025-2026 --publish
```

Progressionsberäkningen ska ligga i en separat modul men anropas av importflödet när båda källåren finns. Om historisk åk 6-data saknas ska ordinarie betygsimport fortsätta och progressionsdiagnostiken ange att underlaget saknas.

## Matchning och urval

Elever matchas lokalt på ett normaliserat `PersonNr`. Skolenhetskod får inte ingå i matchningsnyckeln eftersom eleven kan byta skola mellan åk 6 och åk 9.

Matchningen ska:

1. normalisera personnummer till enbart siffror, acceptera exakt 10 eller 12 siffror och omvandla 12 siffror till de sista 10
2. avvisa tomma nycklar och alla andra längder
3. kontrollera att varje nyckel är unik inom respektive årskurs
4. slå samman identiska dubbletter
5. utesluta motstridiga dubbletter och redovisa dem som antal i lokal diagnostik
6. endast analysera elever som finns i båda underlagen

Skolgrupperingen bestäms av skolenheten i åk 9:

- Hofgårdsskolan: `59983229`
- Rörviks skola: `74170440`
- Sävsjö kommun: unionen av de två skolenheterna ovan

Matchningsgrad definieras som antal matchade elever dividerat med antal giltiga elever i åk 9 i den valda gruppen. Antal elever i historisk åk 6-data som inte återfinns i åk 9 redovisas endast som diagnostik; orsaken kan inte avgöras av underlaget.

## Segmentering

Varje publicerat aggregat ska kunna filtreras på:

- skola: huvudmannen, Hofgårdsskolan eller Rörviks skola
- kön: Alla, Flickor eller Pojkar
- elevgrupp: Alla, SV eller SVA

Kön härleds med projektets befintliga logik från personnumret och publiceras endast som gruppdimension. SV/SVA bestäms av elevens betygsrad i åk 9, eftersom analysgruppen ska motsvara kursplanen vid slutbetyget.

En elev med giltigt SVA-betyg men inget giltigt SV-betyg ingår i SVA. En elev med giltigt SV-betyg men inget giltigt SVA-betyg ingår i SV. Rader med båda eller inget giltigt betyg ingår i Alla men inte i ett specifikt SV/SVA-filter och redovisas som datakvalitet i lokal diagnostik.

Filterkombinationer ska beräknas vid importen. Webbläsaren ska aldrig få elevdata för att skapa egna grupper.

## Jämförbara betyg

Analysen använder betygsordningen:

```text
F = 0, E = 1, D = 2, C = 3, B = 4, A = 5
```

Ett betyg är höjt, oförändrat eller sänkt genom att jämföra rangvärdet i samma ämne. Endast elev–ämnespar med giltigt betyg i båda årskurserna ingår.

Direkt jämförbara ämnen i första versionen är:

- Bild
- Engelska
- Hem- och konsumentkunskap
- Idrott och hälsa
- Matematik
- Musik
- Biologi, fysik och kemi när separata betyg finns i båda underlagen
- Geografi, historia, religionskunskap och samhällskunskap när separata betyg finns i båda underlagen
- Slöjd
- Svenska/SVA som ett gemensamt ämnesområde
- Teckenspråk
- Teknik

NO- och SO-blockbetyg ska inte omvandlas till separata ämnesbetyg. Moderna språk, modersmål och övrigt ämne ingår inte i det första jämförbara indexet eftersom registrering och ämnesroll kan skilja sig mellan årskurserna.

Det övergripande progressionsmåttet beräknas över alla giltiga, jämförbara elev–ämnespar i segmentet. UI-texten ska därför beskriva andel höjda, oförändrade och sänkta **betyg**, inte andel elever.

## Mätvärden

För varje tillåtet segment beräknas:

- antal elever i åk 9
- antal matchade elever
- matchningsgrad
- antal jämförbara elev–ämnespar
- genomsnittlig förändring i betygssteg
- andel höjda, oförändrade och sänkta betyg
- andel F till A–E
- andel A–E till F
- genomsnittligt betyg i åk 6 och åk 9
- Spearmans rangkorrelation mellan elevernas genomsnittliga betygsrang i åk 6 och åk 9

Det övergripande sambandet beräknas för elever som har minst fem jämförbara ämnen. Samma mått, med relevant antal jämförbara elever, beräknas per ämne. Korrelation publiceras bara när minst 10 elevpar finns och båda variablerna varierar.

## Meritvärde

Projektets nuvarande meritfunktion omvandlar A–F till 20, 17,5, 15, 12,5, 10 och 0 poäng. `meritvarde_16` summerar de 16 högsta giltiga betygen, använder det högsta av SV/SVA och hoppar över specialkoder och saknade betyg. `meritvarde_17` lägger till det högsta godkända betyget i moderna språk.

Beräkningen används i dag för både åk 6 och åk 9, men resultaten är inte fullt jämförbara. Ämnesuppsättningen, blockbetyg och antalet registrerade betyg kan skilja sig. En differens kan därför spegla både kunskapsutveckling och förändrad betygstäckning.

Första versionen ska därför:

- inte kalla skillnaden mellan meritvärde i åk 6 och åk 9 för progression
- visa genomsnittligt `meritvarde_16` och `meritvarde_17` i åk 9 som kompletterande slutmått
- visa rangkorrelation mellan elevens genomsnittliga jämförbara betygsrang i åk 6 och `meritvarde_16` i åk 9
- förklara att sambandet inte visar orsak

## Sekretess och publicering

Minsta publicerbara grupp är 10 matchade elever. Tröskeln ska tillämpas separat efter varje kombination av skola, kön och SV/SVA samt per ämnesrad.

En undertryckt grupp får finnas i publicerad JSON med `undertryckt: true`, men exakt antal och samtliga mätvärden ska vara `null`. Det får inte gå att räkna fram ett undertryckt värde genom totaler och delgrupper. Om en publicerad total tillsammans med en delgrupp skulle avslöja den andra delgruppen ska även den berörda kompletterande cellen undertryckas.

Följande får aldrig skrivas till `data/processed/` eller `docs/`:

- personnummer eller hash av personnummer
- namn
- klass
- elevrader
- källfilens radnummer
- listor över matchade eller omatchade elever

Publiceringsfil:

```text
data/output/<slutläsår>/json/betygsprogression_ak6_ak9.json
data/processed/<slutläsår>/json/betygsprogression_ak6_ak9.json
docs/data/processed/<slutläsår>/json/betygsprogression_ak6_ak9.json
```

Filen ska läggas till i projektets uttryckliga publiceringslista. Pages-bygget ska fortsätta kopiera enbart godkända aggregat.

## JSON-kontrakt

Rotobjektet ska innehålla:

```json
{
  "schema_version": 1,
  "source": "local_scb_progression",
  "ak6_lasar": "2022-2023",
  "ak9_lasar": "2025-2026",
  "sekretessgrans": 10,
  "segment": []
}
```

Varje segment identifieras av nivå, skolenhet, kön och elevgrupp. Ett publicerbart segment innehåller `matchning`, `oversikt`, `merit_ak9` och `amnen`. Ett undertryckt segment innehåller endast dimensionerna, `undertryckt: true` och nullvärden. Ämnesrader kan undertryckas oberoende av segmentets totalsammanfattning.

## Sida och interaktion

Webbappen får en ny flik med rubriken **Progression åk 6–9**. Fliken laddar den nya JSON-filen via samma lokala datakälleordning som befintliga vyer.

Fliken har egna filter för:

- elevkull
- huvudman/Hofgårdsskolan/Rörviks skola
- Alla/Flickor/Pojkar
- Alla/SV/SVA

Vyn innehåller:

1. sammanfattningskort för matchade elever, matchningsgrad, genomsnittlig betygsförändring och fördelningen höjt/oförändrat/sänkt
2. ett staplat ämnesdiagram för höjt/oförändrat/sänkt
3. en jämförelse mellan genomsnittligt betyg i åk 6 och åk 9 per ämne
4. ett sambandsavsnitt med rangkorrelation per ämne och samband mellan åk 6-index och meritvärde i åk 9
5. en tabell med antal jämförbara elever, genomsnitt, förändring, andelar och korrelation per ämne
6. en metodruta som beskriver urval, sekretessgräns, meritvärdets begränsning och att korrelation inte visar orsak

Undertryckta urval visar texten: **Resultatet visas inte eftersom gruppen är för liten.**

## Felhantering och diagnostik

Lokal diagnostik skrivs till:

```text
data/output/<slutläsår>/diagnostik/progression_ak6_ak9.json
```

Den ska innehålla antal lästa rader, giltiga matchningsnycklar, matchade elever, omatchade elever, identiska dubbletter, motstridiga dubbletter, SV/SVA-oklarheter och jämförbara betyg per ämne. Diagnostiken får inte innehålla personnummer, namn eller andra identifierande värden.

Saknad historisk fil eller fel kolumnantal ska ge tydlig diagnostik. Ordinarie import ska fortsätta. Progressionsvyn ska visa att underlag saknas i stället för att falla tillbaka till demo- eller PxWeb-data.

## Testning

Enhetstester ska verifiera:

- härledning av källläsår
- normalisering och matchning utan skolenhetskod
- hantering av identiska och motstridiga dubbletter
- skolgruppering efter åk 9
- köns- och SV/SVA-segmentering
- betygsrang, ämnespar och övergångar mellan F och godkänt
- rangkorrelation och fall utan variation
- meritvärdets sekundära mått
- sekretessgräns och kompletterande undertryckning
- att publicerad JSON saknar identifierande fält
- att endast den whitelistade progressionsfilen publiceras

Gränssnittstester ska verifiera filterkombinationer, diagram och tabell, undertryckta grupper, saknat underlag samt korrekt svensk text.

Efter varje ändring i import eller beräkning ska projektets fastställda publiceringsordning följas:

```text
python src/scb_betyg_import.py --lasar <slutläsår> --publish
node scripts/build-pages.js
```

`data/processed/`, `docs/` och källkoden ska versionshanteras tillsammans. Rådata, lokal diagnostik och elevrader får inte läggas i Git.

## Godkända designbeslut

- separat progressionsmodul som anropas av det befintliga importflödet
- gruppering efter elevens skola i åk 9
- huvudmannanivå samt Hofgårdsskolan och Rörviks skola
- publik aggregerad vy på GitHub Pages
- sekretessgräns 10
- filter för kön och SV/SVA
- meritvärde som sekundärt slutmått, inte primärt progressionsmått
