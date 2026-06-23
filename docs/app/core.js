const KOMKOD = '0684';
const HUVUDMAN_KOD = '2120000563';
const PXBASE = 'https://statistikdatabasen.skolverket.se/PxWeb/api/v1/sv/Skolverkets_statistikdatabas';
const ROOTS = [
  '/Kommunala_jamforelsetal/Grundskola/',
  '/Underlag_for_analys_inom_det_nationella_kvalitetssystemet/Grundskola/'
];
const $ = id => document.getElementById(id);
let state = { tables: [], metrics: [], diagnostics: [], local: null, filters: { grades: [], schools: [], gender: 'Alla', group: 'Alla' } };
let charts = {};
const STATIC_PAGES_BUILD = true;
const IS_GITHUB_PAGES = location.hostname.endsWith('github.io');

const wantedViews = [
  ['Pojkar/Flickor', 'SÃ¶ker mÃ¥tt med kÃ¶nsuppdelning. PxWeb-tabeller utan kÃ¶nsdimension kan bara visas totalt.'],
  ['MeritvÃ¤rde', 'SÃ¶ker mÃ¥tt vars text innehÃ¥ller meritvÃ¤rde.'],
  ['MeritvÃ¤rde elever som lÃ¤ser SVA', 'SÃ¶ker specifikt meritvÃ¤rde kopplat till svenska som andrasprÃ¥k. Publiceras inte alltid Ã¶ppet.'],
  ['BetygspoÃ¤ng per Ã¤mne', 'SÃ¶ker genomsnittlig betygspoÃ¤ng per Ã¤mne.'],
  ['NP GAP Ã¥k 6/9', 'SÃ¶ker NP-resultat och jÃ¤mfÃ¶r med motsvarande betygsmÃ¥tt fÃ¶r SV/SVA, engelska och matematik.'],
  ['Relation betyg och nationella prov', 'SÃ¶ker fÃ¤rdig relation mellan betyg och provbetyg.'],
  ['UppnÃ¥tt kunskapskrav i alla Ã¤mnen', 'SÃ¶ker andel elever med lÃ¤gst E i samtliga Ã¤mnen.'],
  ['YrkesbehÃ¶righet till gymnasiet', 'SÃ¶ker behÃ¶righetsmÃ¥tt fÃ¶r yrkesprogram.'],
  ['BetygsfÃ¶rdelning per skolenhet och kommun', 'SÃ¶ker betygsfÃ¶rdelning och skolenhetsdimension. Skolverket kan begrÃ¤nsa skolnivÃ¥ i Ã¶ppet API.']
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
