# PxWeb API – Praktisk guide för Skolverkets statistikdatabas

Hur du hittar rätt tabell, förstår svaret och bygger nya vyer.

---

## Hitta tabellnamnet du behöver

### Steg 1 – Öppna Web UI

https://statistikdatabasen.skolverket.se/PxWeb/pxweb/sv/Skolverkets_statistikdatabas/

Navigera: **Kommunala jämförelsetal → Grundskola → Betyg**  
(eller Nationella prov, Behörighet, etc.)

### Steg 2 – Välj tabell och variabler

Välj en tabell, välj variabler (t.ex. Sävsjö, alla kön, senaste åren).

### Steg 3 – Hämta API-anropet

Klicka **Fortsätt** → välj format **JSON** → klicka **Visa tabell** →  
klicka **API-anrop** i verktygsraden.

Du får exakt det `POST`-anrop du behöver, inklusive tabellsökväg och query-body.

---

## Tabellstruktur – var finns vad?

```
Kommunala_jamforelsetal/
└── Grundskola/
    ├── Betyg/
    │   ├── [meritvärde-tabell].px        ← Meritvärde åk 9, per kön
    │   ├── [ämnesbetyg-tabell].px        ← Snittbetyg per ämne (SV, SVA, EN, MA...)
    │   └── [betygsfördelning-tabell].px  ← A–F fördelning per ämne
    ├── Nationella_prov/
    │   ├── [NP-åk6-tabell].px            ← Andel godkända, åk 6
    │   ├── [NP-åk9-tabell].px            ← Andel godkända, åk 9
    │   ├── [relation-åk6-tabell].px      ← Betyg vs NP relation, åk 6
    │   └── [relation-åk9-tabell].px      ← Betyg vs NP relation, åk 9
    ├── Behorighet/
    │   └── [behörighet-tabell].px        ← Behörighet till gymnasium
    └── Kunskapskrav/
        └── [kk-tabell].px                ← Andel med alla kk uppfyllda
```

> Tabellnamnen ändras ibland vid Skolverkets uppdateringar.  
> Koden i `index.html` söker dynamiskt via kategori-listing → kända fallback-sökvägar.

---

## Svarsformat

PxWeb returnerar JSON med denna struktur:

```json
{
  "columns": [
    { "code": "Kommun", "text": "Kommun", "type": "d" },
    { "code": "Kön",    "text": "Kön",    "type": "d" },
    { "code": "Tid",    "text": "Tid",    "type": "t" },
    { "code": "000",    "text": "Meritvärde", "type": "c" }
  ],
  "data": [
    { "key": ["0684", "1", "20242025"], "values": ["214.5"] },
    { "key": ["0684", "2", "20242025"], "values": ["236.2"] },
    { "key": ["0684", "T", "20242025"], "values": ["225.8"] },
    { "key": ["00",   "T", "20242025"], "values": ["227.6"] }
  ]
}
```

- `columns`: Variabeldefinitioner. `type: "d"` = dimension, `type: "t"` = tid, `type: "c"` = värde.
- `data[i].key`: Radnyckeln — värden för varje dimension i kolumn-ordning.
- `data[i].values`: Faktiska mätvärden (alltid som strängar — konvertera med `parseFloat()`).

### Exempel: extrahera meritvärde för Sävsjö

```javascript
const rows = response.data;

// Hitta totalt meritvärde för Sävsjö, senaste år
const savsjoTotal = rows
  .filter(r => r.key.includes('0684') && r.key.includes('T'))
  .sort((a, b) => b.key.at(-1).localeCompare(a.key.at(-1)))  // senaste år först
  [0]?.values[0];

console.log('Meritvärde Sävsjö:', parseFloat(savsjoTotal));
```

---

## Kända kommunekoder

| Kod | Namn |
|-----|------|
| `00` | Riket (riksnivå) |
| `0684` | Sävsjö |
| `0680` | Jönköping |
| `0682` | Nässjö |
| `0685` | Vetlanda |
| `0686` | Eksjö |
| `0687` | Tranås |

Alla kommunekoder: https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/

---

## Vanliga fel

| Fel | Orsak | Lösning |
|-----|-------|---------|
| `CORS-fel i konsolen` | Sidan öppnad som `file://` | Använd Live Server eller GitHub Pages |
| `HTTP 404` | Tabellnamnet ändrat | Bläddra kategori-listingen och hitta nytt tabellnamn |
| `values: ["."]` | Sekretessmarkerad (< 5 elever) | Visa `–` i gränssnittet |
| `values: [".."]` | Saknas / ej publicerad | Visa `–` i gränssnittet |
| Tom array `data: []` | Ingen data för valda filter | Kontrollera kommunKod och Tid |

---

## Selektionstyper (filter)

```javascript
// Exakta värden
{ "filter": "item", "values": ["0684", "00"] }

// De N senaste tidsperioderna
{ "filter": "top", "values": ["5"] }

// Alla tillgängliga värden
{ "filter": "all", "values": ["*"] }

// Intervall (kräver sorterade koder)
{ "filter": "fromTo", "values": ["20202021", "20242025"] }
```

---

## Responsivt API-anrop i JavaScript

```javascript
const PXBASE = 'https://statistikdatabasen.skolverket.se/PxWeb/api/v1/sv/Skolverkets_statistikdatabas';

async function pxQuery(tablePath, query) {
  const response = await fetch(PXBASE + tablePath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ query, response: { format: 'json' } }),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// Exempel: hämta meritvärde för Sävsjö, senaste 5 åren, per kön
const data = await pxQuery(
  '/Kommunala_jamforelsetal/Grundskola/Betyg/GrundskBetyg.px',
  [
    { code: 'Kommun', selection: { filter: 'item',  values: ['0684', '00'] } },
    { code: 'Kön',    selection: { filter: 'item',  values: ['1', '2', 'T'] } },
    { code: 'Tid',    selection: { filter: 'top',   values: ['5'] } },
  ]
);
```
