function renderMetricRows(){
  $('metricCount').textContent = state.metrics.filter(m => m.status === 'ok').length;
  $('metricRows').innerHTML = state.metrics.map(m => `<tr><td><strong>${esc(m.label)}</strong></td><td class="${m.status === 'ok' ? 'ok' : m.status === 'error' ? 'err' : 'warn'}">${m.status === 'ok' ? 'Klar' : m.status === 'error' ? 'Tekniskt fel' : 'Saknas'}</td><td>${esc(m.table ? m.table.text : m.reason)}</td></tr>`).join('');
}
function renderTables(){
  $('tableCount').textContent = state.tables.length;
  $('tableRows').innerHTML = state.tables.map(t => `<tr><td><strong>${esc(t.text)}</strong><br><code>${esc(t.path)}</code></td><td class="ok">Inläst</td><td>${esc(variableSummary(t.meta))}</td></tr>`).join('') || '<tr><td colspan="3" class="muted">Inga tekniska datakällor hittades.</td></tr>';
}
function renderAvailability(){
  const byKey = Object.fromEntries(state.metrics.map(m => [m.key, m]));
  const rows = [
    ['Skillnader mellan flickor och pojkar', byKey.merit?.status === 'ok' ? 'Tillgänglig' : 'Osäker', 'Visas när könsuppdelat underlag finns tillgängligt.'],
    ['Meritvärde', byKey.merit?.status === 'ok' ? 'Tillgänglig' : 'Saknas', byKey.merit?.table?.text || byKey.merit?.reason],
    ['Meritvärde för elever som läser SVA', byKey.svaMerit?.status === 'ok' ? 'Tillgänglig' : 'Saknas', byKey.svaMerit?.table?.text || byKey.svaMerit?.reason],
    ['Resultat per ämne', byKey.subjectPoints?.status === 'ok' ? 'Tillgänglig' : 'Saknas', byKey.subjectPoints?.table?.text || byKey.subjectPoints?.reason],
    ['Datakontroll för lokal import', 'Lokal vy', 'Visas när lokal SCB-import finns.'],
    ['Nationella prov jämfört med betyg', byKey.npGap?.status === 'ok' ? 'Delvis tillgänglig' : 'Begränsad', byKey.npGap?.status === 'ok' ? 'Jämförelsetal finns för delar av underlaget, men inte för alla ämnen och årskurser.' : byKey.npGap?.reason],
    ['Relation mellan betyg och nationella prov', byKey.npRelation?.status === 'ok' ? 'Tillgänglig' : 'Saknas', byKey.npRelation?.table?.text || byKey.npRelation?.reason],
    ['Måluppfyllelse i alla ämnen', byKey.knowledgeAll?.status === 'ok' ? 'Tillgänglig' : 'Saknas', byKey.knowledgeAll?.table?.text || byKey.knowledgeAll?.reason],
    ['Yrkesbehörighet till gymnasiet', byKey.vocational?.status === 'ok' ? 'Tillgänglig' : byKey.vocational?.status === 'error' ? 'Tekniskt fel' : 'Saknas', byKey.vocational?.table?.text || byKey.vocational?.reason],
    ['Fördelning av betyg per skolenhet och kommun', byKey.gradeDistribution?.status === 'ok' ? 'Tillgänglig' : byKey.gradeDistribution?.status === 'error' ? 'Tekniskt fel' : 'Saknas', byKey.gradeDistribution?.reason || 'Detaljerad skolnivå kräver att underlaget innehåller skolenheter.']
  ];
  $('availabilityRows').innerHTML = rows.map(r => `<tr><td><strong>${esc(r[0])}</strong></td><td class="${/Tillgänglig|Lokal vy/.test(r[1]) ? 'ok' : 'warn'}">${esc(r[1])}</td><td>${esc(r[2] || '')}</td></tr>`).join('');
}
function destroyChart(id){ if(charts[id]) charts[id].destroy(); }
function makeChart(id, type, data, options={}){
  destroyChart(id);
  charts[id] = new Chart($(id), {type, data, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'top'}}, ...options}});
}
function renderGender(){
  const metric = state.metrics.find(m => m.key === 'merit' && m.status === 'ok');
  $('svaRows').innerHTML = '<tr><td colspan="7" class="muted">SV/SVA per skolenhet visas när lokal SCB-import finns.</td></tr>';
  if(!metric){
    $('genderRows').innerHTML = '<tr><td colspan="7" class="muted">Ingen könsuppdelad data hittades.</td></tr>';
    makeChart('genderChart','bar',{labels:['Ingen data'],datasets:[{label:'Värde',data:[0]}]});
    return;
  }
  const cols = metric.data.columns || [];
  const measureVar = findMeasureVar(metric.table.meta);
  const genderVar = findGenderVar(metric.table.meta);
  const g = valuesForGender(genderVar);
  const rowsByMeasure = {};
  for(const row of metric.data.data || []){
    const measureIdx = cols.findIndex(c => c.code === measureVar?.code);
    const levelIdx = cols.findIndex(c => /level|kommun/i.test(c.code + c.text));
    const genderIdx = cols.findIndex(c => /kön|kon|sex/i.test(c.code + c.text));
    if(levelIdx >= 0 && row.key[levelIdx] !== KOMKOD) continue;
    const measure = measureIdx >= 0 ? row.key[measureIdx] : metric.measureValues?.[0];
    rowsByMeasure[measure] ||= {};
    const gender = genderIdx >= 0 ? row.key[genderIdx] : g.total || 'total';
    rowsByMeasure[measure][gender] = row.values?.[0];
  }
  const firstMeasure = Object.keys(rowsByMeasure)[0];
  const first = rowsByMeasure[firstMeasure] || {};
  $('meritCard').textContent = fmt(first[g.total] ?? first.total);
  $('genderRows').innerHTML = Object.entries(rowsByMeasure).map(([measure, vals]) => `<tr><td>-</td><td><strong>Sävsjö kommun</strong></td><td>${esc(valueText(measureVar, measure))}</td><td>${fmt(vals[g.boys])}</td><td>${fmt(vals[g.girls])}</td><td>${fmt(vals[g.total] ?? vals.total)}</td><td>-</td></tr>`).join('') || '<tr><td colspan="7" class="muted">Tabellen saknar könsdimension.</td></tr>';
  makeChart('genderChart','bar',{
    labels:['Pojkar','Flickor','Totalt'],
    datasets:[{label:valueText(measureVar, firstMeasure), data:[first[g.boys], first[g.girls], first[g.total] ?? first.total].map(v => Number.parseFloat(String(v).replace(',','.'))), backgroundColor:['#2f6f9f','#8a5a96','#5b6b73']}]
  },{scales:{y:{beginAtZero:false}}});
}
function renderSubjects(){
  const metric = state.metrics.find(m => m.key === 'subjectPoints' && m.status === 'ok');
  $('gradeDistRows').innerHTML = '<tr><td colspan="12" class="muted">Full A-F-fördelning visas när lokal SCB-import finns.</td></tr>';
  makeChart('gradeDistChart','bar',{labels:['Ingen lokal A-F-data'],datasets:[{label:'Värde',data:[0]}]});
  if(!metric){
    $('subjectRows').innerHTML = '<tr><td colspan="14" class="muted">Ingen ämnesdata hittades.</td></tr>';
    makeChart('subjectChart','bar',{labels:['Ingen data'],datasets:[{label:'Värde',data:[0]}]});
    return;
  }
  const cols = metric.data.columns || [];
  const measureVar = findMeasureVar(metric.table.meta);
  const measureIdx = cols.findIndex(c => c.code === measureVar?.code);
  const levelIdx = cols.findIndex(c => /level|kommun/i.test(c.code + c.text));
  const bySubject = {};
  for(const row of metric.data.data || []){
    if(measureIdx < 0) continue;
    const name = subjectName(valueText(measureVar, row.key[measureIdx]));
    bySubject[name] ||= {};
    const level = levelIdx >= 0 ? row.key[levelIdx] : KOMKOD;
    bySubject[name][level] = row.values?.[0];
  }
  const subjects = Object.entries(bySubject).sort((a,b) => a[0].localeCompare(b[0], 'sv'));
  $('subjectRows').innerHTML = subjects.map(([name, vals]) => `<tr><td>-</td><td><strong>Sävsjö kommun</strong></td><td>Alla</td><td>Alla</td><td>${esc(name)}</td><td>${fmt(vals[KOMKOD])}</td><td colspan="6" class="muted">A-F saknas i PxWeb-fallback</td><td>${fmt(vals['00'])} riket</td><td>-</td></tr>`).join('');
  makeChart('subjectChart','bar',{
    labels: subjects.map(x => x[0]),
    datasets:[
      {label:'Sävsjö', data:subjects.map(([,v]) => Number.parseFloat(String(v[KOMKOD]).replace(',','.'))), backgroundColor:'#2f6f9f'},
      {label:'Riket', data:subjects.map(([,v]) => Number.parseFloat(String(v['00']).replace(',','.'))), backgroundColor:'#9aa6ad'}
    ]
  },{scales:{y:{beginAtZero:false}}});
}
function renderNp(){
  const metric = state.metrics.find(m => m.key === 'npGap' && m.status === 'ok');
  if(!metric){
    $('npRows').innerHTML = '<tr><td colspan="4" class="muted">Inga NP-/betygsnära mått kunde hämtas.</td></tr>';
    return;
  }
  const cols = metric.data.columns || [];
  const measureVar = findMeasureVar(metric.table.meta);
  const measureIdx = cols.findIndex(c => c.code === measureVar?.code);
  const levelIdx = cols.findIndex(c => /level|kommun|huvudman|skolenhet/i.test(c.code + c.text));
  const byMeasure = {};
  for(const row of metric.data.data || []){
    const measure = measureIdx >= 0 ? row.key[measureIdx] : '';
    const level = levelIdx >= 0 ? row.key[levelIdx] : '';
    byMeasure[measure] ||= {};
    byMeasure[measure][level] = row.values?.[0];
  }
  $('npRows').innerHTML = Object.entries(byMeasure).map(([measure, vals]) => {
    const local = vals[HUVUDMAN_KOD];
    const national = vals['00'];
    const gap = Number.parseFloat(String(local).replace(',','.')) - Number.parseFloat(String(national).replace(',','.'));
    return `<tr><td><strong>${esc(valueText(measureVar, measure))}</strong></td><td>${pctBar(local)}</td><td>${pctBar(national)}</td><td>${Number.isFinite(gap) ? fmt(gap, ' p.e.') : '-'}</td></tr>`;
  }).join('');
}
function renderOverview(){
  const merit = state.metrics.find(m => m.key === 'merit' && m.status === 'ok');
  const vocational = state.metrics.find(m => m.key === 'vocational' && m.status === 'ok');
  $('knowledgeRows').innerHTML = '<tr><td colspan="6" class="muted">Uppnått alla ämnen per skolenhet visas när lokal SCB-import finns.</td></tr>';
  $('vocationalRows').innerHTML = '<tr><td colspan="5" class="muted">Yrkesbehörighet per skolenhet visas när lokal SCB-import finns.</td></tr>';
  makeChart('knowledgeChart','bar',{labels:['Ingen lokal data'],datasets:[{label:'Uppnått alla ämnen %',data:[0]}]});
  makeChart('vocationalChart','bar',{labels:['Ingen lokal data'],datasets:[{label:'Yrkesbehörighet %',data:[0]}]});
  const getTotal = metric => {
    if(!metric) return null;
    const levelCode = metric.table?.path?.includes('Underlag_for_analys') ? HUVUDMAN_KOD : KOMKOD;
    const vals = extractLevel(metric.data.data, metric.data.columns || [], levelCode);
    return vals.T ?? vals.total ?? Object.values(vals)[0];
  };
  const meritVal = getTotal(merit);
  const vocVal = getTotal(vocational);
  $('meritCard').textContent = fmt(meritVal);
  $('vocCard').textContent = fmt(vocVal, vocational ? ' %' : '');
  makeChart('overviewChart','bar',{
    labels:['Meritvärde','Yrkesbehörighet'],
    datasets:[{label:'Sävsjö', data:[Number.parseFloat(meritVal), Number.parseFloat(vocVal)], backgroundColor:['#2f6f9f','#347f6a']}]
  },{scales:{y:{beginAtZero:false}}});
}
