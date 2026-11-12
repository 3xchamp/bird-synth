const fs = require('fs'), vm = require('vm');
const DIR = '/home/hatch/workspace/bird-synth/';
const html = fs.readFileSync(DIR+'syrinx6.html','utf8');
const script = html.split('<script>')[1].split('</script>')[0];
let pass = 0, fail = 0;
const ok = (cond, msg)=>{ if (cond){ pass++; } else { fail++; console.log('  FAIL:', msg); } };

/* ---------- 1. DOM audit ---------- */
console.log('== DOM audit ==');
const htmlIds = new Set([...html.matchAll(/ id="([^"]+)"/g)].map(m=>m[1]));
const litIds = [...script.matchAll(/getElementById\('([^']+)'\)/g)].map(m=>m[1]);
const voiceIds = ['cardinal','owl','thrush','wren','sparrow','towhee'];
let domChecked = 0;
for (const id of new Set(litIds)){ domChecked++; ok(htmlIds.has(id), 'getElementById target missing in HTML: '+id); }
for (const vid of voiceIds){ domChecked++; ok(htmlIds.has('bird-'+vid), 'bird element missing: bird-'+vid); }
console.log(`  getElementById literals: ${new Set(litIds).size}, dynamic bird ids: 6, total checked: ${domChecked}`);

/* ---------- helpers to eval MEAS literals ---------- */
function extractMeasLiteral(src, name){
  const i = src.indexOf('const '+name);
  if (i<0) return null;
  const start = src.indexOf('{', i);
  let depth=0, j=start;
  for (; j<src.length; j++){ if (src[j]==='{') depth++; else if (src[j]==='}'){ depth--; if (!depth) break; } }
  return src.slice(start, j+1);
}
function evalLiteral(lit){ return vm.runInNewContext('('+lit+')', {}); }
function deepCount(a, b, tol, path, res){
  if (typeof a === 'number' && typeof b === 'number'){
    res.n++;
    const d = Math.abs(a-b);
    if (d > res.maxDev) res.maxDev = d;
    if (d > tol) res.bad.push(path+': '+a+' vs '+b);
    return;
  }
  if (Array.isArray(a) && Array.isArray(b)){
    if (a.length !== b.length){ res.bad.push(path+': length '+a.length+' vs '+b.length); return; }
    a.forEach((x,i)=>deepCount(x, b[i], tol, path+'['+i+']', res));
    return;
  }
  if (a && b && typeof a==='object' && typeof b==='object'){
    for (const k of Object.keys(a)){
      if (!(k in b)){ res.bad.push(path+'.'+k+': missing in other'); continue; }
      deepCount(a[k], b[k], tol, path+'.'+k, res);
    }
    return;
  }
  if (a !== b) res.bad.push(path+': '+(typeof a)+' '+a+' vs '+(typeof b)+' '+b);
}

/* ---------- 2a. constants: bank vs lab pages (exact port) ---------- */
console.log('== Constants audit: bank vs lab pages ==');
const LAB = { MEAS_CARDINAL:'cardinal.html', MEAS_OWL:'owl.html', MEAS_THRUSH:'hermit-thrush.html',
  MEAS_WREN:'carolina-wren.html', MEAS_SPARROW:'song-sparrow.html', MEAS_TOWHEE:'eastern-towhee.html' };
const bankMeas = {};
for (const [name, file] of Object.entries(LAB)){
  const labSrc = fs.readFileSync(DIR+file,'utf8');
  const bankObj = evalLiteral(extractMeasLiteral(script, name));
  const labObj = evalLiteral(extractMeasLiteral(labSrc, 'MEAS'));
  bankMeas[name] = bankObj;
  const res = { n:0, bad:[], maxDev:0 };
  deepCount(bankObj, labObj, 0, name, res);
  console.log(`  ${name}: ${res.n} numeric leaves compared, mismatches: ${res.bad.length}`);
  res.bad.slice(0,5).forEach(b=>console.log('    ', b));
  ok(res.bad.length===0, name+' differs from lab page');
}

/* ---------- 2b. constants: bank vs measurements JSONs ---------- */
console.log('== Constants audit: bank vs measurements JSONs ==');
const J = f => JSON.parse(fs.readFileSync(DIR+'analysis/'+f,'utf8'));
function triple(o){ return o ? [o.min, o.median, o.max] : null; }
function cmpNum(a, b, tol, label, res){ res.n++; const d=Math.abs(a-b); if (d>res.maxDev) res.maxDev=d; if (d>tol) res.bad.push(label+': '+a+' vs '+b); }
function cmpArr(a, b, tol, label, res){ if (!Array.isArray(a)||!Array.isArray(b) || a.length!==b.length){ res.bad.push(label+': array mismatch'); return; } a.forEach((x,i)=>cmpNum(x, b[i], tol, label+'['+i+']', res)); }
function tonalVsJson(M, Jd, typeMap, opts){
  const res = { n:0, bad:[], maxDev:0 };
  for (const [bk, jk] of Object.entries(typeMap)){
    const T = M.types[bk], P = Jd.phrase_types[jk];
    if (!T || !P){ res.bad.push('missing type '+bk+'/'+jk); continue; }
    cmpArr(T.contour, P.contour_template_hz, 0.15, bk+'.contour', res);
    cmpArr(T.amp, P.amp_template, 0.0011, bk+'.amp', res);
    cmpNum(T.durMed, P.dur_s.median, 0.0011, bk+'.durMed', res);
    cmpNum(T.durMin, P.dur_s.min, 0.0011, bk+'.durMin', res);
    cmpNum(T.durMax, P.dur_s.max, 0.0011, bk+'.durMax', res);
    cmpNum(T.fStart, P.f_start_hz.median, 0.6, bk+'.fStart', res);
    cmpNum(T.fEnd, P.f_end_hz.median, 0.6, bk+'.fEnd', res);
    cmpNum(T.harm2, P.harm2_ratio.median, 0.0011, bk+'.harm2', res);
    if (opts.harm3) cmpNum(T.harm3, P.harm3_ratio.median, 0.0011, bk+'.harm3', res);
    if (opts.peakField) cmpNum(T[opts.peakField], P.peak_amp_rel.median, 0.0011, bk+'.'+opts.peakField, res);
  }
  const tr = opts.transitionsOf(M), jt = Jd.transitions;
  for (const k of Object.keys(tr)){
    if (!jt[k]){ continue; }
    cmpNum(tr[k].min, jt[k].min, 0.0011, 'tr '+k+'.min', res);
    cmpNum(tr[k].med, jt[k].median !== undefined ? jt[k].median : jt[k].med, 0.0011, 'tr '+k+'.med', res);
    cmpNum(tr[k].max, jt[k].max, 0.0011, 'tr '+k+'.max', res);
  }
  return res;
}
let r;
r = tonalVsJson(bankMeas.MEAS_CARDINAL, J('cardinal-measurements-xc75501.json'),
  {Ua:'Ua',Ub:'Ub',D:'D',C:'C'}, { transitionsOf:M=>M.grammar.transitions });
console.log(`  CARDINAL vs JSON: ${r.n} values, mismatches ${r.bad.length}, maxDev ${r.maxDev.toFixed(4)}`); r.bad.slice(0,4).forEach(b=>console.log('    ',b)); ok(r.bad.length===0,'cardinal vs json');
{ // cardinal bout pause (JSON bout_pause_s {min,median,max})
  const bp = J('cardinal-measurements-xc75501.json').bout_pause_s;
  const res={n:0,bad:[],maxDev:0};
  cmpNum(bankMeas.MEAS_CARDINAL.grammar.boutPause[0], bp.min, 0.0011, 'boutPause.min', res);
  cmpNum(bankMeas.MEAS_CARDINAL.grammar.boutPause[1], bp.median, 0.0011, 'boutPause.med', res);
  cmpNum(bankMeas.MEAS_CARDINAL.grammar.boutPause[2], bp.max, 0.0011, 'boutPause.max', res);
  console.log(`  CARDINAL pause vs JSON: ${res.n} values, mismatches ${res.bad.length}`); ok(res.bad.length===0,'cardinal pause');
}
{ // owl positions
  const Jd = J('great-horned-owl-measurements.json');
  const res = { n:0, bad:[], maxDev:0 };
  const pos = { P1:'1', P2:'2', P3:'3', P4:'4' };
  for (const [bk, jk] of Object.entries(pos)){
    const T = bankMeas.MEAS_OWL.types[bk], P = Jd.positions[jk];
    cmpArr(T.contour, P.contour_template_hz, 0.15, bk+'.contour', res);
    cmpArr(T.amp, P.amp_template, 0.0011, bk+'.amp', res);
    cmpNum(T.durMed, P.dur_s.median, 0.0011, bk+'.durMed', res);
    cmpNum(T.durMin, P.dur_s.min, 0.0011, bk+'.durMin', res);
    cmpNum(T.durMax, P.dur_s.max, 0.0011, bk+'.durMax', res);
    cmpNum(T.fStart, P.f_start_hz.median, 0.6, bk+'.fStart', res);
    cmpNum(T.fEnd, P.f_end_hz.median, 0.6, bk+'.fEnd', res);
    cmpNum(T.harm2, P.harm2_ratio.median, 0.0011, bk+'.harm2', res);
    cmpNum(T.harm3, P.harm3_ratio.median, 0.0011, bk+'.harm3', res);
  }
  for (const k of Object.keys(bankMeas.MEAS_OWL.grammar.transitions)){
    cmpNum(bankMeas.MEAS_OWL.grammar.transitions[k].med, Jd.transitions[k].period_s ? Jd.transitions[k].period_s.median : NaN, 0.0011, 'owl tr '+k, res);
  }
  cmpNum(bankMeas.MEAS_OWL.grammar.seriesPause[0], Jd.series_pause_s.median, 0.0011, 'owl seriesPause', res);
  console.log(`  OWL vs JSON: ${res.n} values, mismatches ${res.bad.length}, maxDev ${res.maxDev.toFixed(4)}`); res.bad.slice(0,4).forEach(b=>console.log('    ',b)); ok(res.bad.length===0,'owl vs json');
}
r = tonalVsJson(bankMeas.MEAS_WREN, J('carolina-wren-measurements.json'),
  {D:'D',U:'U',L:'L',S:'S'}, { harm3:true, peakField:'peak', transitionsOf:M=>M.grammar.transitions });
console.log(`  WREN vs JSON: ${r.n} values, mismatches ${r.bad.length}, maxDev ${r.maxDev.toFixed(4)}`); r.bad.slice(0,4).forEach(b=>console.log('    ',b)); ok(r.bad.length===0,'wren vs json');
r = tonalVsJson(bankMeas.MEAS_SPARROW, J('song-sparrow-measurements.json'),
  {P:'P',I:'I',B:'B',L:'L',H:'H',h:'h',M:'M',C:'C',T:'T',E:'E',W:'W'},
  { peakField:'peakRel', transitionsOf:M=>M.grammar.transitions });
console.log(`  SPARROW vs JSON: ${r.n} values, mismatches ${r.bad.length}, maxDev ${r.maxDev.toFixed(4)}`); r.bad.slice(0,4).forEach(b=>console.log('    ',b)); ok(r.bad.length===0,'sparrow vs json');
r = tonalVsJson(bankMeas.MEAS_TOWHEE, J('eastern-towhee-measurements.json'),
  {I1:'I1',I2:'I2',TRILL:'TRILL',TN:'TN'}, { peakField:'peakAmp', transitionsOf:()=>({}) });
console.log(`  TOWHEE vs JSON: ${r.n} values, mismatches ${r.bad.length}, maxDev ${r.maxDev.toFixed(4)}`); r.bad.slice(0,4).forEach(b=>console.log('    ',b)); ok(r.bad.length===0,'towhee vs json');
{ // towhee grammar triples
  const Jd = J('eastern-towhee-measurements.json'), G = bankMeas.MEAS_TOWHEE.grammar, res={n:0,bad:[],maxDev:0};
  const T = (arr, jo, label)=>{ if (!jo) { res.bad.push(label+': json field missing'); return; }
    const t = Array.isArray(jo) ? jo : [jo.min, jo.median, jo.max];
    arr.forEach((x,i)=>cmpNum(x, t[i], 0.02, label+'['+i+']', res)); };
  T(G.introGap, Jd.intro_gap_s, 'introGap');
  T(G.introTrillGap, Jd.intro_to_trill_gap_s, 'introTrillGap');
  T(G.songPause, Jd.inter_song_pause_s, 'songPause');
  T(G.trillRate, Jd.trill_rate_per_s, 'trillRate');
  T(G.trillNotes, Jd.trill_notes_per_song, 'trillNotes');
  console.log(`  TOWHEE grammar vs JSON: ${res.n} values, mismatches ${res.bad.length}`); res.bad.slice(0,4).forEach(b=>console.log('    ',b)); ok(res.bad.length===0,'towhee grammar');
}
{ // thrush
  const Jd = J('hermit-thrush-measurements.json'), M = bankMeas.MEAS_THRUSH, res={n:0,bad:[],maxDev:0};
  for (const k of ['W','S','U','D','C','u','d']){
    const T=M.types[k], P=Jd.phrase_types[k];
    if (!T || !P){ res.bad.push('missing type '+k); continue; }
    cmpArr(T.contour, P.contour_template_hz, 0.15, k+'.contour', res);
    cmpArr(T.amp, P.amp_template, 0.0011, k+'.amp', res);
    cmpNum(T.n, P.n_instances, 0, k+'.n', res);
    cmpNum(T.durMed, P.dur_s.median, 0.0011, k+'.durMed', res);
    cmpNum(T.durMin, P.dur_s.min, 0.0011, k+'.durMin', res);
    cmpNum(T.durMax, P.dur_s.max, 0.0011, k+'.durMax', res);
    cmpNum(T.fStart, P.f_start_hz.median, 0.6, k+'.fStart', res);
    cmpNum(T.fEnd, P.f_end_hz.median, 0.6, k+'.fEnd', res);
    cmpNum(T.harm2, P.harm2_ratio.median, 0.0011, k+'.harm2', res);
    cmpNum(T.harm3, P.harm3_ratio.median, 0.0011, k+'.harm3', res);
    cmpNum(T.peakRel, P.peak_amp_rel.median, 0.0011, k+'.peakRel', res);
    cmpNum(T.voice, P.voice, 0, k+'.voice', res);
    cmpNum(T.gridDur, P.grid_dur_s, 0.0011, k+'.gridDur', res);
    const trm = P.tremolo;
    if (trm && trm.rate_hz && trm.rate_hz.median != null && trm.n_measured > 0){
      cmpNum(T.tremRate, trm.rate_hz.median, 0.0011, k+'.tremRate', res);
      cmpNum(T.tremDepth, 0.45*trm.depth_index.median, 0.002, k+'.tremDepth', res);
    } else {
      cmpNum(T.tremRate, 0, 0, k+'.tremRate(zero)', res);
      cmpNum(T.tremDepth, 0, 0, k+'.tremDepth(zero)', res);
    }
  }
  for (const k of Object.keys(M.grammar.transitions)){
    const jt = Jd.transitions[k];
    if (!jt){ res.bad.push('json missing transition '+k); continue; }
    cmpNum(M.grammar.transitions[k].min, jt.period_s.min, 0.0011, 'tr '+k+'.min', res);
    cmpNum(M.grammar.transitions[k].med, jt.period_s.median, 0.0011, 'tr '+k+'.med', res);
    cmpNum(M.grammar.transitions[k].max, jt.period_s.max, 0.0011, 'tr '+k+'.max', res);
    cmpNum(M.grammar.transitions[k].grid, jt.grid_period_s, 0.0011, 'tr '+k+'.grid', res);
  }
  cmpNum(M.grammar.songPause[0], Jd.song_pause_s.min, 0.0011, 'songPause.min', res);
  cmpNum(M.grammar.songPause[1], Jd.song_pause_s.median, 0.0011, 'songPause.med', res);
  cmpNum(M.grammar.songPause[2], Jd.song_pause_s.max, 0.0011, 'songPause.max', res);
  cmpNum(M.grammar.gridSongPause, Jd.grid_song_pause_s, 0.0011, 'gridSongPause', res);
  cmpArr(M.ladder, Jd.songs.map(s=>s.base_freq_hz), 0.15, 'ladder', res);
  // measured song forms: type sequence + freqScale = f_med / type template base
  // (template base = numpy median of the type's 16-point contour template)
  const base = {};
  for (const k of Object.keys(Jd.phrase_types)){
    const c = [...Jd.phrase_types[k].contour_template_hz].sort((a,b)=>a-b);
    base[k] = (c[7]+c[8])/2;
  }
  M.grammar.forms.forEach((form, fi)=>{
    const js = Jd.songs[fi];
    if (!js){ res.bad.push('json missing song '+fi); return; }
    if (form.length !== js.form.length){ res.bad.push('form '+fi+' length '+form.length+' vs '+js.form.length); return; }
    form.forEach((el, ni)=>{
      if (el.t !== js.form[ni].type) res.bad.push('form '+fi+'['+ni+'] type '+el.t+' vs '+js.form[ni].type);
      cmpNum(el.s, js.form[ni].f_med_hz / base[el.t], 0.0011, 'form '+fi+'['+ni+'].s', res);
    });
  });
  console.log(`  THRUSH vs JSON: ${res.n} values, mismatches ${res.bad.length}, maxDev ${res.maxDev.toFixed(4)}`); res.bad.slice(0,5).forEach(b=>console.log('    ',b)); ok(res.bad.length===0,'thrush vs json');
}

/* ---------- 2c. pre/post swap: the other five voices' literals unchanged ---------- */
console.log('== Pre/post swap identity (five unchanged voices) ==');
{
  const PRE = '/tmp/syrinx6-pre-swap.html';
  if (fs.existsSync(PRE)){
    const preScript = fs.readFileSync(PRE,'utf8').split('<script>')[1].split('</script>')[0];
    for (const name of ['MEAS_CARDINAL','MEAS_OWL','MEAS_WREN','MEAS_SPARROW','MEAS_TOWHEE']){
      const a = extractMeasLiteral(script, name), b = extractMeasLiteral(preScript, name);
      console.log(`  ${name}: literal byte-identical to pre-swap bank: ${a===b}`);
      ok(a===b, name+' literal changed vs pre-swap bank');
    }
  } else {
    console.log('  (pre-swap snapshot /tmp/syrinx6-pre-swap.html not present; identity check skipped)');
  }
}

/* ---------- 3. static breath-path audit ---------- */
console.log('== Static breath-path audit ==');
const discCount = (script.match(/disconnect/g)||[]).length;
console.log('  occurrences of "disconnect" in script:', discCount);
ok(discCount===0, 'disconnect present');
const bufSrcCount = (script.match(/createBufferSource\(\)/g)||[]).length;
console.log('  createBufferSource() sites:', bufSrcCount, '(expect 1 builder site — buildTonal, shared by all six voices; runtime instance count = 6 asserted by the harness)');
ok(bufSrcCount===1, 'buffer source builder sites != 1');
const breathConnect = (script.match(/breathEnv\.connect/g)||[]).length;
const breathTrimConnect = (script.match(/breathTrim\.connect/g)||[]).length;
const noiseEnvConnect = (script.match(/noiseEnv\.connect/g)||[]).length;
const noiseTrimConnect = (script.match(/noiseTrim\.connect/g)||[]).length;
console.log(`  breathEnv.connect sites: ${breathConnect}, breathTrim.connect: ${breathTrimConnect} (expect 1 each, in buildTonal); noiseEnv/noiseTrim sites: ${noiseEnvConnect}/${noiseTrimConnect} (expect 0 — the heron noise engine is gone)`);
ok(breathConnect===1 && breathTrimConnect===1 && noiseEnvConnect===0 && noiseTrimConnect===0, 'breath path connect sites');
ok(!/noiseEnv|noiseTrim|noiseBusy/.test(script), 'stale noise-path identifiers remain');
ok(!/heron/i.test(html), 'stale "heron" reference remains in syrinx6.html');
ok(!/MEAS_HERON|HERON_/.test(script), 'stale heron identifiers remain');
function fnBody(name){
  const i = script.indexOf('function '+name);
  if (i<0) return '';
  const start = script.indexOf('{', i);
  let depth=0, j=start;
  for (; j<script.length; j++){ if (script[j]==='{') depth++; else if (script[j]==='}'){ depth--; if (!depth) break; } }
  return script.slice(start, j+1);
}
for (const fn of ['tonalPlay','thrushPlay','synthNote']){
  const body = fnBody(fn);
  const bad = /breathEnv\.connect|breathTrim\.connect|noiseEnv\.connect|noiseTrim\.connect/.test(body);
  console.log(`  ${fn}: wiring calls on the breath path inside note renderer: ${bad ? 'FOUND (bad)' : 'none'}`);
  ok(!bad, fn+' touches breath wiring');
}
const breathCurveSites = (script.match(/breathEnv\.gain\.setValueCurveAtTime/g)||[]).length;
const noiseCurveSites = (script.match(/noiseEnv\.gain\.setValueCurveAtTime/g)||[]).length;
console.log(`  breath envelope writers: breathEnv curves ${breathCurveSites} (expect 2: tonalPlay + thrushPlay), noiseEnv curves ${noiseCurveSites} (expect 0)`);
ok(breathCurveSites===2 && noiseCurveSites===0, 'envelope writer count');
{ // thrush tremolo: LFO on a series gain in the note's own chain, as in the lab page
  const body = fnBody('thrushPlay');
  const has = /tremRate/.test(body) && /tremDepth/.test(body) && /lg\.connect\(tg\.gain\)/.test(body) && /regSrc\(v, lfo\)/.test(body);
  console.log(`  thrushPlay tremolo block (tremRate/tremDepth, LFO gain -> tg.gain, LFO registered for STOP): ${has ? 'present' : 'MISSING'}`);
  ok(has, 'thrushPlay tremolo block incomplete');
}

console.log(`\nAUDIT RESULT: ${pass} checks passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
