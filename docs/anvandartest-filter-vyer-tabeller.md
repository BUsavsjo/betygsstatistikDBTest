# Användartest: filter, vyer och tabeller

## Syfte

Det här testet verifierar att användare förstår och lyckas använda:

- filtren för årskurs, skolenhet, kön och elevgrupp
- växlingen mellan olika vyer/flikar
- tabellerna och deras urvalssammanfattningar

Testet är utformat för den nuvarande sidan och utgår från att vissa vyer kan visa olika mycket innehåll beroende på om lokal JSON, publicerad JSON eller demodata används.

## Rekommenderad testmiljö

- Kör sidan via `npm run dev` för lokal server med proxystöd.
- Öppna [index.html](/C:/Users/petwen/OneDrive%20-%20H%C3%B6glandsf%C3%B6rbundet/Projekt/betygsstatistikDBTest/index.html) via `http://localhost:3000`, inte via `file://`.
- Använd helst lokal eller publicerad aggregerad JSON så att filtren för skolor, kön och elevgrupp fylls med verkliga val.
- Om bara demodata finns fungerar testet ändå, men vissa resultat blir mindre representativa.

## Deltagare

- 3 till 5 personer räcker för ett första användartest.
- Välj gärna en blandning av personer som kan skolstatistik väl och personer som mest ska använda sidan i praktiken.

## Testledarens upplägg

- Be deltagaren tänka högt.
- Hjälp inte till direkt när något blir svårt.
- Notera var deltagaren tvekar, feltolkar en tabell eller missar att ett filter påverkar flera vyer.
- Mät gärna tid per uppgift och om uppgiften klaras utan hjälp.

## Förberedelser före test

1. Starta sidan och kontrollera att data har lästs in.
2. Säkerställ att filterraden visas.
3. Bekräfta vilka årskurser som faktiskt finns i aktuell datamängd.
4. Kontrollera att fliken **Teknisk diagnostik** finns kvar för felsökning, men använd den inte i själva användartestet.
5. Nollställ filtren innan varje ny deltagare.

## Testuppgifter

### 1. Hitta rätt urval

Be deltagaren:

"Visa bara en vald årskurs och en eller två skolor."

Observera:

- Förstår deltagaren att årskurs och skolenheter kan ha flera val samtidigt?
- Märker deltagaren att vissa skolor blir otillgängliga beroende på vald årskurs?
- Förstår deltagaren vad knapparna **Alla skolor** och **Nollställ urval** gör?

Godkänt resultat:

- Deltagaren gör ett avgränsat urval utan hjälp.

### 2. Förstå vad urvalet påverkar

Be deltagaren:

"Gå till en annan flik och kontrollera om samma urval fortfarande gäller."

Observera:

- Letar deltagaren efter någon visuell bekräftelse?
- Ser deltagaren tabellens rad `Urval:` och kan använda den för att verifiera läget?
- Förväntar sig deltagaren att filtren ska nollställas när flik byts?

Godkänt resultat:

- Deltagaren förstår att samma filterläge lever vidare mellan vyerna.

### 3. Hitta en jämförelse mellan kön

Be deltagaren:

"Ta reda på om flickor och pojkar visas separat någonstans."

Observera:

- Hittar deltagaren fliken **Jämförelser**?
- Förstår deltagaren skillnaden mellan att filtrera på kön och att läsa en jämförelsetabell som visar båda könen samtidigt?
- Tolkar deltagaren kolumnerna `Pojkar`, `Flickor`, `Totalt` och `Skillnad F-P` rätt?

Godkänt resultat:

- Deltagaren hittar rätt vy och kan förklara vad tabellen visar.

### 4. Byt elevgrupp och tolka konsekvensen

Be deltagaren:

"Byt till en annan elevgrupp och beskriv vad som ändrades i tabellen."

Observera:

- Märker deltagaren vilka tabeller och kort som påverkas?
- Förstår deltagaren om vissa rader försvinner därför att urvalet inte längre matchar?
- Reagerar deltagaren på om tabellens kolumn för elevgrupp döljs eller blir tom i vissa lägen?

Godkänt resultat:

- Deltagaren ser att innehållet ändras och kan beskriva varför.

### 5. Hitta resultat per ämne

Be deltagaren:

"Ta fram resultat för ett ämne och jämför skolor eller grupper."

Observera:

- Hittar deltagaren fliken **Resultat per ämne**?
- Förstår deltagaren att tabellen kan behöva scrollas horisontellt?
- Kan deltagaren skilja på ämne, betygspoäng, antal och A-F-relaterade kolumner?

Godkänt resultat:

- Deltagaren hittar ämnesvyn och kan läsa ut minst en konkret jämförelse.

### 6. Förstå tabellernas struktur

Be deltagaren:

"Beskriv hur tabellen är grupperad och hur du ser vilken skola en rad tillhör."

Observera:

- Förstår deltagaren den grupperade tabellayouten med skolnamn som sticky första kolumn?
- Missar deltagaren att flera rader hör till samma skola?
- Uppfattas tabellstrukturen som tydlig eller visuellt tung?

Godkänt resultat:

- Deltagaren kan korrekt beskriva hur grupperingen fungerar.

### 7. Hitta måluppfyllelse eller yrkesbehörighet

Be deltagaren:

"Ta reda på hur det går för kommunen totalt inom måluppfyllelse eller yrkesbehörighet."

Observera:

- Förstår deltagaren skillnaden mellan kort överst och tabellen längre ned?
- Hittar deltagaren rätt flik utan hjälp?
- Tolkar deltagaren procentvärden rätt?

Godkänt resultat:

- Deltagaren hittar ett totalmått och kan läsa upp värdet.

### 8. Bedöm vad som saknas

Be deltagaren:

"Finns det någon vy där du är osäker på om data saknas eller om du bara inte hittar den?"

Observera:

- Är det tydligt när data saknas?
- Förstår deltagaren skillnaden mellan tom vy, filtrerat bort innehåll och faktisk databegränsning?
- Hjälper fliken **Vilken data som finns** användaren?

Godkänt resultat:

- Deltagaren kan peka ut minst ett ställe där kommunikationen är tydlig eller otydlig.

## Frågor efter testet

Ställ dessa frågor direkt efter genomförandet:

1. Vad var enklast att förstå?
2. Vad var svårast att förstå?
3. Var något filter eller någon flik oväntad?
4. Var tabellerna lätta att läsa och jämföra i?
5. Saknade du någon tydlig återkoppling när ett urval ändrades?
6. Om du skulle använda sidan i arbetet, vad skulle du lita minst på?

## Observationsmall

Använd gärna denna enkla mall per deltagare:

| Uppgift | Klarad utan hjälp | Tid | Problem/felsteg | Kommentar |
|---|---|---:|---|---|
| 1. Hitta rätt urval | Ja/Nej |  |  |  |
| 2. Förstå vad urvalet påverkar | Ja/Nej |  |  |  |
| 3. Hitta könsjämförelse | Ja/Nej |  |  |  |
| 4. Byt elevgrupp | Ja/Nej |  |  |  |
| 5. Hitta resultat per ämne | Ja/Nej |  |  |  |
| 6. Förstå tabellstruktur | Ja/Nej |  |  |  |
| 7. Hitta totalmått | Ja/Nej |  |  |  |
| 8. Bedöm vad som saknas | Ja/Nej |  |  |  |

## Vad ni särskilt bör leta efter

- Om flerselect-fälten för årskurs och skola uppfattas som tydliga.
- Om användare förstår att vissa flikar döljs i rena åk 3-lägen.
- Om tabellernas `Urval:`-rad faktiskt används.
- Om användare förstår varför vissa rader eller skolor försvinner efter filterval.
- Om skillnaden mellan jämförelsevy, ämnesvy och utfallsvy är tydlig.
- Om horisontell scroll i breda tabeller märks tillräckligt tydligt.

## Efterarbete

Sammanställ fynd i tre nivåer:

- Kritiska problem: användaren kan inte slutföra en central uppgift.
- Tydliga friktioner: uppgiften går att slutföra men med tvekan eller felsteg.
- Förbättringsidéer: mindre justeringar i text, layout eller återkoppling.

Prioritera först sådant som påverkar:

- filterförståelse
- kopplingen mellan filter och aktiv vy
- tabellernas läsbarhet
- tydlighet när data saknas eller är bortfiltrerad
