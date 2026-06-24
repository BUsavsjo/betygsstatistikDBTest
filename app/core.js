const KOMKOD = '0684';
const HUVUDMAN_KOD = '2120000563';
const PXBASE = 'https://statistikdatabasen.skolverket.se/PxWeb/api/v1/sv/Skolverkets_statistikdatabas';
const ROOTS = [
  '/Kommunala_jamforelsetal/Grundskola/',
  '/Underlag_for_analys_inom_det_nationella_kvalitetssystemet/Grundskola/'
];
const $ = id => document.getElementById(id);
let state = { tables: [], metrics: [], diagnostics: [], local: null, localSchools: [], filters: { grades: [], schools: [], gender: 'Alla', group: 'Alla' } };
let charts = {};
const STATIC_PAGES_BUILD = false;
const IS_GITHUB_PAGES = location.hostname.endsWith('github.io');

const wantedViews = [
  ['Pojkar/Flickor', 'Söker mått med könsuppdelning. PxWeb-tabeller utan könsdimension kan bara visas totalt.'],
  ['Meritvärde', 'Söker mått vars text innehåller meritvärde.'],
  ['Meritvärde elever som läser SVA', 'Söker specifikt meritvärde kopplat till svenska som andraspråk. Publiceras inte alltid öppet.'],
  ['Betygspoäng per ämne', 'Söker genomsnittlig betygspoäng per ämne.'],
  ['Kontroll antal betyg och specialkoder', 'Visas från lokal SCB-import för att kontrollera giltiga betyg, tomma värden och specialkoder per ämne.'],
  ['NP GAP åk 6/9', 'Söker NP-resultat och jämför med motsvarande betygsmått för SV/SVA, engelska och matematik.'],
  ['Relation betyg och nationella prov', 'Söker färdig relation mellan betyg och provbetyg.'],
  ['Uppnått kunskapskrav i alla ämnen', 'Söker andel elever med lägst E i samtliga ämnen.'],
  ['Yrkesbehörighet till gymnasiet', 'Söker behörighetsmått för yrkesprogram.'],
  ['Betygsfördelning per skolenhet och kommun', 'Söker betygsfördelning och skolenhetsdimension. Skolverket kan begränsa skolnivå i öppet API.']
];

function setStatus(type, text, sub=''){
  $('statusDot').className = `dot ${type}`;
  $('statusText').textContent = text;
  $('statusSub').textContent = sub;
}
function esc(s){return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }
function log(msg, obj){
  const line = `[${new Date().toLocaleTimeString('sv-SE')}] ${msg}`;
  state.diagnostics.push(obj ? `${line}\n${JSON.stringify(obj, null, 2)}` : line);
  $('diagLog').textContent = state.diagnostics.join('\n\n');
}
function fmt(v, suffix=''){
  const n = Number.parseFloat(String(v ?? '').replace(',','.'));
  return Number.isFinite(n) ? `${n.toLocaleString('sv-SE', {maximumFractionDigits:1})}${suffix}` : '-';
}
function formatPercentWithCount(percent, total){
  const percentNumber = Number.parseFloat(String(percent ?? '').replace(',','.'));
  const totalNumber = Number(total);
  if(!Number.isFinite(percentNumber)) return '-';
  if(!Number.isFinite(totalNumber) || totalNumber <= 0) return fmt(percentNumber, ' %');
  const count = Math.round((percentNumber / 100) * totalNumber);
  return `${fmt(percentNumber, ' %')} · ${count} av ${totalNumber.toLocaleString('sv-SE')}`;
}
function pctBar(v, label=null){
  const n = Number.parseFloat(String(v ?? '').replace(',','.'));
  if(!Number.isFinite(n)) return '-';
  const width = Math.max(0, Math.min(100, n));
  const display = label || fmt(n, ' %');
  return `<div class="pct-cell" title="${esc(display)}"><div class="pct-bar"><span class="pct-fill" style="width:${width}%"></span></div><span class="pct-label">${esc(display)}</span></div>`;
}
function isSmallGroup(studentCount){
  const count = Number(studentCount);
  return count > 0 && count < 10;
}
function studentCountCell(studentCount){
  const value = studentCount ?? '-';
  const badge = isSmallGroup(studentCount) ? '<div class="badge-muted">Lågt elevantal</div>' : '';
  return `${esc(value)}${badge}`;
}
function selectedSingleGrade(){
  const grades = state.filters?.grades || [];
  return grades.length === 1 ? Number(grades[0]) : null;
}
function getGradeViewConfig(grade){
  const isGrade6 = Number(grade) === 6;
  return {
    grade: Number.isFinite(Number(grade)) ? Number(grade) : null,
    isGrade6,
    title: isGrade6 ? 'Åk 6 – terminsbetyg och uppföljningssignaler' : null,
    description: isGrade6
      ? 'Resultaten bygger på terminsbetyg i årskurs 6 och ska användas som signal för uppföljning, inte som slutligt resultat eller behörighetsmått. Koladas 95-procentsregel används när 40 eller fler elever ingår och endast 1-4 elever inte når betygskriterierna i alla ämnen.'
      : null,
    labels: {
      uppnatt_alla_amnen: isGrade6 ? 'Minst E i alla ämnen med terminsbetyg' : 'Uppnått alla ämnen'
    },
    tooltips: {
      uppnatt_alla_amnen: isGrade6
        ? 'Åk 6 bygger på terminsbetyg. Måttet visar andel elever som har minst E i de ämnen där eleven har terminsbetyg. Det ska tolkas som uppföljningssignal, inte som slutligt resultat. Ämnen där eleven inte undervisats i årskurs 6 ska inte tolkas som underkända. När 40 eller fler elever ingår och bara 1-4 elever inte når måttet visas 95 procent enligt Kolada/Siris-regeln.'
        : null
    },
    hiddenColumns: isGrade6 ? ['yrkesbehorighet'] : []
  };
}
function gradeAwareLabel(key, grade){
  const config = getGradeViewConfig(grade);
  return config.labels[key] || key;
}
function infoLabel(label, tooltip){
  if(!tooltip) return esc(label);
  return `${esc(label)} <span class="info-icon" title="${esc(tooltip)}" aria-label="${esc(tooltip)}">i</span>`;
}
