# Pedagogisk progressionstolkning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Göra progressionsvyn självinstruerande för rektorer genom synlig vardagsspråklig tolkning av jämförbara ämnesbetyg, genomsnittlig betygsförändring och korrelation.

**Architecture:** Befintlig anonymiserad progressions-JSON behålls oförändrad. `app/progression.js` får små rena tolkningsfunktioner och separata renderingsfunktioner för sammanfattning, samband och meritvärde. `index.html` får semantiska ytor för innehållet och tydligare tabell-/diagrametiketter; Playwright verifierar den användarsynliga betydelsen.

**Tech Stack:** JavaScript utan ramverk, befintlig Chart.js, semantisk HTML/CSS, Playwright och projektets befintliga Python-enhetstester.

## Global Constraints

- Ändra inte Pythonberäkningar, importlogik, anonymisering, sekretessgräns eller JSON-kontrakt.
- Använd ordet **elever** endast för matchade elever och matchningsgrad.
- Använd **jämförbara ämnesbetyg** för höjt, oförändrat, sänkt och genomsnittlig förändring.
- Beskriv aldrig andelen sänkta ämnesbetyg som andelen elever som sänkt sina betyg.
- Korrelation ska förklaras som samband i relativ placering, inte förändring, orsak eller skoleffekt.
- Meritvärde ska visas som ett avskilt kompletterande slutmått.
- Centrala förklaringar ska vara synlig text och inte enbart tooltip eller hovring.
- UI-text ska vara UTF-8 med korrekta svenska tecken.
- Diagnostikfliken och befintliga vyer ska bevaras.
- Rådata och elevuppgifter får inte läggas i Git eller skrivas till publicerad JSON.

---

### Task 1: Dynamisk rektorsförklaring och sambandstolkning

**Files:**
- Modify: `tests/e2e/filter-vyer-tabeller.spec.js:56-79`
- Modify: `index.html:145-155`
- Modify: `app/progression.js:76-171`

**Interfaces:**
- Consumes: befintligt segment med `matchning`, `oversikt`, `merit_ak9` och `amnen`
- Produces: `changeInterpretation(value: number) -> string`
- Produces: `correlationInterpretation(value: number | null) -> { heading: string, body: string }`
- Produces: `renderProgressionInterpretation(segment: object) -> void`
- Produces: `renderProgressionCorrelation(segment: object) -> void`
- Produces DOM ids: `progressionInterpretation`, `progressionCorrelation`

- [ ] **Step 1: Utöka Playwrighttestet med den pedagogiska textens kontrakt**

Lägg följande verifieringar efter att progressionsfliken öppnats i testet `visar anonymiserad progression och filtrerar skola och SVA`:

```javascript
const interpretation = page.locator('#progressionInterpretation');
await expect(interpretation).toContainText('36 av 40 elever');
await expect(interpretation).toContainText('jämförbara ämnesbetyg');
await expect(interpretation).toContainText('50 % höjts');
await expect(interpretation).toContainText('35 % varit oförändrade');
await expect(interpretation).toContainText('15 % sänkts');
await expect(interpretation).toContainText('ungefär 2 av 10 jämförbara ämnesbetyg');
await expect(interpretation).toContainText('0,4 betygssteg högre');
await expect(interpretation).not.toContainText('2 av 10 elever');

const correlation = page.locator('#progressionCorrelation');
await expect(correlation).toContainText('måttligt positivt samband');
await expect(correlation).toContainText('relativt höga betyg');
await expect(correlation).toContainText('visar inte om betygen har höjts eller sänkts');
await expect(correlation).toContainText('vilken effekt skolan haft');
```

- [ ] **Step 2: Kör måltestet och verifiera rätt rött fel**

Run:

```text
npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"
```

Expected: FAIL eftersom `#progressionInterpretation` och `#progressionCorrelation` saknas.

- [ ] **Step 3: Lägg till semantiska ytor i progressionsresultatet**

Placera ytorna inuti `#progressionResults`, före respektive efter `#progressionCards`:

```html
<section id="progressionInterpretation" class="box progression-explanation" aria-live="polite"></section>
<section id="progressionCards" class="grid"></section>
<section id="progressionCorrelation" class="box progression-explanation"></section>
```

Ytorna ska ligga i den redan dolda resultatcontainern så att de automatiskt döljs för saknat och undertryckt underlag.

- [ ] **Step 4: Implementera förändrings- och sambandstolkningen**

Lägg rena hjälpfunktioner före renderingsfunktionerna i `app/progression.js`:

```javascript
function changeInterpretation(value){
  const amount = fmt(Math.abs(value));
  if(value < 0){
    return `Det innebär att samma elevers betyg i samma ämnen i genomsnitt ligger ${amount} betygssteg lägre i årskurs 9.`;
  }
  if(value > 0){
    return `Det innebär att samma elevers betyg i samma ämnen i genomsnitt ligger ${amount} betygssteg högre i årskurs 9.`;
  }
  return 'De jämförbara ämnesbetygen är i genomsnitt oförändrade.';
}

function correlationInterpretation(value){
  if(value === null || value === undefined){
    return {
      heading: 'Sambandet kan inte beräknas för det valda underlaget.',
      body: 'Det behövs tillräckligt många varierande resultat för att beräkna ett samband.'
    };
  }
  const absolute = Math.abs(value);
  const strength = absolute < 0.2 ? 'inget tydligt' : absolute < 0.4 ? 'svagt' : absolute < 0.7 ? 'måttligt' : 'starkt';
  const direction = absolute < 0.2 ? '' : value >= 0 ? ' positivt' : ' negativt';
  const pattern = absolute < 0.2
    ? 'Resultaten i årskurs 6 ger liten vägledning om elevernas relativa resultat i årskurs 9.'
    : value >= 0
      ? 'Elever som hade relativt höga betyg i årskurs 6 tenderar även att ha relativt höga betyg i årskurs 9.'
      : 'Elevernas relativa placering tenderar att vara omvänd mellan årskurs 6 och årskurs 9.';
  return {
    heading: `${fmt(value)} – ${strength}${direction} samband`,
    body: `${pattern} Sambandet visar inte om betygen har höjts eller sänkts, varför resultaten förändrats eller vilken effekt skolan haft.`
  };
}
```

- [ ] **Step 5: Rendera den dynamiska sammanfattningen och sambandet**

Implementera funktionerna:

```javascript
function renderProgressionInterpretation(segment){
  const match = segment.matchning;
  const overview = segment.oversikt;
  const loweredOfTen = Math.round(overview.andel_sankta_betyg / 10);
  $('progressionInterpretation').innerHTML = `
    <h2>Så kan resultatet tolkas</h2>
    <p>${esc(match.antal_matchade)} av ${esc(match.antal_ak9)} elever i årskurs 9 kunde följas tillbaka till årskurs 6. Bland deras jämförbara ämnesbetyg har ${fmt(overview.andel_hojda_betyg, ' %')} höjts, ${fmt(overview.andel_oforandrade_betyg, ' %')} varit oförändrade och ${fmt(overview.andel_sankta_betyg, ' %')} sänkts. Det motsvarar ungefär ${esc(loweredOfTen)} av 10 jämförbara ämnesbetyg som har sänkts.</p>
    <p>Den genomsnittliga betygsförändringen är <strong>${fmt(overview.genomsnittlig_forandring, ' steg')}</strong>. ${esc(changeInterpretation(overview.genomsnittlig_forandring))} Ett steg motsvarar exempelvis E till D eller C till B. Måttet beskriver alla jämförbara ämnesbetyg tillsammans, inte varje enskild elev.</p>`;
}

function renderProgressionCorrelation(segment){
  const interpretation = correlationInterpretation(segment.oversikt.korrelation);
  $('progressionCorrelation').innerHTML = `
    <h2>Samband mellan resultaten</h2>
    <p><strong>${esc(interpretation.heading)}</strong></p>
    <p>${esc(interpretation.body)}</p>`;
}
```

Anropa båda från `renderProgressionView()` efter att `#progressionResults` har visats.

- [ ] **Step 6: Kör måltestet till grönt**

Run:

```text
npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"
```

Expected: 1 test PASS.

- [ ] **Step 7: Commit**

```text
git add app/progression.js index.html tests/e2e/filter-vyer-tabeller.spec.js
git commit -m "feat: forklar progressionens nyckeltal"
```

---

### Task 2: Tydligare kort, betygsskala, ämnestabell och meritvärde

**Files:**
- Modify: `tests/e2e/filter-vyer-tabeller.spec.js:56-79`
- Modify: `index.html:19-22,145-155`
- Modify: `app/progression.js:99-150`

**Interfaces:**
- Consumes: `renderProgressionInterpretation(segment)` och `renderProgressionCorrelation(segment)` från Task 1
- Produces: `renderProgressionSecondary(segment: object) -> void`
- Produces DOM id: `progressionSecondary`
- Changes: `renderProgressionCards(segment)`, `renderProgressionCharts(subjects)` och statiska tabellrubriker

- [ ] **Step 1: Skriv fallande test för rubriker och separat meritvärde**

Lägg till följande verifieringar före det undertryckta filtervalet:

```javascript
await expect(page.locator('#progressionCards')).toContainText('Genomsnittlig betygsförändring');
await expect(page.locator('#progressionCards')).toContainText('Jämförbara ämnesbetyg som höjts');
await expect(page.locator('#progressionCards')).toContainText('Jämförbara ämnesbetyg som är oförändrade');
await expect(page.locator('#progressionCards')).toContainText('Jämförbara ämnesbetyg som sänkts');
await expect(page.locator('#progressionCards')).not.toContainText('Meritvärde åk 9');
await expect(page.locator('#progressionSecondary')).toContainText('Kompletterande slutmått');
await expect(page.locator('#progressionSecondary')).toContainText('Meritvärde i årskurs 9: 231');
await expect(page.locator('#progressionSecondary')).toContainText('jämförs inte med årskurs 6');
await expect(page.locator('#progressionSubjectIntro')).toContainText('giltigt betyg i ämnet både i årskurs 6 och årskurs 9');
await expect(page.locator('#progressionSubjectTable thead')).toContainText('Jämförbara elever');
await expect(page.locator('#progressionSubjectTable thead')).toContainText('Förändring i steg');
await expect(page.locator('#progressionSubjectTable thead')).toContainText('Samband mellan resultaten');
```

- [ ] **Step 2: Kör måltestet och verifiera rätt rött fel**

Run:

```text
npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"
```

Expected: FAIL på de nya rubrikerna eller saknat `#progressionSecondary`.

- [ ] **Step 3: Ändra korten till fem entydiga mått**

Ersätt innehållet i `renderProgressionCards` med:

```javascript
$('progressionCards').innerHTML = [
  progressionCard('Matchade elever', match.antal_matchade, `${fmt(match.matchningsgrad, ' %')} av eleverna i årskurs 9`),
  progressionCard('Genomsnittlig betygsförändring', fmt(overview.genomsnittlig_forandring, ' steg'), 'Samma elev och samma ämne'),
  progressionCard('Jämförbara ämnesbetyg som höjts', fmt(overview.andel_hojda_betyg, ' %'), 'Andel av alla jämförbara ämnesbetyg'),
  progressionCard('Jämförbara ämnesbetyg som är oförändrade', fmt(overview.andel_oforandrade_betyg, ' %'), 'Andel av alla jämförbara ämnesbetyg'),
  progressionCard('Jämförbara ämnesbetyg som sänkts', fmt(overview.andel_sankta_betyg, ' %'), 'Andel av alla jämförbara ämnesbetyg')
].join('');
```

- [ ] **Step 4: Lägg till ämnesintroduktion, tabell-id och separat meritdel**

Ändra den statiska HTML-strukturen till:

```html
<div class="box">
  <h2>Resultat per ämne</h2>
  <p id="progressionSubjectIntro" class="small">Varje rad jämför elever som har ett giltigt betyg i ämnet både i årskurs 6 och årskurs 9.</p>
  <div class="tw"><table id="progressionSubjectTable" class="progression-table"><thead><tr><th>Ämne</th><th>Jämförbara elever</th><th>Åk 6</th><th>Åk 9</th><th>Förändring i steg</th><th>Höjt</th><th>Oförändrat</th><th>Sänkt</th><th>Samband mellan resultaten</th></tr></thead><tbody id="progressionRows"></tbody></table></div>
</div>
<section id="progressionSecondary" class="box progression-explanation"></section>
```

Implementera:

```javascript
function renderProgressionSecondary(segment){
  $('progressionSecondary').innerHTML = `
    <h2>Kompletterande slutmått</h2>
    <p><strong>Meritvärde i årskurs 9: ${fmt(segment.merit_ak9?.genomsnitt_merit_17)}</strong></p>
    <p class="small">Meritvärdet visar slutresultatet i årskurs 9. Det jämförs inte med årskurs 6 eftersom ämnesuppsättningen och beräkningsunderlaget kan skilja sig.</p>`;
}
```

Anropa funktionen från `renderProgressionView()`.

- [ ] **Step 5: Visa F–A på diagrammets y-axel och förbättra tabellens läsbarhet**

Ändra betygsdiagrammets options till:

```javascript
const gradeLabels = ['F', 'E', 'D', 'C', 'B', 'A'];
makeChart('progressionGradeChart', 'bar', {
  labels: visible.map(row => row.amnesnamn),
  datasets: [
    {label:'Åk 6', data:visible.map(row => row.genomsnitt_ak6), backgroundColor:'#8aa8b8'},
    {label:'Åk 9', data:visible.map(row => row.genomsnitt_ak9), backgroundColor:'#1f5f7a'}
  ]
}, {
  scales:{
    y:{
      beginAtZero:true,
      max:5,
      ticks:{stepSize:1,callback:value => gradeLabels[value] || ''}
    }
  }
});
```

Lägg till fokuserad CSS i `index.html`:

```css
.progression-explanation p{max-width:78ch}.progression-table th{white-space:normal}.progression-table .numeric{white-space:nowrap}.progression-table th:nth-child(2),.progression-table th:nth-child(5),.progression-table th:nth-child(9){min-width:110px}
```

- [ ] **Step 6: Kör progressionstester och hela UI-sviten**

Run:

```text
npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "progression"
npm run test:e2e
```

Expected: båda körningarna PASS, totalt 5 Playwrighttester i hela sviten.

- [ ] **Step 7: Commit**

```text
git add app/progression.js index.html tests/e2e/filter-vyer-tabeller.spec.js
git commit -m "feat: gor progressionen sjalvinstruerande"
```

---

### Task 3: Gemensam ämnessortering och kort ämnestolkning

**Files:**
- Modify: `tests/e2e/filter-vyer-tabeller.spec.js:56-90`
- Modify: `index.html:145-155`
- Modify: `app/progression.js:115-171`
- Modify: `app/init.js`

**Interfaces:**
- Produces: `sortedProgressionSubjects(subjects: object[], sortMode: string) -> object[]`
- Produces: `subjectInterpretation(subject: object) -> string`
- Produces DOM id: `progressionSubjectSort`
- Changes: båda ämnesdiagrammen och ämnestabellen använder samma sorterade kopia

- [ ] **Step 1: Skriv fallande test för ämnestolkning och gemensam sortering**

Utöka progressionstestet med verifieringar att Matematik förklaras som `0,6 steg högre`, att sambandet beskrivs som `måttligt` och att texten säger att måttet inte visar varför. Byt sedan sortering till `correlation` och verifiera att Engelska ligger först i tabellen och båda diagrammen. Byt till `increase` och verifiera att Matematik ligger först.

- [ ] **Step 2: Kör måltestet och verifiera rätt rött fel**

Run:

```text
npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"
```

Expected: FAIL eftersom sorteringskontrollen och kolumnen `Kort tolkning` saknas.

- [ ] **Step 3: Lägg till sorteringskontroll och tabellkolumn**

Lägg ett selectfält med id `progressionSubjectSort` ovanför diagrammen och alternativen:

- `default`: Ämnesordning
- `increase`: Störst höjning
- `decrease`: Störst sänkning
- `correlation`: Starkast samband

Lägg till kolumnen `Kort tolkning` sist i ämnestabellen.

- [ ] **Step 4: Implementera rena sorterings- och tolkningsfunktioner**

`sortedProgressionSubjects` ska alltid returnera en kopia. `increase` sorterar fallande på `genomsnittlig_forandring`, `decrease` stigande och `correlation` fallande på absolut korrelation med saknade värden sist. Standardläget behåller källordningen.

`subjectInterpretation` ska först beskriva om ämnets betyg i genomsnitt ligger högre, lägre eller oförändrat och därefter tolka sambandet som relativ placering. Texten ska avslutas med att måttet inte visar varför nivån har förändrats.

- [ ] **Step 5: Koppla samma sorterade lista till diagram och tabell**

Lägg `subjectSort: 'default'` i progressionens tillstånd, bind ändringshändelsen i `app/init.js` och rendera om vyn. Skicka samma resultat från `sortedProgressionSubjects` till både `renderProgressionCharts` och `renderProgressionTable`.

- [ ] **Step 6: Kör progressionstest och hela UI-sviten**

Run:

```text
npx playwright test tests/e2e/filter-vyer-tabeller.spec.js --grep "anonymiserad progression"
npm run test:e2e
```

Expected: måltestet och hela Playwrightsviten PASS.

- [ ] **Step 7: Commit**

```text
git add app/progression.js app/init.js index.html tests/e2e/filter-vyer-tabeller.spec.js
git commit -m "feat: lagg till amnesanalys i progression"
```

---

### Task 4: Pages-paket, visuell kontroll och slutverifiering

**Files:**
- Modify generated: `docs/app/progression.js`
- Modify generated: `docs/index.html`
- Verify unchanged data contract: `data/processed/2025-2026/json/betygsprogression_ak6_ak9.json`
- Verify copied data: `docs/data/processed/2025-2026/json/betygsprogression_ak6_ak9.json`

**Interfaces:**
- Consumes: färdig käll-UI från Task 1, Task 2 och Task 3
- Produces: statiskt GitHub Pages-paket med samma pedagogiska progressionsvy

- [ ] **Step 1: Bygg Pages-paketet**

Run:

```text
node scripts/build-pages.js
```

Expected: exit code 0 och meddelandet `GitHub Pages package created in docs/.`.

- [ ] **Step 2: Verifiera att käll- och Pages-filerna motsvarar varandra**

Run:

```powershell
Compare-Object (Get-Content app/progression.js) (Get-Content docs/app/progression.js)
Select-String -Path docs/index.html -Pattern "Så kan resultatet tolkas|progressionInterpretation|progressionCorrelation|progressionSecondary"
```

Expected: `Compare-Object` ger ingen output och `Select-String` hittar de nya DOM-elementen.

- [ ] **Step 3: Kontrollera den verkliga lokala vyn visuellt**

Starta eller återanvänd `npm run dev`, öppna `http://localhost:3000`, välj **Progression åk 6–9** och verifiera:

1. sammanfattningen säger **jämförbara ämnesbetyg**, inte andel elever
2. `−0,2` förklaras som genomsnittligt lägre för samma elev och ämne
3. sambandet `0,8` förklaras som starkt positivt men inte förändring, orsak eller skoleffekt
4. F–A visas på betygsdiagrammets y-axel
5. meritvärdet ligger i en separat ruta
6. undertryckt Rörvik/SVA döljer alla resultatdelar

- [ ] **Step 4: Kör full automatisk verifiering**

Run:

```text
python -m unittest discover -s tests -v
npm run test:e2e
git diff --check
```

Expected: 36 Pythontester och 5 Playwrighttester PASS samt ingen output från `git diff --check`.

- [ ] **Step 5: Kontrollera att publicerad data fortfarande saknar identifierande nycklar**

Run:

```powershell
$paths = @("data/processed/2025-2026/json/betygsprogression_ak6_ak9.json", "docs/data/processed/2025-2026/json/betygsprogression_ak6_ak9.json")
foreach($path in $paths){
  $content = Get-Content -Raw -LiteralPath $path -Encoding UTF8
  foreach($key in @('PersonNr','Fornamn','Efternamn','Klass','_source_file','_source_row')){
    if($content.Contains(('"' + $key + '"'))){ throw "Otillåten publik nyckel i $path" }
  }
}
```

Expected: exit code 0 utan felutskrift.

- [ ] **Step 6: Commit Pages-paketet**

```text
git add docs/app/progression.js docs/index.html
git commit -m "docs: paketera pedagogisk progressionsvy"
```
