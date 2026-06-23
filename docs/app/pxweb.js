function norm(s){
  return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
}
async function fetchJson(url, options={}){
  const r = await fetch(url, options);
  const body = await r.text();
  if(!r.ok) throw new Error(`HTTP ${r.status}: ${body.slice(0,220)}`);
  try { return JSON.parse(body); } catch { throw new Error(`JSON kunde inte tolkas: ${body.slice(0,220)}`); }
}
function pxUrl(path){ return new URL(`api/pxweb?path=${encodeURIComponent(path)}`, location.href).toString(); }
async function pxGet(path){ return fetchJson(pxUrl(path), {headers:{Accept:'application/json'}}); }
async function pxPost(path, query){
  return fetchJson(pxUrl(path), {
    method:'POST',
    headers:{'Content-Type':'application/json', Accept:'application/json'},
    body:JSON.stringify({query, response:{format:'json'}})
  });
}
function pxItems(response){
  if(Array.isArray(response)) return response;
  if(Array.isArray(response?.value)) return response.value;
  return [];
}
async function discoverTables(path, depth=0){
  if(depth > 4) return [];
  await sleep(180);
  const list = pxItems(await pxGet(path));
  const tables = [];
  for(const item of list){
    const itemPath = `${path}${item.id}`;
    if(item.type === 't') tables.push({path:itemPath, text:item.text || item.id, id:item.id});
    if(item.type === 'l') tables.push(...await discoverTables(`${itemPath}/`, depth + 1));
  }
  return tables;
}
function variableSummary(meta){
  return (meta.variables || []).map(v => `${v.code}: ${v.text} (${(v.values || []).length})`).join(' | ');
}
function valueText(variable, value){
  const i = (variable.values || []).indexOf(value);
  return i >= 0 ? (variable.valueTexts?.[i] || value) : value;
}
function findVar(meta, tests){
  return (meta.variables || []).find(v => tests.some(t => t(norm(`${v.code} ${v.text}`), v)));
}
function findMeasureVar(meta){
  return findVar(meta, [
    text => /\bmatt\b|\bmat\b|measure|variable/.test(text),
    (_, v) => v.code === 'variable'
  ]);
}
function findTimeVar(meta){ return findVar(meta, [text => /\btid\b|lasar|\bar\b|\btime\b/.test(text), (_, v) => v.time]); }
function findLevelVar(meta){ return findVar(meta, [text => /kommun|huvudman|skolenhet|level|indelning/.test(text)]); }
function findGenderVar(meta){ return findVar(meta, [text => /kon|kÃ¶n|sex/.test(text)]); }
function pickTimeValue(variable, schoolYear, tablePath='', yearCodes={}){
  const values = (variable?.values || []).map(String);
  const preferred = tablePath.includes('Underlag_for_analys') ? yearCodes.underlag : yearCodes.jmf;
  if(preferred) return preferred;
  const texts = variable?.valueTexts || [];
  const byText = texts.findIndex(t => t === schoolYear);
  if(byText >= 0) return variable.values[byText];
  return values.includes(schoolYear) ? schoolYear : values[0];
}
function pickValueByText(variable, regexes){
  const texts = variable?.valueTexts || [];
  for(const re of regexes){
    const i = texts.findIndex(t => re.test(norm(t)));
    if(i >= 0) return variable.values[i];
  }
  return null;
}
function pickTotal(variable){
  return pickValueByText(variable, [/^totalt$/, /^samtliga/, /riket totalt/]) ||
    ['T','Totalt','0','00','samtl_kom'].find(v => (variable?.values || []).includes(v)) ||
    (variable?.values || [])[0];
}
function valuesForGender(variable){
  if(!variable) return { total:null, boys:null, girls:null };
  return {
    boys: pickValueByText(variable, [/pojkar/, /^man$/, /^male$/]) || ['1','M'].find(v => variable.values.includes(v)),
    girls: pickValueByText(variable, [/flickor/, /^kvinna$/, /^female$/]) || ['2','F'].find(v => variable.values.includes(v)),
    total: pickTotal(variable)
  };
}
function buildQuery(meta, measureValues, year, options={}){
  const query = [];
  const measureVar = findMeasureVar(meta);
  const timeVar = findTimeVar(meta);
  const levelVar = findLevelVar(meta);
  const genderVar = findGenderVar(meta);
  for(const v of meta.variables || []){
    if(v === measureVar){
      query.push({code:v.code, selection:{filter:'item', values:measureValues}});
    } else if(v === timeVar){
      const timeValue = pickTimeValue(v, year, options.path || '', options.yearCodes || {});
      query.push({code:v.code, selection:{filter:'item', values:[timeValue]}});
    } else if(v === levelVar){
      const values = [];
      if(!(v.values || []).length){
        // Vissa Skolverket-tabeller dÃ¶ljer vÃ¤rdelistan fÃ¶r huvudman/skolenhet i metadata.
        // DÃ¥ anvÃ¤nder vi kÃ¤nd huvudmannakod fÃ¶r SÃ¤vsjÃ¶ och riket i stÃ¤llet fÃ¶r ett stort all-anrop.
        query.push({code:v.code, selection:{filter:'item', values:[HUVUDMAN_KOD, '00']}});
      } else {
        if((v.values || []).includes(KOMKOD)) values.push(KOMKOD);
        if((v.values || []).includes('00')) values.push('00');
        if(!values.length) values.push(pickTotal(v));
        query.push({code:v.code, selection:{filter:'item', values:[...new Set(values)].filter(Boolean)}});
      }
    } else if(v === genderVar){
      const g = valuesForGender(v);
      const values = [g.boys, g.girls, g.total].filter(Boolean);
      query.push({code:v.code, selection:{filter:'item', values:[...new Set(values)]}});
    } else {
      query.push({code:v.code, selection:{filter:'item', values:[pickTotal(v)].filter(Boolean)}});
    }
  }
  return query;
}
function rowObject(result, row){
  const obj = { value: Number.parseFloat(String(row.values?.[0] ?? '').replace(',','.')), raw: row };
  (result.columns || []).forEach((c, i) => obj[c.code] = row.key?.[i]);
  return obj;
}
function extractLevel(rows, columns, levelCode, genderCode){
  const levelCol = columns.find(c => /level|kommun|huvudman|skolenhet/i.test(c.code + c.text));
  const genderCol = columns.find(c => /kÃ¶n|kon|sex/i.test(c.code + c.text));
  const levelIdx = columns.indexOf(levelCol);
  const genderIdx = columns.indexOf(genderCol);
  const out = {};
  for(const r of rows || []){
    if(levelIdx >= 0 && r.key[levelIdx] !== levelCode && !String(r.key[levelIdx]).includes(levelCode)) continue;
    const gender = genderIdx >= 0 ? r.key[genderIdx] : 'total';
    out[gender || 'total'] = r.values?.[0];
  }
  if(genderIdx < 0 && rows?.[0]) out.total = rows[0].values?.[0];
  return out;
}
function measureMatches(meta, regexes){
  const measureVar = findMeasureVar(meta);
  if(!measureVar) return [];
  return (measureVar.values || []).filter((value, i) => regexes.some(re => re.test(norm(measureVar.valueTexts?.[i] || value))));
}
function subjectName(text){
  return String(text || '').replace(/^.*i /i,'').replace(/^.*for /i,'');
}
async function loadMetric(key, label, regexes, year, postLimit=10){
  let matched = false;
  let lastError = null;
  for(const table of state.tables){
    const values = measureMatches(table.meta, regexes);
    if(!values.length) continue;
    matched = true;
    const selected = values.slice(0, postLimit);
    const query = buildQuery(table.meta, selected, year.label, {path: table.path, yearCodes: year});
    const timeSelection = query.find(q => q.code === findTimeVar(table.meta)?.code);
    if(timeSelection && table.path.includes('Underlag_for_analys')) timeSelection.selection.values = [year.underlag];
    if(timeSelection && !table.path.includes('Underlag_for_analys')) timeSelection.selection.values = [year.jmf];
    try{
      await sleep(900);
      const data = await pxPost(table.path, query);
      const metric = {key, label, status:'ok', table, measureValues:selected, query, data};
      state.metrics.push(metric);
      log(`POST OK: ${label}`, {path:table.path, rows:data.data?.length || 0, year, query, measures:selected.map(v => valueText(findMeasureVar(table.meta), v))});
      return metric;
    }catch(e){
      lastError = {path:table.path, error:e.message, query};
      log(`POST misslyckades: ${label}`, {path:table.path, error:e.message, query});
    }
  }
  if(matched){
    const failed = {key, label, status:'error', reason:'MÃ¥ttet finns i metadata, men POST-anropet misslyckades i webblÃ¤saren.', error:lastError};
    state.metrics.push(failed);
    log(`MÃ¥tt hittades men kunde inte hÃ¤mtas: ${label}`, lastError);
    return failed;
  }
  const missing = {key, label, status:'missing', reason:'Inget matchande mÃ¥tt hittades i Ã¶ppna PxWeb-tabeller.'};
  state.metrics.push(missing);
  log(`MÃ¥tt saknas: ${label}`);
  return missing;
}
function cloneMetricData(data, measureValues){
  const wanted = new Set(measureValues);
  const measureCode = data.columns?.[0]?.code || 'variable';
  const measureIdx = (data.columns || []).findIndex(c => c.code === measureCode);
  return {...data, data:(data.data || []).filter(row => wanted.has(row.key?.[measureIdx]))};
}
async function loadUnderlagBundle(year){
  const table = state.tables.find(t => t.path.includes('Underlag_for_analys') && t.path.includes('/Grundskola/Grundskola.px'));
  if(!table){
    ['vocational','knowledgeAll','npGap'].forEach(key => state.metrics.push({key, label:key, status:'missing', reason:'Underlagstabellen hittades inte.'}));
    return;
  }
  const values = ['24','25','26','43','44','45','46','47','48'];
  const query = buildQuery(table.meta, values, year.label, {path:table.path, yearCodes:year});
  const timeSelection = query.find(q => q.code === findTimeVar(table.meta)?.code);
  if(timeSelection) timeSelection.selection.values = [year.underlag];
  try{
    await sleep(900);
    const data = await pxPost(table.path, query);
    const measureVar = findMeasureVar(table.meta);
    const make = (key, label, selected) => {
      state.metrics.push({key, label, status:'ok', table, measureValues:selected, query, data:cloneMetricData(data, selected)});
    };
    make('vocational', 'YrkesbehÃ¶righet till gymnasiet', ['26']);
    make('knowledgeAll', 'UppnÃ¥tt kunskapskrav i alla Ã¤mnen', ['24','25']);
    make('npGap', 'NP GAP och betygsnÃ¤ra mÃ¥tt', ['43','44','45','46','47','48']);
    log('POST OK: Underlagspaket behÃ¶righet, kunskapskrav och NP', {path:table.path, rows:data.data?.length || 0, year, query, measures:values.map(v => valueText(measureVar, v))});
  }catch(e){
    log('POST misslyckades: Underlagspaket behÃ¶righet, kunskapskrav och NP', {path:table.path, error:e.message, query});
    [
      ['vocational','YrkesbehÃ¶righet till gymnasiet'],
      ['knowledgeAll','UppnÃ¥tt kunskapskrav i alla Ã¤mnen'],
      ['npGap','NP GAP och betygsnÃ¤ra mÃ¥tt']
    ].forEach(([key,label]) => state.metrics.push({key, label, status:'error', reason:'Underlagspaketet kunde inte hÃ¤mtas.', error:e.message}));
  }
}
