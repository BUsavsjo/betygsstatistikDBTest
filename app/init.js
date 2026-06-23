async function loadAll(){
  state = {tables:[], metrics:[], diagnostics:[], local:null, filters:{grades:[], schools:[], gender:'Alla', group:'Alla'}};
  $('diagLog').textContent = '';
  $('localFilters').classList.remove('active');
  $('demoNotice').style.display = 'none';
  $('localMeritRows').innerHTML = '';
  setStatus('loading', 'Hämtar PxWeb-kategorier...', 'Läser tabellistan från Skolverket.');
  const selectedYear = $('yearSel').selectedOptions[0];
  const year = {
    label: selectedYear.value,
    local: selectedYear.dataset.local,
    jmf: selectedYear.dataset.jmf,
    underlag: selectedYear.dataset.underlag
  };
  try{
    setStatus('loading', 'Söker lokal SCB-import...', `Letar efter data/output/${year.local}/json.`);
    const local = await tryLoadLocalYear(year.local);
    if(local){
      renderLocalData(local);
      return;
    }
    if(STATIC_PAGES_BUILD || IS_GITHUB_PAGES){
      const message = 'Ingen publicerad statisk JSON hittades för valt läsår.';
      log('GitHub Pages-läge: PxWeb-proxy är inte tillgänglig', {
        selectedYear: year.local,
        expectedDemoPath: `data/demo/${year.local}/json`,
        reason: 'GitHub Pages kan bara servera statiska filer och kör inte server.js.'
      });
      setStatus('warn', message, 'Bygg om docs med npm run build:pages efter att godkänd demo-JSON finns i data/demo.');
      $('availabilityRows').innerHTML = wantedViews.map(v => `<tr><td><strong>${esc(v[0])}</strong></td><td class="warn">Ej laddad</td><td>${esc(message)}</td></tr>`).join('');
      $('tableRows').innerHTML = '<tr><td colspan="3" class="muted">PxWeb-tabeller kan bara upptäckas via lokal server/proxy.</td></tr>';
      renderMetricRows();
      return;
    }
    const discovered = [];
    for(const root of ROOTS){
      try { discovered.push(...await discoverTables(root)); }
      catch(e){ log(`Kategoriläsning misslyckades: ${root}`, {error:e.message}); }
    }
    setStatus('loading', 'Läser tabellmetadata...', 'Väntar kort mellan anrop för att undvika rate limit.');
    for(const table of discovered){
      try{
        await sleep(320);
        table.meta = await pxGet(table.path);
        state.tables.push(table);
        log(`Metadata OK: ${table.path}`, {title:table.meta.title, variables:variableSummary(table.meta)});
      }catch(e){
        log(`Metadata misslyckades: ${table.path}`, {error:e.message});
      }
    }
    renderTables();
    setStatus('loading', 'Hämtar önskade mått...', 'Matchar måttnamn mot metadata och testar POST-anrop.');
    await loadMetric('merit', 'Meritvärde', [/meritvarde/], year, 8);
    await loadMetric('svaMerit', 'Meritvärde elever som läser SVA', [/meritvarde.*svenska som andrasprak/, /svenska som andrasprak.*meritvarde/, /\bsva\b.*meritvarde/], year, 6);
    await loadMetric('subjectPoints', 'Betygspoäng per ämne', [/genomsnittlig betygspoang/, /betygspoang.*i /], year, 24);
    await loadUnderlagBundle(year);
    await loadMetric('npRelation', 'Relation betyg och nationella prov', [/relation.*nationella prov/, /betyg.*provbetyg/, /hogre.*provbetyg/, /lagre.*provbetyg/], year, 12);
    await loadMetric('gradeDistribution', 'Betygsfördelning per skolenhet och kommun', [/betygsfordelning/, /betyg.*a.*b.*c.*d.*e.*f/, /andel.*betyg [abcde]/], year, 12);
    renderMetricRows();
    renderAvailability();
    renderOverview();
    renderGender();
    renderSubjects();
    renderNp();
    const ok = state.metrics.filter(m => m.status === 'ok').length;
    setStatus(ok ? 'ok' : 'warn', ok ? `Data hämtad: ${ok} mått fungerar.` : 'API:t svarade, men inga önskade mått hittades.', 'Se Datatäckning och Diagnostik för detaljer.');
  }catch(e){
    setStatus('error', 'Kunde inte hämta API-data.', e.message);
    log('Oväntat fel i laddning', {error:e.message});
  }
}
document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  tab.classList.add('active');
  $('tab-' + tab.dataset.tab).classList.add('active');
  setTimeout(() => Object.values(charts).forEach(c => c.resize()), 50);
}));
$('reloadBtn').addEventListener('click', loadAll);
$('diagBtn').addEventListener('click', () => document.querySelector('[data-tab="diagnostics"]').click());
['gradeFilter','schoolFilter','genderFilter','groupFilter'].forEach(id => {
  $(id).addEventListener('change', () => {
    updateFilterState();
    renderFilteredLocal();
  });
});
$('selectAllSchoolsBtn').addEventListener('click', () => {
  [...$('schoolFilter').options].forEach(o => o.selected = true);
  updateFilterState();
  renderFilteredLocal();
});
$('clearFiltersBtn').addEventListener('click', () => {
  if(!state.local) return;
  populateLocalFilters(state.local);
  renderFilteredLocal();
});
loadAll();
