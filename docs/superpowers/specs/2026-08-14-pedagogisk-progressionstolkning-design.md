# Pedagogisk tolkning av progression åk 6–9 – design

## Syfte och målgrupp

Progressionsvyn ska kunna tolkas direkt av en rektor eller huvudman utan statistisk förkunskap. Sidan ska först svara på vad som har mätts och vad resultatet säger, därefter visa diagram och detaljer.

Ändringen gäller presentation och förklaringar. Befintliga beräkningar, anonymisering, sekretessgräns och publicerat JSON-kontrakt ändras inte.

## Grundprincip

Vyn ska konsekvent skilja mellan:

- **elever**, när matchningsgrad och antal matchade beskrivs
- **jämförbara ämnesbetyg**, när höjt, oförändrat, sänkt och genomsnittlig förändring beskrivs
- **samband**, som beskriver hur elevernas relativa resultat hänger ihop mellan årskurserna men inte om betygen har höjts eller varför de förändrats

Texten får aldrig omformulera andelen sänkta ämnesbetyg till andelen elever som sänkt sina betyg.

## Informationsordning

Efter filtren visas innehållet i denna ordning:

1. urval och matchningsgrad
2. en synlig ruta med rubriken **Så kan resultatet tolkas**
3. nyckeltal med tydliga benämningar
4. en synlig förklaring av sambandet
5. diagram
6. ämnestabell
7. meritvärde som ett avskilt kompletterande slutmått
8. fullständig metodförklaring

Viktiga definitioner ska vara synliga. De får inte enbart placeras i informationsknappar eller hjälptexter som kräver hovring.

## Dynamisk sammanfattning

Ett nytt element `progressionInterpretation` byggs från det valda segmentets befintliga aggregat. Texten uppdateras tillsammans med filtren.

För kommunresultatet kan texten exempelvis vara:

> **Så kan resultatet tolkas**
> 114 av 121 elever i årskurs 9 kunde följas tillbaka till årskurs 6. Bland deras jämförbara ämnesbetyg har 26,3 % höjts, 36 % varit oförändrade och 37,8 % sänkts. Det motsvarar ungefär 4 av 10 jämförbara ämnesbetyg som har sänkts.
>
> Den genomsnittliga betygsförändringen är −0,2 steg. Det innebär att samma elevers betyg i samma ämnen i genomsnitt ligger 0,2 betygssteg lägre i årskurs 9. Ett steg motsvarar exempelvis E till D eller C till B. Måttet beskriver alla jämförbara ämnesbetyg tillsammans, inte varje enskild elev.
>
> Analysen följer en och samma elevgrupp från årskurs 6 till årskurs 9 under tre år. Resultatet behöver tolkas försiktigt. Rapporten visar inte en trend över flera elevkullar, fler årskurser eller en längre tidsperiod.

Texten använder segmentets exakta procenttal. Formuleringen **ungefär X av 10** beräknas genom att avrunda andelen sänkta ämnesbetyg till närmaste tiondel av gruppen. Den formuleringen ska alltid följas av orden **jämförbara ämnesbetyg**.

För genomsnittlig förändring används följande regler:

- negativt värde: betygen ligger i genomsnitt `abs(värdet)` steg lägre i årskurs 9
- positivt värde: betygen ligger i genomsnitt `värdet` steg högre i årskurs 9
- noll: de jämförbara betygen är i genomsnitt oförändrade

## Nyckeltal

Nyckeltalen ska vara:

1. **Matchade elever** – antal och matchningsgrad
2. **Genomsnittlig betygsförändring** – värde med suffixet `steg`
3. **Jämförbara ämnesbetyg som höjts** – andel
4. **Jämförbara ämnesbetyg som är oförändrade** – andel
5. **Jämförbara ämnesbetyg som sänkts** – andel

Korrelation och meritvärde ska inte ligga som hjälptext under något av dessa kort.

## Förklaring av samband

Ett nytt synligt element `progressionCorrelation` visas efter nyckeltalen. Det innehåller värdet, en försiktig beskrivning av styrkan och en tolkning.

För värdet `0,8` ska texten följa denna modell:

> **Samband mellan resultaten: 0,8 – starkt positivt samband**
> Elever som hade relativt höga betyg i årskurs 6 tenderar även att ha relativt höga betyg i årskurs 9. Sambandet beskriver hur stabil elevernas inbördes placering är. Det visar inte om betygen har höjts eller sänkts, varför resultaten förändrats eller vilken effekt skolan haft.

Beskrivningen av styrkan använder samma fasta gränser för positiva och negativa värden:

- `abs(r) < 0,2`: inget tydligt samband
- `0,2 ≤ abs(r) < 0,4`: svagt samband
- `0,4 ≤ abs(r) < 0,7`: måttligt samband
- `abs(r) ≥ 0,7`: starkt samband

Riktningen anges som positiv eller negativ när `abs(r) ≥ 0,2`. Om korrelationen är `null` visas **Sambandet kan inte beräknas för det valda underlaget.**

## Diagram och tabell

Diagrammet över genomsnittlig betygsnivå ska visa betygsskalan `F, E, D, C, B, A` i stället för de tekniska talen `0–5` på y-axeln.

Ovanför ämnesdiagrammen och tabellen visas ett gemensamt val **Sortera ämnen** med alternativen:

- Ämnesordning
- Störst höjning
- Störst sänkning
- Starkast samband

Valet ska sortera båda diagrammen och ämnestabellen på samma sätt. **Störst höjning** sorterar fallande på genomsnittlig förändring, **Störst sänkning** stigande och **Starkast samband** fallande på korrelationens absoluta värde med saknade samband sist. Grundalternativet återställer den befintliga ämnesordningen. Sorteringen använder endast de redan publicerade ämnesaggregaten och skapar inga nya elevgrupper.

Ämnestabellen behåller befintliga värden men får tydligare rubriker och en kort synlig introduktion:

> Varje rad jämför elever som har ett giltigt betyg i ämnet både i årskurs 6 och årskurs 9.

Kolumnen **Elever** byter namn till **Jämförbara elever**. **Förändring** byter namn till **Förändring i steg**. **Samband** byter namn till **Samband mellan resultaten**. En ny kolumn **Kort tolkning** sammanför förändring och samband i vardagsspråk. Tabellen ska behålla procenttecknet på samma rad som värdet vid normal skrivbordsbredd.

## Kort ämnestolkning

Varje publicerbar ämnesrad får en dynamisk text som beskriver två separata observationer:

1. om den genomsnittliga betygsnivån ligger högre, lägre eller är oförändrad
2. vad korrelationen säger om elevernas relativa placering

Exempel för matematik med förändring `−0,44` och korrelation `0,79`:

> Betygen ligger i genomsnitt 0,4 steg lägre i årskurs 9. Det starka positiva sambandet innebär att elevernas relativa placering är förhållandevis stabil. Det visar inte varför nivån har förändrats.

Texten använder det exakta tecknet på förändringen och samma korrelationsgränser som den övergripande sambandsförklaringen. Positiv förändring beskrivs som högre, negativ som lägre och exakt noll som oförändrad. Ingen godtycklig gräns ska användas för att kalla små förändringar oförändrade.

För positiva samband används följande andra mening:

- inget tydligt samband: **Det finns inget tydligt mönster i elevernas relativa placering.**
- svagt positivt: **Elevernas relativa placering varierar mer mellan årskurserna.**
- måttligt positivt: **Det finns ett tydligt men inte starkt mönster i elevernas relativa placering.**
- starkt positivt: **Elevernas relativa placering är förhållandevis stabil.**

Negativa samband använder den befintliga förklaringen att elevernas relativa placering tenderar att vara omvänd. Varje ämnestolkning avslutas med **Det visar inte varför nivån har förändrats.**

Ämnen ska inte delas in i elevgrupperna höjda, oförändrade eller sänkta. Andelarna i tabellen avser fortfarande jämförbara elev–ämnespar. Den korta tolkningen får inte beskriva dem som andelar elever.

## Meritvärde och metod

Meritvärdet flyttas från nyckeltalen till en separat ruta med rubriken **Kompletterande slutmått**:

> Meritvärde i årskurs 9: {värde}. Meritvärdet visar slutresultatet i årskurs 9. Det jämförs inte med årskurs 6 eftersom ämnesuppsättningen och beräkningsunderlaget kan skilja sig.

Metodrutan längst ned behålls och kompletterar den synliga tolkningen. Den ska fortsatt beskriva betygsskalan, SV/SVA-urvalet, meritvärdets begränsning, sekretessgränsen och att samband inte visar orsak.

## Saknat och undertryckt underlag

Befintliga tomlägen behålls. Ingen tolkning, korrelation, merit eller tabell visas när underlaget saknas eller gruppen är undertryckt. Texten **Resultatet visas inte eftersom gruppen är för liten.** ska fortsatt användas.

## Tillgänglighet

- Alla centrala förklaringar ska vara vanlig synlig text.
- Färg får inte vara den enda signalen för höjt, oförändrat och sänkt.
- Diagrammens legend och tabellrubriker ska behålla textetiketter.
- Betygsskalan F–A ska kunna förstås utan att användaren behöver läsa metodrutan.

## Testning

Playwrighttestet för progression ska verifiera att:

- den dynamiska tolkningsrutan visar matchade elever och andelarna höjt, oförändrat och sänkt
- formuleringen **jämförbara ämnesbetyg** används och att andelen inte beskrivs som andel elever
- genomsnittlig förändring förklaras som högre, lägre eller oförändrad beroende på tecken
- tolkningsrutan anger att analysen följer samma elevgrupp under tre år och inte visar en trend över flera elevkullar eller en längre tidsperiod
- fixturevärdet `0,62` beskrivs som ett måttligt positivt samband och förklaringen anger att sambandet inte visar orsak eller skoleffekt
- de fem nya nyckeltalsrubrikerna visas
- meritvärdet visas separat som kompletterande slutmått
- tabellens nya rubriker visas
- ämnestabellen visar en kort tolkning som håller förändring och samband isär
- sorteringsvalet **Starkast samband** placerar fixtureämnet Engelska före Matematik i både diagram och tabell
- sorteringsvalet **Störst höjning** placerar fixtureämnet Matematik före Engelska i både diagram och tabell
- saknat och undertryckt underlag fortfarande döljer resultatet

Efter ändringen körs hela Python- och Playwrightsviten samt Pages-bygget. Eftersom beräkning och importlogik inte ändras behöver rådata inte importeras på nytt; den befintliga anonymiserade progressionsfilen återanvänds.
