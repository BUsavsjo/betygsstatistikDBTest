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
function subjectLabel(row){
  return row.amnesnamn || row.amne || '-';
}
const subjectOrder = {
  Bl: 10,
  Sv: 20,
  Sva: 21,
  En: 30,
  M1_betyg: 31,
  M2_betyg: 32,
  ML_betyg: 33,
  Modmalbe: 34,
  Ma: 40,
  Hkk: 50,
  Idh: 60,
  Mu: 70,
  Sl: 80,
  Bi: 90,
  Fy: 91,
  Ke: 92,
  No: 93,
  Ge: 100,
  Hi: 101,
  Re: 102,
  Sh: 103,
  So: 104,
  Tk: 110,
  Tn: 111,
  Ovr: 120
};
function subjectSortValue(row){
  return subjectOrder[row.amne] ?? 999;
}
function schoolLabel(row){
  if(row.niva === 'alla_skolenheter' || row.niva === 'kommun') return 'Alla skolenheter';
  return row.skolenhetsnamn || row.skolenhetskod || 'Okänd skolenhet';
}
function schoolKey(row){
  return row.niva === 'alla_skolenheter' || row.niva === 'kommun' ? '__all__' : String(row.skolenhetskod || '');
}
function normalizedSchoolName(value){
  return norm(value).replace(/\s+/g, ' ');
}
function selectedOnlyGrade3(){
  const grades = state.filters?.grades || [];
  return grades.length === 1 && Number(grades[0]) === 3;
}
function schoolSupportedGrades(school){
  if(Array.isArray(school.supportedGrades) && school.supportedGrades.length) return school.supportedGrades.map(String);
  const name = normalizedSchoolName(school.label || school.skolenhetsnamn || '');
  if(name.includes('hofgard')) return ['9'];
  if(name.includes('rorvik')) return ['3', '6', '9'];
  return ['3', '6'];
}
function schoolSupportsGrades(school, grades){
  const supported = school.supportedGrades || schoolSupportedGrades(school);
  const wantedGrades = (grades || []).map(String);
  return !wantedGrades.length || wantedGrades.some(g => supported.includes(g));
}
function schoolSupportsRowGrade(row){
  if(row.niva !== 'skolenhet') return true;
  return schoolSupportsGrades({label: schoolLabel(row)}, [String(row.arskurs ?? '')]);
}
function updateFilterState(resetSchoolsForGrade=false){
  const grades = selectedValues('gradeFilter');
  let schools = selectedValues('schoolFilter');
  if(state.localSchools?.length){
    const availableSchools = state.localSchools.filter(s => schoolSupportsGrades(s, grades)).map(s => String(s.value));
    schools = resetSchoolsForGrade ? availableSchools : schools.filter(s => availableSchools.includes(String(s)));
    if(!schools.length) schools = availableSchools;
  }
  state.filters = {
    grades,
    schools,
    gender: $('genderFilter').value || 'Alla',
    group: $('groupFilter').value || 'Alla'
  };
  if(state.localSchools?.length) populateSchoolFilter();
}
function populateSelect(id, options, selectedValues){
  const selected = new Set(selectedValues || []);
  $(id).innerHTML = options.map(o => `<option value="${esc(o.value)}"${selected.has(String(o.value)) ? ' selected' : ''}>${esc(o.label)}</option>`).join('');
}
function populateSchoolFilter(){
  const selected = new Set(state.filters.schools || []);
  const grades = state.filters.grades || [];
  $('schoolFilter').innerHTML = (state.localSchools || []).map(s => {
    const available = schoolSupportsGrades(s, grades);
    const gradeLabel = s.supportedGrades?.length ? ` (åk ${s.supportedGrades.join(', ')})` : '';
    const selectedAttr = available && selected.has(String(s.value)) ? ' selected' : '';
    const disabledAttr = available ? '' : ' disabled';
    return `<option value="${esc(s.value)}"${selectedAttr}${disabledAttr}>${esc(s.label + gradeLabel)}</option>`;
  }).join('');
}
function populateLocalFilters(local){
  const overview = local.overview || [];
  const npGrades = uniqueSorted((local.npPass || []).map(r => r.arskurs));
  const grades = uniqueSorted([...overview.map(r => r.arskurs), ...npGrades]);
  const schoolRows = [
    ...overview.filter(r => r.niva === 'skolenhet'),
    ...(local.npPass || []).filter(r => r.niva === 'skolenhet')
  ];
  const schools = uniqueSorted(schoolRows.map(r => schoolKey(r))).map(code => {
    const rowsForSchool = schoolRows.filter(r => schoolKey(r) === code);
    const row = rowsForSchool[0];
    const label = schoolLabel(row);
    const supportedGrades = uniqueSorted(rowsForSchool.map(r => r.arskurs));
    return {value: code, label, supportedGrades};
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
  state.localSchools = schools;

  populateSelect('gradeFilter', grades.map(g => ({value:g, label:`Åk ${g}`})), state.filters.grades);
  populateSchoolFilter();
  $('genderFilter').innerHTML = '<option value="Alla">Alla</option>' + genders.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
  $('groupFilter').innerHTML = '<option value="Alla">Alla</option>' + groups.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
  $('localFilters').classList.add('active');
  updateTabVisibility();
}
function updateTabVisibility(){
  const npOnlyMode = selectedOnlyGrade3();
  const hiddenTabs = new Set(npOnlyMode ? ['overview', 'gender', 'subjects', 'grades', 'control', 'outcomes'] : []);
  document.querySelectorAll('.tab').forEach(tab => {
    const hidden = hiddenTabs.has(tab.dataset.tab);
    tab.style.display = hidden ? 'none' : '';
  });
  if(npOnlyMode){
    const activeTab = document.querySelector('.tab.active');
    if(activeTab && hiddenTabs.has(activeTab.dataset.tab)){
      const npTab = document.querySelector('[data-tab="np"]');
      if(npTab) npTab.click();
    }
  }
}
function rowGender(row){ return row.kon || 'Alla'; }
function rowGroup(row){ return row.elevgrupp || 'Alla'; }
function isAggregateLevel(row){
  return row?.niva === 'alla_skolenheter' || row?.niva === 'kommun';
}
function localFilterRows(rows, {allowAllLevel=false, includeAggregateRow=false, forceGrade=null}={}){
  const f = state.filters;
  return (rows || []).filter(r => {
    const gradeValue = String(r.arskurs ?? '');
    if(forceGrade && Number(r.arskurs) !== Number(forceGrade)) return false;
    if(f.grades.length && !f.grades.includes(gradeValue)) return false;
    if(f.gender !== 'Alla' && rowGender(r) !== f.gender) return false;
    if(f.group !== 'Alla' && rowGroup(r) !== f.group) return false;
    if((allowAllLevel || includeAggregateRow) && isAggregateLevel(r)) return true;
    if(!schoolSupportsRowGrade(r)) return false;
    return r.niva === 'skolenhet' && (!f.schools.length || f.schools.includes(schoolKey(r)));
  });
}
function localBaseFilter(rows, {includeAggregateRow=false, forceGrade=null}={}){
  const f = state.filters;
  return (rows || []).filter(r => {
    if(forceGrade && Number(r.arskurs) !== Number(forceGrade)) return false;
    if(f.grades.length && !f.grades.includes(String(r.arskurs ?? ''))) return false;
    if(f.group !== 'Alla' && rowGroup(r) !== f.group) return false;
    if(includeAggregateRow && isAggregateLevel(r)) return true;
    if(!schoolSupportsRowGrade(r)) return false;
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
function groupConsecutiveRows(rows, keyFn){
  const groups = [];
  for(const row of rows || []){
    const key = keyFn(row);
    const last = groups[groups.length - 1];
    if(last && last.key === key){
      last.rows.push(row);
      continue;
    }
    groups.push({key, rows:[row]});
  }
  return groups;
}
function selectedSchoolSummary(){
  const count = (state.filters?.schools || []).length;
  return count ? `${count} skolenheter` : 'Alla skolenheter';
}
function currentTableSummary({groupLabel='Elevgrupp'}={}){
  const grades = state.filters?.grades || [];
  const gradeText = grades.length ? grades.map(g => `Årskurs: ${g}`).join(', ') : 'Årskurs: Alla';
  const genderText = `Kön: ${state.filters?.gender || 'Alla'}`;
  const groupText = `${groupLabel}: ${state.filters?.group || 'Alla'}`;
  const schoolText = `Skolor: ${selectedSchoolSummary()}`;
  return `${gradeText} · ${genderText} · ${groupText} · ${schoolText}`;
}
function selectedGradeValues(){
  return (state.filters?.grades || []).map(v => Number(v)).filter(Number.isFinite);
}
function setTableSummary(id, summary){
  const el = $(id);
  if(el) el.innerHTML = `<strong>Urval:</strong> ${esc(summary)}`;
}
function showGradeCell(value){
  return (state.filters?.grades || []).length === 1 ? '' : esc(value);
}
function showGenderCell(value){
  return esc(value || 'Alla');
}
function showGroupCell(value){
  return state.filters?.group !== 'Alla' ? '' : esc(value || 'Alla');
}
function rightCell(value){
  return `<td class="numeric">${esc(value ?? '-')}</td>`;
}
function schoolCellHtml(row, span){
  return `<td rowspan="${span}" class="school-cell"><strong>${esc(schoolLabel(row))}</strong></td>`;
}
function renderSchoolGroupedBody(rows, {emptyHtml, colspan, schoolCell, rowCells}){
  if(!rows.length) return emptyHtml;
  return groupConsecutiveRows(rows, row => schoolKey(row)).map(group => {
    return group.rows.map((row, index) => {
      const cells = rowCells(row, index, group.rows.length);
      const schoolHtml = index === 0 ? schoolCell(row, group.rows.length) : '';
      return `<tr class="school-group${index === 0 ? ' school-group-start' : ''}">${cells.beforeSchool || ''}${schoolHtml}${cells.afterSchool || ''}</tr>`;
    }).join('');
  }).join('') || `<tr><td colspan="${colspan}" class="muted">Inga rader matchar urvalet.</td></tr>`;
}
function subjectDistributionRows(local, {includeAggregateRow=false}={}){
  return localFilterRows(local.distribution || [], {includeAggregateRow})
    .filter(r => rowGroup(r) === (state.filters.group === 'Alla' ? 'Alla' : state.filters.group))
    .filter(r => state.filters.gender === 'Alla' ? rowGender(r) === 'Alla' : true)
    .filter(r => Number(r.antal_betyg) > 0)
    .map(r => ({...r, betygspoang: gradePointAverage(r)}))
    .sort((a,b) =>
      `${schoolLabel(a)}${a.arskurs}${rowGender(a)}${rowGroup(a)}${String(subjectSortValue(a)).padStart(3, '0')}${subjectLabel(a)}`
        .localeCompare(
          `${schoolLabel(b)}${b.arskurs}${rowGender(b)}${rowGroup(b)}${String(subjectSortValue(b)).padStart(3, '0')}${subjectLabel(b)}`,
          'sv',
          {numeric:true},
        ));
}
function renderLocalOutcomes(local, meritRows, {hideAggregateOutcome=false}={}){
  const viewConfig = getGradeViewConfig(selectedSingleGrade());
  $('outcomesTitle').textContent = viewConfig.title || viewConfig.labels.uppnatt_alla_amnen;
  $('outcomesDescription').textContent = viewConfig.description || '';
  $('outcomesDescription').style.display = viewConfig.description ? 'block' : 'none';
  $('knowledgeMetricHeader').innerHTML = infoLabel(viewConfig.labels.uppnatt_alla_amnen, viewConfig.tooltips.uppnatt_alla_amnen);
  $('knowledgeBoxTitle').textContent = viewConfig.labels.uppnatt_alla_amnen;
  const outcomeRows = localFilterRows(local.overview || [], {includeAggregateRow:true})
    .filter(r => r.andel_uppnatt_alla_amnen != null)
    .sort((a,b) => `${schoolLabel(a)}${a.arskurs}${rowGender(a)}${rowGroup(a)}`.localeCompare(`${schoolLabel(b)}${b.arskurs}${rowGender(b)}${rowGroup(b)}`, 'sv', {numeric:true}));
  const totalOutcome = localFilterRows(local.overview || [], {allowAllLevel:true})
    .find(r => r.niva === 'alla_skolenheter' && rowGender(r) === 'Alla' && rowGroup(r) === 'Alla' && r.andel_uppnatt_alla_amnen != null);
  $('knowledgeTotalCard').textContent = hideAggregateOutcome || totalOutcome?.andel_uppnatt_alla_amnen == null ? '-' : fmt(totalOutcome.andel_uppnatt_alla_amnen, ' %');
  $('knowledgeTotalSub').textContent = hideAggregateOutcome
    ? 'Döljs när flera årskurser är valda'
    : totalOutcome
      ? `${totalOutcome.antal_elever} elever · alla skolenheter`
      : 'Alla skolenheter';
  setTableSummary('knowledgeTableSummary', currentTableSummary());
  $('knowledgeRows').innerHTML = renderSchoolGroupedBody(outcomeRows, {
    colspan: 6,
    emptyHtml: '<tr><td colspan="6" class="muted">Ingen data för uppnått alla ämnen matchar urvalet.</td></tr>',
    schoolCell: schoolCellHtml,
    rowCells: row => ({
      beforeSchool: `<td>${showGradeCell(row.arskurs)}</td>`,
      afterSchool: `<td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td class="numeric">${studentCountCell(row.antal_elever)}</td><td>${pctBar(row.andel_uppnatt_alla_amnen, formatPercentWithCount(row.andel_uppnatt_alla_amnen, row.antal_elever))}</td>`
    })
  });
  const knowledgeChartRows = outcomeRows
    .filter(r => (state.filters.gender === 'Alla' ? rowGender(r) === 'Alla' : rowGender(r) === state.filters.gender))
    .filter(r => (state.filters.group === 'Alla' ? rowGroup(r) === 'Alla' : rowGroup(r) === state.filters.group))
    .slice(0, 18);
  $('knowledgeTotalCard').closest('.card').style.display = hideAggregateOutcome ? 'none' : '';
  $('knowledgeChart').closest('.box').style.display = hideAggregateOutcome ? 'none' : '';
  if(!hideAggregateOutcome){
    makeChart('knowledgeChart','bar',{
      labels: knowledgeChartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)}`),
      datasets:[{label:`${viewConfig.labels.uppnatt_alla_amnen} %`, data:knowledgeChartRows.map(r => r.andel_uppnatt_alla_amnen), backgroundColor:'#347f6a'}]
    },{scales:{y:{beginAtZero:true,max:100}}});
  }

  const vocationalRows = localFilterRows(local.overview || [], {includeAggregateRow:true, forceGrade:9})
    .filter(r => r.andel_behoriga_yrkesprogram != null)
    .sort((a,b) => `${schoolLabel(a)}${rowGender(a)}${rowGroup(a)}`.localeCompare(`${schoolLabel(b)}${rowGender(b)}${rowGroup(b)}`, 'sv', {numeric:true}));
  setTableSummary('vocationalTableSummary', currentTableSummary());
  $('vocationalRows').innerHTML = renderSchoolGroupedBody(vocationalRows, {
    colspan: 5,
    emptyHtml: '<tr><td colspan="5" class="muted">Ingen yrkesbehörighetsdata för åk 9 matchar urvalet.</td></tr>',
    schoolCell: schoolCellHtml,
    rowCells: row => ({
      afterSchool: `<td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td class="numeric">${studentCountCell(row.antal_elever)}</td><td>${pctBar(row.andel_behoriga_yrkesprogram, formatPercentWithCount(row.andel_behoriga_yrkesprogram, row.antal_elever))}</td>`
    })
  });
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
  const controlRows = localFilterRows(local.control || [], {includeAggregateRow:true})
    .filter(r => rowGroup(r) === (state.filters.group === 'Alla' ? 'Alla' : state.filters.group))
    .sort((a,b) => `${schoolLabel(a)}${a.arskurs}${a.elevgrupp}${a.amne}`.localeCompare(`${schoolLabel(b)}${b.arskurs}${b.elevgrupp}${b.amne}`, 'sv', {numeric:true}));

  setTableSummary('controlTableSummary', currentTableSummary());
  $('controlRows').innerHTML = renderSchoolGroupedBody(controlRows.slice(0, 180), {
    colspan: 17,
    emptyHtml: '<tr><td colspan="17" class="muted">Ingen kontrolldata matchar urvalet.</td></tr>',
    schoolCell: schoolCellHtml,
    rowCells: row => ({
      beforeSchool: `<td>${showGradeCell(row.arskurs)}</td>`,
      afterSchool: `<td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td>${esc(subjectLabel(row))}</td>${rightCell(row.antal_elever)}${rightCell(row.antal_giltiga_betyg)}${rightCell(row.antal_A_E)}${rightCell(row.antal_F)}${rightCell(row.antal_tomma)}${rightCell(row.antal_specialkoder)}${rightCell(row.antal_ogiltiga_koder)}${rightCell(row.specialkod_2)}${rightCell(row.specialkod_3)}${rightCell(row.specialkod_9)}${rightCell(row.specialkod_Y)}${rightCell(row.specialkod_Z)}`
    })
  });

  const topRows = controlRows.filter(r => r.elevgrupp === 'Alla').slice(0, 18);
  makeChart('controlChart','bar',{
    labels: topRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)} ${subjectLabel(r)}`),
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
  updateTabVisibility();

  const meritRows = localFilterRows(local.overview || []);
  const tableMeritRows = localFilterRows(local.overview || [], {includeAggregateRow:true});
  const selectedGrade = selectedSingleGrade();
  const selectedGrades = selectedGradeValues();
  const viewConfig = getGradeViewConfig(selectedGrade);
  const showOverviewMerit = !(selectedGrade != null && Number(selectedGrade) === 6);
  const showVocational = selectedGrade == null || Number(selectedGrade) === 9;
  const meritCardBox = $('meritCard').closest('.card');
  const vocCardBox = $('vocCard').closest('.card');
  const overviewChartBox = $('overviewChart').closest('.box');
  const overviewVocationalChartBox = $('vocOverviewChart')?.closest('.box');
  const cardBase = localFilterRows(local.overview || [], {allowAllLevel:true}).find(r => r.niva === 'alla_skolenheter' && Number(r.arskurs) === 9 && rowGender(r) === 'Alla' && rowGroup(r) === 'Alla')
    || localFilterRows(local.overview || [], {allowAllLevel:true}).find(r => r.niva === 'alla_skolenheter' && rowGender(r) === 'Alla' && rowGroup(r) === 'Alla')
    || meritRows[0] || {};
  $('meritCard').textContent = showOverviewMerit ? fmt(cardBase.genomsnittligt_meritvarde_17 || cardBase.genomsnittligt_meritvarde_16) : '-';
  $('vocCard').textContent = showVocational && cardBase.andel_behoriga_yrkesprogram != null ? fmt(cardBase.andel_behoriga_yrkesprogram, ' %') : '-';
  meritCardBox.style.display = showOverviewMerit ? '' : 'none';
  vocCardBox.style.display = showVocational && showOverviewMerit ? '' : 'none';
  overviewChartBox.style.display = showOverviewMerit ? '' : 'none';
  if(overviewVocationalChartBox) overviewVocationalChartBox.style.display = showVocational && showOverviewMerit ? '' : 'none';
  $('overviewKnowledgeHeader').innerHTML = infoLabel(viewConfig.labels.uppnatt_alla_amnen, viewConfig.tooltips.uppnatt_alla_amnen);
  $('overviewMerit16Header').style.display = showOverviewMerit ? '' : 'none';
  $('overviewMerit17Header').style.display = showOverviewMerit ? '' : 'none';

  const sortedMeritRows = tableMeritRows
    .sort((a,b) => `${schoolLabel(a)}${a.arskurs}${rowGender(a)}${rowGroup(a)}`.localeCompare(`${schoolLabel(b)}${b.arskurs}${rowGender(b)}${rowGroup(b)}`, 'sv', {numeric:true}));
  renderSvaKpis(local);
  setTableSummary('overviewTableSummary', currentTableSummary());
  $('localMeritRows').innerHTML = renderSchoolGroupedBody(sortedMeritRows, {
    colspan: 6 + (showOverviewMerit ? 2 : 0),
    emptyHtml: `<tr><td colspan="${6 + (showOverviewMerit ? 2 : 0)}" class="muted">Inga rader matchar urvalet.</td></tr>`,
    schoolCell: schoolCellHtml,
    rowCells: row => {
      const meritCells = showOverviewMerit ? `<td class="numeric">${fmt(row.genomsnittligt_meritvarde_16)}</td><td class="numeric">${fmt(row.genomsnittligt_meritvarde_17)}</td>` : '';
      return {
        beforeSchool: `<td>${showGradeCell(row.arskurs)}</td>`,
        afterSchool: `<td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td class="numeric">${studentCountCell(row.antal_elever)}</td>${meritCells}<td>${pctBar(row.andel_uppnatt_alla_amnen, formatPercentWithCount(row.andel_uppnatt_alla_amnen, row.antal_elever))}</td>`
      };
    }
  });

  if(showOverviewMerit){
  const chartRows = meritRows.filter(r => rowGender(r) === 'Alla' && rowGroup(r) === 'Alla');
  makeChart('overviewChart','bar',{
    labels: chartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)}`),
    datasets:[
      {label:'Meritvärde 17', data:chartRows.map(r => r.genomsnittligt_meritvarde_17), backgroundColor:'#2f6f9f'}
    ]
  },{scales:{y:{beginAtZero:false}}});
  if(showVocational){
    makeChart('vocOverviewChart','bar',{
      labels: chartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)}`),
      datasets:[
        {label:'Yrkesbehörighet %', data:chartRows.map(r => r.andel_behoriga_yrkesprogram), backgroundColor:'#347f6a'}
      ]
    },{scales:{y:{beginAtZero:true,max:100}}});
  }else{
    destroyChart('vocOverviewChart');
  }
  }

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

  const svSvaRows = localFilterRows(local.svSva || [], {includeAggregateRow:true}).filter(r => ['SV','SVA'].includes(r.elevgrupp));
  setTableSummary('svaTableSummary', currentTableSummary({groupLabel:'Sv/Sva'}));
  $('svaRows').innerHTML = renderSchoolGroupedBody(svSvaRows, {
    colspan: 7,
    emptyHtml: '<tr><td colspan="7" class="muted">Ingen SV/SVA-data hittades för urvalet.</td></tr>',
    schoolCell: schoolCellHtml,
    rowCells: row => ({
      beforeSchool: `<td>${showGradeCell(row.arskurs)}</td>`,
      afterSchool: `<td>${showGroupCell(row.elevgrupp)}</td>${rightCell(row.antal_elever ?? '-')}` + `<td class="numeric">${fmt(row.genomsnittligt_meritvarde_17)}</td><td>${pctBar(row.andel_godkand_sv_sva)}</td><td>${pctBar(row.andel_uppnatt_alla_amnen)}</td>`
    })
  });

  const subjectRows = subjectDistributionRows(local, {includeAggregateRow:true});
  const subjectChartRows = subjectDistributionRows(local);
  setTableSummary('subjectTableSummary', currentTableSummary({groupLabel:'Sv/Sva'}));
  $('subjectRows').innerHTML = renderSchoolGroupedBody(subjectRows.slice(0, 180), {
    colspan: 14,
    emptyHtml: '<tr><td colspan="14" class="muted">Ingen ämnesdata matchar urvalet.</td></tr>',
    schoolCell: schoolCellHtml,
    rowCells: row => ({
      beforeSchool: `<td>${showGradeCell(row.arskurs)}</td>`,
      afterSchool: `<td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td>${esc(subjectLabel(row))}</td><td class="numeric">${fmt(row.betygspoang)}</td>${rightCell(row.antal_A ?? 0)}${rightCell(row.antal_B ?? 0)}${rightCell(row.antal_C ?? 0)}${rightCell(row.antal_D ?? 0)}${rightCell(row.antal_E ?? 0)}${rightCell(row.antal_F ?? 0)}<td>${pctBar(row.andel_A_E)}</td>${rightCell(row.antal_betyg)}`
    })
  });
  const topSubjects = subjectChartRows.slice(0, 24);
  makeChart('subjectChart','bar',{
    labels: topSubjects.map(r => `Åk ${r.arskurs} ${schoolLabel(r)} ${subjectLabel(r)}`),
    datasets:[
      {label:'Betygspoäng', data:topSubjects.map(r => r.betygspoang), backgroundColor:'#2f6f9f', yAxisID:'y'},
      {label:'Andel F %', data:topSubjects.map(r => r.andel_F), backgroundColor:'#b73535', yAxisID:'y1'}
    ]
  },{scales:{y:{beginAtZero:true,max:20},y1:{beginAtZero:true,max:100,position:'right',grid:{drawOnChartArea:false}}}});

  setTableSummary('gradeDistTableSummary', currentTableSummary({groupLabel:'Sv/Sva'}));
  $('gradeDistRows').innerHTML = renderSchoolGroupedBody(subjectRows.slice(0, 180), {
    colspan: 12,
    emptyHtml: '<tr><td colspan="12" class="muted">Ingen betygsfördelning matchar urvalet.</td></tr>',
    schoolCell: schoolCellHtml,
    rowCells: row => ({
      beforeSchool: `<td>${showGradeCell(row.arskurs)}</td>`,
      afterSchool: `<td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td>${esc(subjectLabel(row))}</td><td>${pctBar(row.andel_A)}</td><td>${pctBar(row.andel_B)}</td><td>${pctBar(row.andel_C)}</td><td>${pctBar(row.andel_D)}</td><td>${pctBar(row.andel_E)}</td><td>${pctBar(row.andel_F)}</td>${rightCell(row.antal_betyg)}`
    })
  });
  const gradeChartRows = subjectChartRows.slice(0, 18);
  makeChart('gradeDistChart','bar',{
    labels: gradeChartRows.map(r => `Åk ${r.arskurs} ${schoolLabel(r)} ${subjectLabel(r)}`),
    datasets:[
      {label:'A %', data:gradeChartRows.map(r => r.andel_A), backgroundColor:'#1f5f7a'},
      {label:'B %', data:gradeChartRows.map(r => r.andel_B), backgroundColor:'#2f6f9f'},
      {label:'C %', data:gradeChartRows.map(r => r.andel_C), backgroundColor:'#347f6a'},
      {label:'D %', data:gradeChartRows.map(r => r.andel_D), backgroundColor:'#8a7a35'},
      {label:'E %', data:gradeChartRows.map(r => r.andel_E), backgroundColor:'#b86b1d'},
      {label:'F %', data:gradeChartRows.map(r => r.andel_F), backgroundColor:'#b73535'}
    ]
  },{scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,max:100}}});

  renderLocalOutcomes(local, meritRows, {hideAggregateOutcome: selectedGrades.length > 1});
  renderLocalControl(local);
  renderLocalNp(local);
}
function renderSvaKpis(local){
  const target = $('svaKpiCards');
  if(!target) return;
  target.innerHTML = '';
  const box = target.closest('.box');
  if(box) box.style.display = 'none';
}
function renderLocalNp(local){
  const f = state.filters;
  const npFilter = r => {
    if(f.grades.length && !f.grades.includes(String(r.arskurs ?? ''))) return false;
    if(f.gender !== 'Alla' && rowGender(r) !== f.gender) return false;
    if(f.gender === 'Alla' && rowGender(r) !== 'Alla') return false;
    if(f.group !== 'Alla' && rowGroup(r) !== f.group) return false;
    if(f.group === 'Alla' && rowGroup(r) !== 'Alla') return false;
    if(r.niva === 'kommun') return true;
    if(!schoolSupportsRowGrade(r)) return false;
    return r.niva === 'skolenhet' && (!f.schools.length || f.schools.includes(schoolKey(r)));
  };
  const npPass = (local.npPass || []).filter(npFilter);
  const npRelation = (local.npRelation || []).filter(npFilter);
  const passRows = npPass.sort((a,b) => `${a.niva}${a.skolenhetsnamn}${a.arskurs}${a.amne}`.localeCompare(`${b.niva}${b.skolenhetsnamn}${b.arskurs}${b.amne}`, 'sv'));
  const relationRows = npRelation.sort((a,b) => `${a.niva}${a.skolenhetsnamn}${a.arskurs}${a.amne}`.localeCompare(`${b.niva}${b.skolenhetsnamn}${b.arskurs}${b.amne}`, 'sv'));

  const totalNp = passRows.reduce((sum, row) => sum + Number(row.antal_np || 0), 0);
  const totalPassed = passRows.reduce((sum, row) => sum + Number(row.antal_godkanda_np || 0), 0);
  const totalCompared = relationRows.reduce((sum, row) => sum + Number(row.antal_jamforda || 0), 0);
  const totalHigher = relationRows.reduce((sum, row) => sum + Number(row.antal_betyg_hogre_an_np || 0), 0);
  const selectedGradeText = f.grades.length ? f.grades.map(g => `Årskurs: ${g}`).join(', ') : 'Årskurs: Alla';
  const selectedSchoolText = `Skolor: ${selectedSchoolSummary()}`;
  const selectedGroupText = `Sv/Sva: ${f.group === 'Alla' ? 'Alla' : f.group}`;
  const selectedGenderText = `Kön: ${f.gender === 'Alla' ? 'Alla' : f.gender}`;

  $('npComparedCard').textContent = totalCompared ? totalCompared.toLocaleString('sv-SE') : '-';
  $('npPassRateCard').textContent = totalNp ? fmt((totalPassed / totalNp) * 100, ' %') : '-';
  $('npHigherCard').textContent = totalCompared ? fmt((totalHigher / totalCompared) * 100, ' %') : '-';
  $('npSourceCard').textContent = local.npPass?.length || local.npRelation?.length ? 'Lokal' : 'Öppen källa';
  $('npFilterSummary').textContent = `Urval: ${selectedGradeText} · ${selectedGenderText} · ${selectedGroupText} · ${selectedSchoolText}`;
  setTableSummary('npPassTableSummary', `${selectedGradeText} · ${selectedGenderText} · ${selectedGroupText} · ${selectedSchoolText}`);
  setTableSummary('npRelationTableSummary', `${selectedGradeText} · ${selectedGenderText} · ${selectedGroupText} · ${selectedSchoolText}`);
  renderAk3Kpis(local);

  $('npLocalRows').innerHTML = renderSchoolGroupedBody(passRows, {
    colspan: 8,
    emptyHtml: '<tr><td colspan="8" class="muted">Ingen lokal NP-data hittades.</td></tr>',
    schoolCell: (row, span) => `<td rowspan="${span}" class="school-cell"><strong>${esc(row.skolenhetsnamn || row.skolenhetskod || row.niva)}</strong></td>`,
    rowCells: row => ({
      afterSchool: `<td>${showGradeCell(row.arskurs)}</td><td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td>${esc(row.amne)}</td>${rightCell(row.antal_np)}<td>${pctBar(row.andel_godkanda_np)}</td>${rightCell(row.antal_med_betygsmatch ?? '-')}`
    })
  });
  $('npRelationRows').innerHTML = renderSchoolGroupedBody(relationRows, {
    colspan: 9,
    emptyHtml: '<tr><td colspan="9" class="muted">Ingen betyg-NP-relation kunde beräknas för aktuellt urval.</td></tr>',
    schoolCell: (row, span) => `<td rowspan="${span}" class="school-cell"><strong>${esc(row.skolenhetsnamn || row.skolenhetskod || row.niva)}</strong></td>`,
    rowCells: row => ({
      afterSchool: `<td>${showGradeCell(row.arskurs)}</td><td>${showGenderCell(row.kon || 'Alla')}</td><td>${showGroupCell(row.elevgrupp || 'Alla')}</td><td>${esc(row.amne)}</td>${rightCell(row.antal_jamforda)}<td>${pctBar(row.andel_betyg_hogre_an_np)}</td><td>${pctBar(row.andel_betyg_lika_np)}</td><td>${pctBar(row.andel_betyg_lagre_an_np)}</td>`
    })
  });

  const topPass = passRows.filter(r => r.niva === 'kommun').slice(0, 12);
  makeChart('npPassChart','bar',{
    labels: topPass.map(r => `Åk ${r.arskurs} ${r.amne}`),
    datasets:[{label:'Andel godkända NP %', data:topPass.map(r => r.andel_godkanda_np), backgroundColor:'#347f6a'}]
  },{indexAxis:'y',scales:{x:{beginAtZero:true,max:100}}});

  const topRelation = relationRows.filter(r => r.niva === 'kommun').slice(0, 12);
  makeChart('npRelationChart','bar',{
    labels: topRelation.map(r => `Åk ${r.arskurs} ${r.amne}`),
    datasets:[
      {label:'Betyg > NP %', data:topRelation.map(r => r.andel_betyg_hogre_an_np), backgroundColor:'#b86b1d'},
      {label:'Betyg = NP %', data:topRelation.map(r => r.andel_betyg_lika_np), backgroundColor:'#347f6a'},
      {label:'Betyg < NP %', data:topRelation.map(r => r.andel_betyg_lagre_an_np), backgroundColor:'#2f6f9f'}
    ]
  },{scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,max:100}}});
}
function renderAk3Kpis(local){
  const target = $('npAk3Kpi');
  if(!target) return;
  const container = target.closest('.box');
  const selectedGrades = state.filters?.grades || [];
  const showAk3 = !selectedGrades.length || selectedGrades.includes('3');
  if(container) container.style.display = showAk3 ? '' : 'none';
  if(!showAk3){
    target.innerHTML = '';
    return;
  }

  const rows = (local.npPass || []).filter(r =>
    Number(r.arskurs) === 3 &&
    r.niva === 'kommun' &&
    (r.elevgrupp || 'Alla') === 'Alla' &&
    ['Alla', 'Flickor', 'Pojkar'].includes(r.kon || 'Alla')
  );

  const bySubject = {};
  for(const row of rows){
    bySubject[row.amne] ||= {};
    bySubject[row.amne][row.kon || 'Alla'] = row;
  }

  const cards = [
    {
      subject: 'Ma',
      title: 'Elever i åk 3 som klarat alla delar av nationella proven för ämnesprovet i matematik',
      accent: '#1f5f7a'
    },
    {
      subject: 'Sv/Sva',
      title: 'Elever i åk 3 som klarat alla delar av nationella proven för ämnesproven i svenska och svenska som andraspråk',
      accent: '#347f6a'
    }
  ];

  target.innerHTML = cards.map(card => {
    const subjectRows = bySubject[card.subject] || {};
    const total = subjectRows.Alla;
    if(!total){
      return `<article class="kpi-card" style="border-left-color:${card.accent}"><h3>${esc(card.title)}, kommunala skolor, andel (%)</h3><div class="kpi-empty">Ingen lokal åk 3-data hittades för valt läsår.</div></article>`;
    }

    const chip = (label, row) => `
      <div class="kpi-chip">
        <span class="kpi-chip-label">${esc(label)}</span>
        <span class="kpi-chip-value">${fmt(row?.andel_godkanda_np, ' %')}</span>
      </div>`;

    return `
      <article class="kpi-card" style="border-left-color:${card.accent}">
        <h3>${esc(card.title)}, kommunala skolor, andel (%)</h3>
        <div class="kpi-topline">
          <div>
            <div class="kpi-main">${fmt(total.andel_godkanda_np, ' %')}</div>
            <div class="kpi-main-sub">Alla elever · ${esc(total.antal_godkanda_np)} av ${esc(total.antal_np)}</div>
          </div>
          <div class="badge" style="color:var(--txt);border-color:var(--brd);background:#fff">Lokal data</div>
        </div>
        <div class="kpi-breakdown">
          ${chip('Alla', subjectRows.Alla)}
          ${chip('Flickor', subjectRows.Flickor)}
          ${chip('Pojkar', subjectRows.Pojkar)}
        </div>
      </article>`;
  }).join('');
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
  $('npRows').innerHTML = '<tr><td colspan="4" class="muted">Öppna jämförelsetal används inte när lokal SCB-import är laddad.</td></tr>';
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

function applyCurrentViewVisibilityRules(){
  const selectedGrade = selectedSingleGrade();
  const showVocational = selectedGrade == null || Number(selectedGrade) === 9;
  const gradeIsOnly3 = selectedGrade != null && Number(selectedGrade) === 3;

  const vocationalCard = $('vocCard')?.closest('.card');
  if(vocationalCard) vocationalCard.style.display = showVocational ? '' : 'none';
  if(!showVocational && $('vocCard')) $('vocCard').textContent = '-';

  const vocationalRowsBox = $('vocationalRows')?.closest('.box');
  const vocationalChartBox = $('vocationalChart')?.closest('.box');
  if(vocationalRowsBox) vocationalRowsBox.style.display = showVocational ? '' : 'none';
  if(vocationalChartBox) vocationalChartBox.style.display = showVocational ? '' : 'none';

  const npHigherCard = $('npHigherCard')?.closest('.card');
  const npRelationRowsBox = $('npRelationRows')?.closest('.box');
  const npRelationChartBox = $('npRelationChart')?.closest('.box');
  if(npHigherCard) npHigherCard.style.display = gradeIsOnly3 ? 'none' : '';
  if(npRelationRowsBox) npRelationRowsBox.style.display = gradeIsOnly3 ? 'none' : '';
  if(npRelationChartBox) npRelationChartBox.style.display = gradeIsOnly3 ? 'none' : '';
  if(gradeIsOnly3 && $('npHigherCard')) $('npHigherCard').textContent = '-';
}

const __baseRenderFilteredLocal = renderFilteredLocal;
renderFilteredLocal = function(){
  __baseRenderFilteredLocal();
  applyCurrentViewVisibilityRules();
};

// Override legacy text with user-facing labels and corrected Swedish characters.
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
  $('npRows').innerHTML = '<tr><td colspan="4" class="muted">Öppna jämförelsetal används inte när lokal SCB-import är laddad.</td></tr>';
  const hasSvSvaRows = (local.svSva || []).some(r => ['SV','SVA'].includes(r.elevgrupp));
  $('availabilityRows').innerHTML = [
    [local.isDemo ? 'Demodata' : local.sourceKind === 'processed' ? 'Bearbetad publiceringsdata' : 'Årets SCB-betyg', 'Tillgänglig', `Läst från ${local.base}`],
    ['SV/SVA-jämförelse', hasSvSvaRows ? 'Tillgänglig' : 'Saknas', 'Beräknas från Sv/Sva-kolumnerna.'],
    ['Datakontroll för lokal import', (local.control || []).length ? 'Tillgänglig' : 'Saknas', 'Bygger på lokal SCB-import och visar giltiga betyg, tomma värden och specialkoder per ämne.'],
    ['Nationella prov', (local.npPass || []).length ? 'Tillgänglig' : 'Saknas', 'Beräknas från lokal NP-import per kommun och skolenhet.'],
    ['Relation mellan betyg och nationella prov', (local.npRelation || []).length ? 'Tillgänglig' : 'Saknas', 'Kräver både betygsfil och NP-fil med matchande elev/skolenhet.'],
    ['Öppna jämförelsetal', 'Ej använd', 'Lokal SCB-import hittades och används som primär källa.']
  ].map(r => `<tr><td><strong>${esc(r[0])}</strong></td><td class="${r[1] === 'Tillgänglig' ? 'ok' : r[1] === 'Ej använd' ? 'muted' : 'warn'}">${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`).join('');
  $('tableRows').innerHTML = (local.manifest.files || []).map(f => `<tr><td><strong>${esc(f.file)}</strong></td><td class="ok">Inläst</td><td>${esc(f.rows)} rader</td></tr>`).join('') || '<tr><td colspan="3" class="muted">Manifestet innehåller inga filrader.</td></tr>';
  log('Lokal SCB-import används', local.manifest);
  setStatus(local.isDemo ? 'warn' : 'ok', local.isDemo ? 'Demodata laddad.' : 'Lokal SCB-import laddad.', `${local.isDemo ? 'Visar anonym testdata' : 'Visar anonymiserad statistik'} från ${local.base}.`);
}

