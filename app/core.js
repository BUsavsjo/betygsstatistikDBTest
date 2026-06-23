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
