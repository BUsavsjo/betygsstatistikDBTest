# TODO

## Excel-ersattning

Malet ar att ersatta den gamla arbetsboken `data/dokumentation/Betygsstatistik lasar 24-25 med SVA - 2025-08-15 - Korrigerad.xlsx`.

Behörighet gymnasiet betyder i projektet yrkesbehörighet till gymnasiet, inte samtliga högskoleförberedande behörigheter.

| Excelblad | Status | Plan |
| --- | --- | --- |
| Meritvärde SVA | Delvis | Bygg vy med årskurs, flera skolenheter, kön och SV/SVA-grupp. |
| Genomsnittligt meritvärde | Delvis | Bygg tabell per årskurs, skolenhet och kön. |
| Betygspoäng per ämne | Delvis | Beräkna och visa genomsnittlig betygspoäng per ämne. |
| Betygspoäng nyanlända | Delvis | Visa samma ämnesmått filtrerat på elever som läser SVA. |
| NP andel godkända | Delvis | Behåll lokal NP-import och lägg till urval för årskurs och flera skolenheter. |
| Relationen betyg och nationella | Delvis | Behåll relationen och lägg till urval per årskurs och flera skolenheter. |
| Behörighet gymnasiet | Delvis | Visa yrkesbehörighet för åk 9 per skolenhet och kön. |
| Fördelning betyg pr ämne tabell | Delvis | Visa full A-F-fördelning per ämne, årskurs, skolenhet och elevgrupp. |
| Fördelning betyg per ämne diagr | Delvis | Bygg diagram på samma filtrerade A-F-data. |
| Uppnått kunskapskr i alla ämnen | Delvis | Visa egen tabell per årskurs, skolenhet och kön. |
| Kontroll antal betyg | Saknas | Bygg kontrollvy för antal betyg per ämne och specialkoder. |

## Byggordning

- [x] Dokumentera Excel-täckningen.
- [x] Bygg gemensamma urval för årskurs och flera skolenheter.
- [x] Bygg meritvärde och SV/SVA-vyer med urvalen.
- [x] Bygg ämnesvy för betygspoäng.
- [x] Bygg full A-F-fördelning.
- [x] Bygg uppnått alla ämnen och yrkesbehörighet åk 9.
- [ ] Bygg kontrollvy för antal betyg och specialkoder.
- [ ] Validera 2024/25 mot Excel blad för blad.

## Senare

- [ ] Lägg till cachning i `sessionStorage`.
- [ ] Lägg till CSV-export.
- [ ] Lägg till jämförelse med flera kommuner.
- [ ] Förbättra tillgänglighet och utskriftsvy.
