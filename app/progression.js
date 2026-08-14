const progressionState = {
  data: null,
  school: 'huvudman',
  gender: 'Alla',
  group: 'Alla'
};

function progressionOption(value, label){
  return `<option value="${esc(value)}">${esc(label)}</option>`;
}

function populateProgressionFilters(){
  const data = progressionState.data;
  const cohortLabel = data?.ak6_lasar && data?.ak9_lasar
    ? `Åk 6 ${data.ak6_lasar} → åk 9 ${data.ak9_lasar}`
    : 'Underlag saknas';
  $('progressionCohortFilter').innerHTML = progressionOption(data?.ak9_lasar || '', cohortLabel);

  const schools = new Map();
  for(const row of data?.segment || []){
    if(row.niva === 'skolenhet' && row.skolenhetskod){
      schools.set(String(row.skolenhetskod), row.skolenhetsnamn || row.skolenhetskod);
    }
  }
  $('progressionSchoolFilter').innerHTML = progressionOption('huvudman', 'Sävsjö kommun')
    + [...schools.entries()]
      .sort((a,b) => a[1].localeCompare(b[1], 'sv'))
      .map(([value,label]) => progressionOption(value,label))
      .join('');
  $('progressionGenderFilter').innerHTML = [
    progressionOption('Alla', 'Alla'),
    progressionOption('Flickor', 'Flickor'),
    progressionOption('Pojkar', 'Pojkar')
  ].join('');
  $('progressionGroupFilter').innerHTML = [
    progressionOption('Alla', 'Alla'),
    progressionOption('SV', 'SV'),
    progressionOption('SVA', 'SVA')
  ].join('');

  progressionState.school = 'huvudman';
  progressionState.gender = 'Alla';
  progressionState.group = 'Alla';
}

function initializeProgressionView(progression){
  progressionState.data = progression;
  populateProgressionFilters();
  $('progressionMethod').innerHTML = `
    <h2>Om måtten</h2>
    <p class="small">Analysen jämför samma elevs giltiga betyg i samma ämne. Betygssteg räknas F=0, E=1, D=2, C=3, B=4 och A=5. SV/SVA-filtret utgår från kursplanen i åk 9.</p>
    <p class="small">Meritvärdet visas endast som slutmått i åk 9. Skillnaden mellan meritvärde i åk 6 och åk 9 är inte ett rent progressionsmått eftersom ämnesuppsättningen kan skilja sig. Korrelation visar samband, inte orsak.</p>
    <p class="small">Grupper med färre än ${esc(progression?.sekretessgrans || 10)} matchade elever undertrycks.</p>`;
  renderProgressionView();
}

function updateProgressionFilters(){
  progressionState.school = $('progressionSchoolFilter').value || 'huvudman';
  progressionState.gender = $('progressionGenderFilter').value || 'Alla';
  progressionState.group = $('progressionGroupFilter').value || 'Alla';
  renderProgressionView();
}

function selectedProgressionSegment(){
  const data = progressionState.data;
  if(!data || data.status !== 'ok') return null;
  return (data.segment || []).find(row =>
    (progressionState.school === 'huvudman'
      ? row.niva === 'huvudman'
      : String(row.skolenhetskod || '') === progressionState.school)
    && row.kon === progressionState.gender
    && row.elevgrupp === progressionState.group
  ) || null;
}

function clearProgressionResults(){
  $('progressionResults').hidden = true;
  $('progressionCards').innerHTML = '';
  $('progressionRows').innerHTML = '';
  destroyChart('progressionChangeChart');
  destroyChart('progressionGradeChart');
}

function renderProgressionUnavailable(data){
  clearProgressionResults();
  const ak6Year = data?.ak6_lasar;
  const ak9Year = data?.ak9_lasar;
  const paths = ak6Year && ak9Year
    ? ` Förväntade mappar: data/raw/betyg/${ak6Year}/ak6/ och data/raw/betyg/${ak9Year}/ak9/.`
    : '';
  $('progressionStatus').textContent = `Historiska betyg för åk 6 saknas eller har inte importerats.${paths}`;
}

function renderProgressionSuppressed(){
  clearProgressionResults();
  $('progressionStatus').textContent = 'Resultatet visas inte eftersom gruppen är för liten.';
}

function progressionCard(label, value, detail){
  return `<article class="card"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><div class="small">${esc(detail)}</div></article>`;
}

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

function renderProgressionCards(segment){
  const match = segment.matchning;
  const overview = segment.oversikt;
  $('progressionCards').innerHTML = [
    progressionCard('Matchade elever', match.antal_matchade, `${fmt(match.matchningsgrad, ' %')} av eleverna i åk 9`),
    progressionCard('Genomsnittlig betygsförändring', fmt(overview.genomsnittlig_forandring, ' steg'), 'Samma elev och samma ämne'),
    progressionCard('Jämförbara ämnesbetyg som höjts', fmt(overview.andel_hojda_betyg, ' %'), 'Andel av alla jämförbara ämnesbetyg'),
    progressionCard('Jämförbara ämnesbetyg som är oförändrade', fmt(overview.andel_oforandrade_betyg, ' %'), 'Andel av alla jämförbara ämnesbetyg'),
    progressionCard('Jämförbara ämnesbetyg som sänkts', fmt(overview.andel_sankta_betyg, ' %'), 'Andel av alla jämförbara ämnesbetyg')
  ].join('');
}

function renderProgressionSecondary(segment){
  $('progressionSecondary').innerHTML = `
    <h2>Kompletterande slutmått</h2>
    <p><strong>Meritvärde i årskurs 9: ${fmt(segment.merit_ak9?.genomsnitt_merit_17)}</strong></p>
    <p class="small">Meritvärdet visar slutresultatet i årskurs 9. Det jämförs inte med årskurs 6 eftersom ämnesuppsättningen och beräkningsunderlaget kan skilja sig.</p>`;
}

function renderProgressionCharts(subjects){
  const visible = subjects.filter(row => !row.undertryckt);
  makeChart('progressionChangeChart', 'bar', {
    labels: visible.map(row => row.amnesnamn),
    datasets: [
      {label:'Höjt %', data:visible.map(row => row.andel_hojda), backgroundColor:'#258a5b'},
      {label:'Oförändrat %', data:visible.map(row => row.andel_oforandrade), backgroundColor:'#8a7a35'},
      {label:'Sänkt %', data:visible.map(row => row.andel_sankta), backgroundColor:'#b73535'}
    ]
  }, {scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,max:100}}});
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
}

function renderProgressionTable(subjects){
  $('progressionRows').innerHTML = subjects
    .filter(row => !row.undertryckt)
    .map(row => `<tr>
      <td><strong>${esc(row.amnesnamn)}</strong></td>
      <td class="numeric">${esc(row.antal_elever)}</td>
      <td class="numeric">${fmt(row.genomsnitt_ak6)}</td>
      <td class="numeric">${fmt(row.genomsnitt_ak9)}</td>
      <td class="numeric">${fmt(row.genomsnittlig_forandring)}</td>
      <td class="numeric">${fmt(row.andel_hojda, ' %')}</td>
      <td class="numeric">${fmt(row.andel_oforandrade, ' %')}</td>
      <td class="numeric">${fmt(row.andel_sankta, ' %')}</td>
      <td class="numeric">${fmt(row.korrelation)}</td>
    </tr>`)
    .join('');
}

function renderProgressionView(){
  const data = progressionState.data;
  if(!data || data.status !== 'ok'){
    renderProgressionUnavailable(data);
    return;
  }
  const segment = selectedProgressionSegment();
  if(!segment || segment.undertryckt){
    renderProgressionSuppressed();
    return;
  }

  const schoolLabel = progressionState.school === 'huvudman'
    ? 'Sävsjö kommun'
    : segment.skolenhetsnamn;
  $('progressionStatus').textContent = `${schoolLabel} · ${progressionState.gender} · ${progressionState.group} · åk 6 ${data.ak6_lasar} till åk 9 ${data.ak9_lasar}`;
  $('progressionResults').hidden = false;
  renderProgressionInterpretation(segment);
  renderProgressionCards(segment);
  renderProgressionCorrelation(segment);
  renderProgressionCharts(segment.amnen || []);
  renderProgressionTable(segment.amnen || []);
  renderProgressionSecondary(segment);
}
