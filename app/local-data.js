async function tryLoadLocalSource(base, sourceKind){
  try{
    const [manifest, overview, svSva, distribution] = await Promise.all([
      fetchJson(`${base}/manifest.json`),
      fetchJson(`${base}/betygsstatistik_oversikt.json`),
      fetchJson(`${base}/betygsstatistik_sv_sva.json`),
      fetchJson(`${base}/betygsstatistik_betygsfordelning_amne.json`)
    ]);
    const [control, npPass, npRelation] = await Promise.all([
      fetchJsonOptional(`${base}/betygsstatistik_kontroll_betyg.json`, []),
      fetchJsonOptional(`${base}/np_andel_godkanda.json`, []),
      fetchJsonOptional(`${base}/np_betyg_relation.json`, [])
    ]);
    const hasGrades = manifest.arskurser?.some(a => Number(a.rows) > 0);
    const hasNp = manifest.np_arskurser?.some(a => Number(a.rows) > 0) || npPass.length || npRelation.length;
    if(!hasGrades && !hasNp) return null;
    return {base, sourceKind, isDemo: sourceKind === 'demo' || norm(manifest.source).includes('dummy') || norm(manifest.source).includes('demo'), manifest, overview, svSva, distribution, control, npPass, npRelation};
  }catch{
    return null;
  }
}
async function tryLoadLocalYear(localYear){
  if(!localYear) return null;
  const processed = await tryLoadLocalSource(`data/processed/${localYear}/json`, 'processed');
  if(processed) return processed;
  const output = await tryLoadLocalSource(`data/output/${localYear}/json`, 'output');
  if(output) return output;
  return tryLoadLocalSource(`data/demo/${localYear}/json`, 'demo');
}
async function fetchJsonOptional(url, fallback){
  try{ return await fetchJson(url); }catch{ return fallback; }
}
function localRows(data, arskurs, niva='alla_skolenheter'){
  return (data || []).filter(r => Number(r.arskurs) === Number(arskurs) && r.niva === niva);
}
function uniqueSorted(values){
  return [...new Set(values.filter(v => v !== null && v !== undefined && String(v).trim() !== '').map(String))]
    .sort((a,b) => a.localeCompare(b, 'sv', {numeric:true}));
}
function selectedValues(id){
  return [...$(id).selectedOptions].map(o => o.value);
}
function schoolLabel(row){
  if(row.niva === 'alla_skolenheter' || row.niva === 'kommun') return 'Alla skolenheter';
  return row.skolenhetsnamn || row.skolenhetskod || 'Okänd skolenhet';
}
function schoolKey(row){
  return row.niva === 'alla_skolenheter' || row.niva === 'kommun' ? '__all__' : String(row.skolenhetskod || '');
}
function updateFilterState(){
  state.filters = {
    grades: selectedValues('gradeFilter'),
    schools: selectedValues('schoolFilter'),
    gender: $('genderFilter').value || 'Alla',
    group: $('groupFilter').value || 'Alla'
  };
}
function populateSelect(id, options, selectedValues){
  const selected = new Set(selectedValues || []);
  $(id).innerHTML = options.map(o => `<option value="${esc(o.value)}"${selected.has(String(o.value)) ? ' selected' : ''}>${esc(o.label)}</option>`).join('');
}
function populateLocalFilters(local){
  const overview = local.overview || [];
  const grades = uniqueSorted(overview.map(r => r.arskurs));
  const schoolRows = overview.filter(r => r.niva === 'skolenhet');
  const schools = uniqueSorted(schoolRows.map(r => schoolKey(r))).map(code => {
    const row = schoolRows.find(r => schoolKey(r) === code);
    return {value: code, label: schoolLabel(row)};
  });
  const filterRows = [
    ...(local.overview || []),
    ...(local.svSva || []),
    ...(local.distribution || []),
    ...(local.control || [])
  ];
  const genders = uniqueSorted(filterRows.map(r => r.kon).filter(v => v && v !== 'Alla'));
  const groups = uniqueSorted(filterRows.map(r => r.elevgrupp).filter(v => v && v !== 'Alla'));

  state.filters.grades = grades;
  state.filters.schools = schools.map(s => s.value);
  state.filters.gender = 'Alla';
  state.filters.group = 'Alla';

  populateSelect('gradeFilter', grades.map(g => ({value:g, label:`Åk ${g}`})), state.filters.grades);
  populateSelect('schoolFilter', schools, state.filters.schools);
  $('genderFilter').innerHTML = '<option value="Alla">Alla</option>' + genders.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
  $('groupFilter').innerHTML = '<option value="Alla">Alla</option>' + groups.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
  $('localFilters').classList.add('active');
}
function rowGender(row){ return row.kon || 'Alla'; }
function rowGroup(row){ return row.elevgrupp || 'Alla'; }
function localFilterRows(rows, {allowAllLevel=false, forceGrade=null}={}){
  const f = state.filters;
  return (rows || []).filter(r => {
    const gradeValue = String(r.arskurs ?? '');
    if(forceGrade && Number(r.arskurs) !== Number(forceGrade)) return false;
    if(f.grades.length && !f.grades.includes(gradeValue)) return false;
    if(f.gender !== 'Alla' && rowGender(r) !== f.gender) return false;
    if(f.group !== 'Alla' && rowGroup(r) !== f.group) return false;
    if(allowAllLevel && (r.niva === 'alla_skolenheter' || r.niva === 'kommun')) return true;
    return r.niva === 'skolenhet' && (!f.schools.length || f.schools.includes(schoolKey(r)));
  });
}
function localBaseFilter(rows, {forceGrade=null}={}){
  const f = state.filters;
  return (rows || []).filter(r => {
    if(forceGrade && Number(r.arskurs) !== Number(forceGrade)) return false;
    if(f.grades.length && !f.grades.includes(String(r.arskurs ?? ''))) return false;
    if(f.group !== 'Alla' && rowGroup(r) !== f.group) return false;
    return r.niva === 'skolenhet' && (!f.schools.length || f.schools.includes(schoolKey(r)));
  });
}
function gradePointAverage(row){
  const total = Number(row.antal_betyg || 0);
  if(!total) return null;
  const sum =
    Number(row.antal_A || 0) * 20 +
    Number(row.antal_B || 0) * 17.5 +
    Number(row.antal_C || 0) * 15 +
    Number(row.antal_D || 0) * 12.5 +
    Number(row.antal_E || 0) * 10;
  return Math.round((sum / total) * 10) / 10;
}
function subjectDistributionRows(local){
  return localFilterRows(local.distribution || [])
    .filter(r => rowGroup(r) === (state.filters.group === 'Alla' ? 'Alla' : state.filters.group))
    .filter(r => state.filters.gender === 'Alla' ? rowGender(r) === 'Alla' : true)
    .filter(r => Number(r.antal_betyg) > 0)
    .map(r => ({...r, betygspoang: gradePointAverage(r)}))
    .sort((a,b) => `${a.arskurs}${schoolLabel(a)}${rowGender(a)}${rowGroup(a)}${a.amne}`.localeCompare(`${b.arskurs}${schoolLabel(b)}${rowGender(b)}${rowGroup(b)}${b.amne}`, 'sv', {numeric:true}));
}
function renderLocalOutcomes(local, meritRows){
  const outcomeRows = meritRows
    .filter(r => r.andel_uppnatt_alla_amnen != null)
    .sort((a,b) => `${a.arskurs}${schoolLabel(a)}${rowGender(a)}${rowGroup(a)}`.localeCompare(`${b.arskurs}${schoolLabel(b)}${rowGender(b)}${rowGroup(b)}`, 'sv', {numeric:true}));
  $('knowledgeRows').innerHTML = outcomeRows.map(r => `<tr><td>${esc(r.arskurs)}</td><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.elevgrupp || 'Alla')}</td><td>${esc(r.antal_elever ?? '-')}</td><td>${fmt(r.andel_uppnatt_alla_amnen, ' %')}</td></tr>`).join('') || '<tr><td colspan="6" class="muted">Ingen data för uppnått alla ämnen matchar urvalet.</td></tr>';
  const knowledgeChartRows = outcomeRows
    .filter(r => (state.filters.gender === 'Alla' ? rowGender(r) === 'Alla' : rowGender(r) === state.filters.gender))
    .filter(r => (state.filters.group === 'Alla' ? rowGroup(r) === 'Alla' : rowGroup(r) === state.filters.group))
    .slice(0, 18);
  makeChart('knowledgeChart','bar',{
    labels: knowledgeChartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)}`),
    datasets:[{label:'Uppnått alla ämnen %', data:knowledgeChartRows.map(r => r.andel_uppnatt_alla_amnen), backgroundColor:'#347f6a'}]
  },{scales:{y:{beginAtZero:true,max:100}}});

  const vocationalRows = localFilterRows(local.overview || [], {forceGrade:9})
    .filter(r => r.andel_behoriga_yrkesprogram != null)
    .sort((a,b) => `${schoolLabel(a)}${rowGender(a)}${rowGroup(a)}`.localeCompare(`${schoolLabel(b)}${rowGender(b)}${rowGroup(b)}`, 'sv', {numeric:true}));
  $('vocationalRows').innerHTML = vocationalRows.map(r => `<tr><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.elevgrupp || 'Alla')}</td><td>${esc(r.antal_elever ?? '-')}</td><td>${fmt(r.andel_behoriga_yrkesprogram, ' %')}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">Ingen yrkesbehörighetsdata för åk 9 matchar urvalet.</td></tr>';
  const vocationalChartRows = vocationalRows
    .filter(r => (state.filters.gender === 'Alla' ? rowGender(r) === 'Alla' : rowGender(r) === state.filters.gender))
    .filter(r => (state.filters.group === 'Alla' ? rowGroup(r) === 'Alla' : rowGroup(r) === state.filters.group))
    .slice(0, 12);
  makeChart('vocationalChart','bar',{
    labels: vocationalChartRows.map(r => schoolLabel(r)),
    datasets:[{label:'Yrkesbehörighet åk 9 %', data:vocationalChartRows.map(r => r.andel_behoriga_yrkesprogram), backgroundColor:'#2f6f9f'}]
  },{scales:{y:{beginAtZero:true,max:100}}});
}
function renderLocalControl(local){
  const controlRows = localFilterRows(local.control || [])
    .filter(r => rowGroup(r) === (state.filters.group === 'Alla' ? 'Alla' : state.filters.group))
    .sort((a,b) => `${a.arskurs}${schoolLabel(a)}${a.elevgrupp}${a.amne}`.localeCompare(`${b.arskurs}${schoolLabel(b)}${b.elevgrupp}${b.amne}`, 'sv', {numeric:true}));

  $('controlRows').innerHTML = controlRows.slice(0, 180).map(r => `<tr><td>${esc(r.arskurs)}</td><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.elevgrupp || 'Alla')}</td><td>${esc(r.amne)}</td><td>${esc(r.antal_elever)}</td><td>${esc(r.antal_giltiga_betyg)}</td><td>${esc(r.antal_A_E)}</td><td>${esc(r.antal_F)}</td><td>${esc(r.antal_tomma)}</td><td>${esc(r.antal_specialkoder)}</td><td>${esc(r.antal_ogiltiga_koder)}</td><td>${esc(r.specialkod_2)}</td><td>${esc(r.specialkod_3)}</td><td>${esc(r.specialkod_9)}</td><td>${esc(r.specialkod_Y)}</td><td>${esc(r.specialkod_Z)}</td></tr>`).join('') || '<tr><td colspan="16" class="muted">Ingen kontrolldata matchar urvalet.</td></tr>';

  const topRows = controlRows.filter(r => r.elevgrupp === 'Alla').slice(0, 18);
  makeChart('controlChart','bar',{
    labels: topRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)} ${r.amne}`),
    datasets:[
      {label:'Giltiga betyg', data:topRows.map(r => r.antal_giltiga_betyg), backgroundColor:'#2f6f9f'},
      {label:'Tomma', data:topRows.map(r => r.antal_tomma), backgroundColor:'#9aa6ad'},
      {label:'Specialkoder', data:topRows.map(r => r.antal_specialkoder), backgroundColor:'#b86b1d'},
      {label:'Ogiltiga koder', data:topRows.map(r => r.antal_ogiltiga_koder), backgroundColor:'#b73535'}
    ]
  },{scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true}}});
}
function renderFilteredLocal(){
  const local = state.local;
  if(!local) return;

  const meritRows = localFilterRows(local.overview || []);
  const cardBase = localFilterRows(local.overview || [], {allowAllLevel:true}).find(r => r.niva === 'alla_skolenheter' && Number(r.arskurs) === 9 && rowGender(r) === 'Alla' && rowGroup(r) === 'Alla')
    || localFilterRows(local.overview || [], {allowAllLevel:true}).find(r => r.niva === 'alla_skolenheter' && rowGender(r) === 'Alla' && rowGroup(r) === 'Alla')
    || meritRows[0] || {};
  $('meritCard').textContent = fmt(cardBase.genomsnittligt_meritvarde_17 || cardBase.genomsnittligt_meritvarde_16);
  $('vocCard').textContent = cardBase.andel_behoriga_yrkesprogram == null ? '-' : fmt(cardBase.andel_behoriga_yrkesprogram, ' %');

  $('localMeritRows').innerHTML = meritRows
    .sort((a,b) => `${a.arskurs}${schoolLabel(a)}${rowGender(a)}${rowGroup(a)}`.localeCompare(`${b.arskurs}${schoolLabel(b)}${rowGender(b)}${rowGroup(b)}`, 'sv', {numeric:true}))
    .map(r => `<tr><td>${esc(r.arskurs)}</td><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.elevgrupp || 'Alla')}</td><td>${esc(r.antal_elever ?? '-')}</td><td>${fmt(r.genomsnittligt_meritvarde_16)}</td><td>${fmt(r.genomsnittligt_meritvarde_17)}</td><td>${fmt(r.andel_uppnatt_alla_amnen, ' %')}</td><td>${r.andel_behoriga_yrkesprogram == null ? '-' : fmt(r.andel_behoriga_yrkesprogram, ' %')}</td></tr>`)
    .join('') || '<tr><td colspan="9" class="muted">Inga rader matchar urvalet.</td></tr>';

  const chartRows = meritRows.filter(r => rowGender(r) === 'Alla' && rowGroup(r) === 'Alla');
  makeChart('overviewChart','bar',{
    labels: chartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)}`),
    datasets:[
      {label:'Meritvärde 17', data:chartRows.map(r => r.genomsnittligt_meritvarde_17), backgroundColor:'#2f6f9f'},
      {label:'Yrkesbehörighet %', data:chartRows.map(r => r.andel_behoriga_yrkesprogram), backgroundColor:'#347f6a'}
    ]
  },{scales:{y:{beginAtZero:false}}});

  const genderSource = localBaseFilter(local.overview || []).filter(r => rowGroup(r) === (state.filters.group === 'Alla' ? 'Alla' : state.filters.group));
  const genderGroups = {};
  for(const row of genderSource){
    const key = `${row.arskurs}|${schoolKey(row)}|${row.elevgrupp || 'Alla'}`;
    genderGroups[key] ||= {arskurs:row.arskurs, school:schoolLabel(row), elevgrupp:row.elevgrupp || 'Alla'};
    genderGroups[key][row.kon || 'Alla'] = row;
  }
  const genderRows = Object.values(genderGroups).sort((a,b) => `${a.arskurs}${a.school}${a.elevgrupp}`.localeCompare(`${b.arskurs}${b.school}${b.elevgrupp}`, 'sv', {numeric:true}));
  $('genderRows').innerHTML = genderRows.map(g => {
    const boys = g.Pojkar?.genomsnittligt_meritvarde_17;
    const girls = g.Flickor?.genomsnittligt_meritvarde_17;
    const diff = Number(girls) - Number(boys);
    return `<tr><td>${esc(g.arskurs)}</td><td><strong>${esc(g.school)}</strong></td><td>${esc(g.elevgrupp)}</td><td>${fmt(boys)}</td><td>${fmt(girls)}</td><td>${fmt(g.Alla?.genomsnittligt_meritvarde_17)}</td><td>${Number.isFinite(diff) ? fmt(diff) : '-'}</td></tr>`;
  }).join('') || '<tr><td colspan="7" class="muted">Ingen könsuppdelad meritdata matchar urvalet.</td></tr>';
  const genderChartRows = genderRows.slice(0, 12);
  makeChart('genderChart','bar',{
    labels: genderChartRows.map(r => `Åk ${r.arskurs} ${r.school}`),
    datasets:[
      {label:'Pojkar merit 17', data:genderChartRows.map(r => r.Pojkar?.genomsnittligt_meritvarde_17), backgroundColor:'#2f6f9f'},
      {label:'Flickor merit 17', data:genderChartRows.map(r => r.Flickor?.genomsnittligt_meritvarde_17), backgroundColor:'#8a5a96'}
    ]
  },{scales:{y:{beginAtZero:false}}});

  const svSvaRows = localFilterRows(local.svSva || []).filter(r => ['SV','SVA'].includes(r.elevgrupp));
  $('svaRows').innerHTML = svSvaRows.map(r => `<tr><td>${esc(r.arskurs)}</td><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.elevgrupp)}</td><td>${esc(r.antal_elever ?? '-')}</td><td>${fmt(r.genomsnittligt_meritvarde_17)}</td><td>${fmt(r.andel_godkand_sv_sva, ' %')}</td><td>${fmt(r.andel_uppnatt_alla_amnen, ' %')}</td></tr>`).join('') || '<tr><td colspan="7" class="muted">Ingen SV/SVA-data hittades för urvalet.</td></tr>';

  const subjectRows = subjectDistributionRows(local);
  $('subjectRows').innerHTML = subjectRows.slice(0, 180).map(r => `<tr><td>${esc(r.arskurs)}</td><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.elevgrupp || 'Alla')}</td><td>${esc(r.amne)}</td><td>${fmt(r.betygspoang)}</td><td>${esc(r.antal_A ?? 0)}</td><td>${esc(r.antal_B ?? 0)}</td><td>${esc(r.antal_C ?? 0)}</td><td>${esc(r.antal_D ?? 0)}</td><td>${esc(r.antal_E ?? 0)}</td><td>${esc(r.antal_F ?? 0)}</td><td>${fmt(r.andel_A_E, ' %')}</td><td>${esc(r.antal_betyg)}</td></tr>`).join('') || '<tr><td colspan="14" class="muted">Ingen ämnesdata matchar urvalet.</td></tr>';
  const topSubjects = subjectRows.slice(0, 24);
  makeChart('subjectChart','bar',{
    labels: topSubjects.map(r => `Åk ${r.arskurs} ${schoolLabel(r)} ${r.amne}`),
    datasets:[
      {label:'Betygspoäng', data:topSubjects.map(r => r.betygspoang), backgroundColor:'#2f6f9f', yAxisID:'y'},
      {label:'Andel F %', data:topSubjects.map(r => r.andel_F), backgroundColor:'#b73535', yAxisID:'y1'}
    ]
  },{scales:{y:{beginAtZero:true,max:20},y1:{beginAtZero:true,max:100,position:'right',grid:{drawOnChartArea:false}}}});

  $('gradeDistRows').innerHTML = subjectRows.slice(0, 180).map(r => `<tr><td>${esc(r.arskurs)}</td><td><strong>${esc(schoolLabel(r))}</strong></td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.elevgrupp || 'Alla')}</td><td>${esc(r.amne)}</td><td>${fmt(r.andel_A, ' %')}</td><td>${fmt(r.andel_B, ' %')}</td><td>${fmt(r.andel_C, ' %')}</td><td>${fmt(r.andel_D, ' %')}</td><td>${fmt(r.andel_E, ' %')}</td><td>${fmt(r.andel_F, ' %')}</td><td>${esc(r.antal_betyg)}</td></tr>`).join('') || '<tr><td colspan="12" class="muted">Ingen betygsfördelning matchar urvalet.</td></tr>';
  const gradeChartRows = subjectRows.slice(0, 18);
  makeChart('gradeDistChart','bar',{
    labels: gradeChartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)} ${r.amne}`),
    datasets:[
      {label:'A %', data:gradeChartRows.map(r => r.andel_A), backgroundColor:'#1f5f7a'},
      {label:'B %', data:gradeChartRows.map(r => r.andel_B), backgroundColor:'#2f6f9f'},
      {label:'C %', data:gradeChartRows.map(r => r.andel_C), backgroundColor:'#347f6a'},
      {label:'D %', data:gradeChartRows.map(r => r.andel_D), backgroundColor:'#8a7a35'},
      {label:'E %', data:gradeChartRows.map(r => r.andel_E), backgroundColor:'#b86b1d'},
      {label:'F %', data:gradeChartRows.map(r => r.andel_F), backgroundColor:'#b73535'}
    ]
  },{scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,max:100}}});

  renderLocalOutcomes(local, meritRows);
  renderLocalControl(local);
  renderLocalNp(local);
}
function renderLocalNp(local){
  const f = state.filters;
  const npFilter = r => {
    if(f.grades.length && !f.grades.includes(String(r.arskurs ?? ''))) return false;
    if(f.gender !== 'Alla' && rowGender(r) !== f.gender) return false;
    if(f.gender === 'Alla' && rowGender(r) !== 'Alla') return false;
    if(r.niva === 'kommun') return true;
    return r.niva === 'skolenhet' && (!f.schools.length || f.schools.includes(schoolKey(r)));
  };
  const npPass = (local.npPass || []).filter(npFilter);
  const npRelation = (local.npRelation || []).filter(npFilter);
  const passRows = npPass.sort((a,b) => `${a.niva}${a.skolenhetsnamn}${a.arskurs}${a.amne}`.localeCompare(`${b.niva}${b.skolenhetsnamn}${b.arskurs}${b.amne}`, 'sv'));
  const relationRows = npRelation.sort((a,b) => `${a.niva}${a.skolenhetsnamn}${a.arskurs}${a.amne}`.localeCompare(`${b.niva}${b.skolenhetsnamn}${b.arskurs}${b.amne}`, 'sv'));

  $('npLocalRows').innerHTML = passRows.map(r => `<tr><td><strong>${esc(r.skolenhetsnamn || r.skolenhetskod || r.niva)}</strong></td><td>${esc(r.arskurs)}</td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.amne)}</td><td>${esc(r.antal_np)}</td><td>${fmt(r.andel_godkanda_np, ' %')}</td><td>${esc(r.antal_med_betygsmatch ?? '-')}</td></tr>`).join('') || '<tr><td colspan="7" class="muted">Ingen lokal NP-data hittades.</td></tr>';
  $('npRelationRows').innerHTML = relationRows.map(r => `<tr><td><strong>${esc(r.skolenhetsnamn || r.skolenhetskod || r.niva)}</strong></td><td>${esc(r.arskurs)}</td><td>${esc(r.kon || 'Alla')}</td><td>${esc(r.amne)}</td><td>${esc(r.antal_jamforda)}</td><td>${fmt(r.andel_betyg_hogre_an_np, ' %')}</td><td>${fmt(r.andel_betyg_lika_np, ' %')}</td><td>${fmt(r.andel_betyg_lagre_an_np, ' %')}</td></tr>`).join('') || '<tr><td colspan="8" class="muted">Ingen betyg-NP-relation kunde beräknas.</td></tr>';

  const topPass = passRows.filter(r => r.niva === 'kommun').slice(0, 12);
  makeChart('npPassChart','bar',{
    labels: topPass.map(r => `Åk ${r.arskurs} ${r.kon || 'Alla'} ${r.amne}`),
    datasets:[{label:'Andel godkända NP %', data:topPass.map(r => r.andel_godkanda_np), backgroundColor:'#347f6a'}]
  },{scales:{y:{beginAtZero:true,max:100}}});

  const topRelation = relationRows.filter(r => r.niva === 'kommun').slice(0, 12);
  makeChart('npRelationChart','bar',{
    labels: topRelation.map(r => `Åk ${r.arskurs} ${r.kon || 'Alla'} ${r.amne}`),
    datasets:[
      {label:'Betyg > NP %', data:topRelation.map(r => r.andel_betyg_hogre_an_np), backgroundColor:'#b86b1d'},
      {label:'Betyg = NP %', data:topRelation.map(r => r.andel_betyg_lika_np), backgroundColor:'#347f6a'},
      {label:'Betyg < NP %', data:topRelation.map(r => r.andel_betyg_lagre_an_np), backgroundColor:'#2f6f9f'}
    ]
  },{scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,max:100}}});
}
function renderLocalData(local){
  state.local = local;
  $('demoNotice').style.display = local.isDemo ? 'block' : 'none';
  state.tables = [];
  state.metrics = [
    {key:'localScb', label:local.isDemo ? 'Demodata' : 'Lokal SCB-import', status:'ok', reason:`${local.manifest.arskurser?.map(a => `åk ${a.arskurs}: ${a.rows}`).join(', ') || 'data finns'}`}
  ];
  $('tableCount').textContent = local.manifest.files?.length || 0;
  $('metricCount').textContent = 'lokal';
  renderMetricRows();
  populateLocalFilters(local);
  renderFilteredLocal();
  $('npRows').innerHTML = '<tr><td colspan="4" class="muted">PxWeb-fallback används inte när lokal SCB-import är laddad.</td></tr>';
  const hasSvSvaRows = (local.svSva || []).some(r => ['SV','SVA'].includes(r.elevgrupp));
  $('availabilityRows').innerHTML = [
    [local.isDemo ? 'Demodata' : local.sourceKind === 'processed' ? 'Bearbetad publiceringsdata' : 'Årets SCB-betyg', 'OK', `Läst från ${local.base}`],
    ['SV/SVA-jämförelse', hasSvSvaRows ? 'OK' : 'Ej hittad', 'Beräknas från Sv/Sva-kolumnerna.'],
    ['Kontroll antal betyg och specialkoder', (local.control || []).length ? 'OK' : 'Ej hittad', 'Bygger på lokal SCB-import och visar giltiga betyg, tomma värden och specialkoder per ämne.'],
    ['NP andel godkända', (local.npPass || []).length ? 'OK' : 'Ej hittad', 'Beräknas från lokal NP-import per kommun och skolenhet.'],
    ['Relation betyg och NP', (local.npRelation || []).length ? 'OK' : 'Ej hittad', 'Kräver både betygsfil och NP-fil med matchande elev/skolenhet.'],
    ['PxWeb/Kolada fallback', 'Ej använd', 'Lokal SCB-import hittades och används som primär källa.']
  ].map(r => `<tr><td><strong>${esc(r[0])}</strong></td><td class="${r[1] === 'OK' ? 'ok' : 'warn'}">${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`).join('');
  $('tableRows').innerHTML = (local.manifest.files || []).map(f => `<tr><td><strong>${esc(f.file)}</strong></td><td class="ok">läst</td><td>${esc(f.rows)} rader</td></tr>`).join('') || '<tr><td colspan="3" class="muted">Manifestet innehåller inga filrader.</td></tr>';
  log('Lokal SCB-import används', local.manifest);
  setStatus(local.isDemo ? 'warn' : 'ok', local.isDemo ? 'Demodata laddad.' : 'Lokal SCB-import laddad.', `${local.isDemo ? 'Visar anonym testdata' : 'Visar anonymiserad statistik'} från ${local.base}.`);
}
