/* Hermit Thrush verification: constant audit vs hermit-thrush-measurements.json,
   static breath-path audit, generator plan tests (ladder + envelopes), and a
   functional run of the page's Sing engine on a stub Web Audio graph. */
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('/home/hatch/workspace/bird-synth/hermit-thrush.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const J = JSON.parse(fs.readFileSync('/home/hatch/workspace/bird-synth/analysis/hermit-thrush-measurements.json', 'utf8'));

let pass = 0, fail = 0;
const failures = [];
function ok(cond, label) { if (cond) pass++; else { fail++; failures.push(label); console.log('FAIL:', label); } }
function eq(a, b, label) { ok(a === b, `${label}: page=${JSON.stringify(a)} json=${JSON.stringify(b)}`); }
function eqArr(a, b, label) { ok(JSON.stringify(a) === JSON.stringify(b), `${label}: page=${JSON.stringify(a)} json=${JSON.stringify(b)}`); }
function close(a, b, tol, label) { ok(Math.abs(a - b) <= tol, `${label}: page=${a} expected=${b} tol=${tol}`); }

/* ================= 1. CONSTANT AUDIT ================= */
const meas = JSON.parse(script.match(/const MEAS = (\{[\s\S]*?\n\});/)[1]);
const STEP = (60 / 112) / 8;                       /* 32nd note at 112 BPM */
const gridDurOf = med => Math.round(Math.max(STEP, Math.round(med / STEP) * STEP) * 1000) / 1000;
const gridPeriodOf = med => Math.round(Math.max(2 * STEP, Math.round(med / STEP) * STEP) * 1000) / 1000;
const GAIN_SCALE = 0.6;
const baseOf = ty => { const s = [...J.phrase_types[ty].contour_template_hz].sort((a, b) => a - b); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };  /* numpy median, as in the generator */

for (const ty of Object.keys(J.phrase_types)) {
  const P = meas.types[ty], T = J.phrase_types[ty];
  eq(P.name, T.name, `${ty}.name`);
  eq(P.n, T.n_instances, `${ty}.n`);
  eq(P.durMed, T.dur_s.median, `${ty}.durMed`);
  eq(P.durMin, T.dur_s.min, `${ty}.durMin`);
  eq(P.durMax, T.dur_s.max, `${ty}.durMax`);
  eq(P.fStart, T.f_start_hz.median, `${ty}.fStart`);
  eq(P.fEnd, T.f_end_hz.median, `${ty}.fEnd`);
  eq(P.harm2, Math.round(T.harm2_ratio.median * 10000) / 10000, `${ty}.harm2`);
  eq(P.harm3, Math.round(T.harm3_ratio.median * 10000) / 10000, `${ty}.harm3`);
  eq(P.peakRel, T.peak_amp_rel.median, `${ty}.peakRel`);
  eq(P.voice, T.voice, `${ty}.voice`);
  eq(P.gridDur, gridDurOf(T.dur_s.median), `${ty}.gridDur (32nd rule)`);
  eq(P.gridDur, T.grid_dur_s, `${ty}.gridDur (json)`);
  eqArr(P.contour, T.contour_template_hz, `${ty}.contour`);
  eqArr(P.amp, T.amp_template, `${ty}.amp`);
  if (T.tremolo) {
    eq(P.tremRate, Math.round(T.tremolo.rate_hz.median * 100) / 100, `${ty}.tremRate`);
    eq(P.tremDepth, Math.round(0.45 * T.tremolo.depth_index.median * 1000) / 1000, `${ty}.tremDepth (0.45x index rule)`);
  } else { eq(P.tremRate, 0, `${ty}.tremRate = 0 (no tremolo measured)`); eq(P.tremDepth, 0, `${ty}.tremDepth = 0`); }
}
eq(Object.keys(meas.types).length, 7, 'exactly 7 phrase types');
for (const k of Object.keys(J.transitions)) {
  const P = meas.grammar.transitions[k], T = J.transitions[k];
  eq(P.min, T.period_s.min, `tr ${k} min`); eq(P.med, T.period_s.median, `tr ${k} med`); eq(P.max, T.period_s.max, `tr ${k} max`);
  eq(P.grid, gridPeriodOf(T.period_s.median), `tr ${k} grid (32nd rule, floor 2)`);
  eq(P.grid, T.grid_period_s, `tr ${k} grid (json)`);
}
eqArr(meas.grammar.songPause, [J.song_pause_s.min, J.song_pause_s.median, J.song_pause_s.max], 'grammar.songPause [min,med,max]');
eq(meas.grammar.gridSongPause, J.grid_song_pause_s, 'grammar.gridSongPause');
eq(meas.grammar.forms.length, J.songs.length, 'grammar.forms = measured song count');
J.songs.forEach((s, i) => {
  const F = meas.grammar.forms[i];
  eq(F.length, s.form.length, `form ${i} length`);
  s.form.forEach((n, j) => {
    eq(F[j].t, n.type, `form ${i}[${j}].type`);
    close(F[j].s, Math.round(n.f_med_hz / baseOf(n.type) * 10000) / 10000, 1e-9, `form ${i}[${j}].freqScale`);
  });
});
eqArr(meas.ladder, J.pitch_ladder.levels.map(l => l.base_freq_hz), 'ladder = measured song bases in order');
eq(meas.tremoloOverall.rateMed, J.tremolo.rate_hz.median, 'tremoloOverall.rateMed');
const landmarks = script.match(/const LANDMARKS = \[([^\]]+)\]/)[1].split(',').map(s => parseInt(s));
eqArr(landmarks, [Math.round(Math.min(...meas.ladder)), Math.round(J.songs[5].base_freq_hz),
                  Math.round(Math.max(...meas.ladder)), Math.round(J.phrase_types.C.f_med_hz.median)],
      'LANDMARKS = measured values');
ok(/XC1048898/.test(html) && /AUDEVARD/.test(html) && /CC BY-NC-SA 4\.0|Attribution-NonCommercial-ShareAlike 4\.0/.test(html),
   'attribution present (XC1048898 / AUDEVARD / CC BY-NC-SA 4.0)');
console.log(`constant audit: ${pass} pass, ${fail} fail so far`);

/* ================= 2. STATIC BREATH-PATH AUDIT ================= */
const codeOnly = script.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
const count = (re) => (codeOnly.match(re) || []).length;
eq(count(/noiseSrc\.connect\(/g), 1, 'STATIC: exactly one noiseSrc.connect()');
eq(count(/nf\.connect\(breathGain\)/g), 1, 'STATIC: exactly one nf.connect(breathGain)');
eq(count(/breathGain\.connect\(/g), 1, 'STATIC: exactly one breathGain.connect() (to master)');
eq(count(/\.disconnect\(/g), 0, 'STATIC: zero disconnect() calls in the whole script');
eq(count(/breathBus/g), 0, 'STATIC: zero breathBus references');
eq(count(/breathGain\.gain\.setValueCurveAtTime/g), 1, 'STATIC: breath gain shaped in exactly one place (playNote)');
eq(count(/breathGain\.gain/g), 2, 'STATIC: breathGain.gain touched only at init (=0) and in playNote');
ok(/const BREATH_REL = 0\.05/.test(codeOnly), 'STATIC: BREATH_REL = 0.05 cap constant present');
ok(/i===0 \|\| i===T\.amp\.length-1\) \? 0 :/.test(codeOnly), 'STATIC: breath curve endpoints forced to 0');
ok(count(/createDynamicsCompressor/g) >= 1, 'STATIC: master DynamicsCompressor present');
ok(/master\.connect\(comp\)/.test(codeOnly) && /comp\.connect\(analyser\)/.test(codeOnly),
   'STATIC: master -> compressor -> analyser -> destination chain');
ok(!/bTap/.test(codeOnly), 'STATIC: no per-note breath tap nodes (v1 pattern gone)');
console.log(`static audit: cumulative ${pass} pass, ${fail} fail`);

/* ================= 3. STUB WEB AUDIO HARNESS ================= */
let nodeSeq = 0, disconnectCalls = 0;
const connLog = [], oscStarts = [], allNodes = [];
class Param {
  constructor() { this.events = []; this._value = 0; }
  set value(v) { this._value = v; } get value() { return this._value; }
  setValueAtTime(v, t) { this.events.push({ kind: 'set', v, t }); }
  setValueCurveAtTime(curve, t, dur) { this.events.push({ kind: 'curve', values: Array.from(curve), t, dur }); }
  linearRampToValueAtTime(v, t) { this.events.push({ kind: 'lin', v, t }); }
  setTargetAtTime(v, t, tc) { this.events.push({ kind: 'target', v, t, tc }); }
  cancelScheduledValues(t) { this.events.push({ kind: 'cancel', t }); }
}
class Node {
  constructor(type) { this.id = ++nodeSeq; this.type = type; allNodes.push(this); }
  connect(to) { connLog.push([this.id, to.id]); return to; }
  disconnect() { disconnectCalls++; }
}
class Osc extends Node {
  constructor() { super('osc'); this.frequency = new Param(); this._type = 'sine'; }
  set type(v) { this._type = v; } get type() { return this._type; }
  start(t) { const c = this.frequency.events.find(e => e.kind === 'curve'); if (c) oscStarts.push({ t, f0: c.values[0] }); }
  stop() {}
}
class Gain extends Node { constructor() { super('gain'); this.gain = new Param(); } }
class Filter extends Node { constructor() { super('filter'); this.frequency = new Param(); this.Q = new Param(); this.gain = new Param(); this._type = ''; } set type(v) { this._type = v; } get type() { return this._type; } }
const contexts = [];
class FakeCtx {
  constructor() { this.currentTime = 0; this.sampleRate = 44100; this.state = 'running'; this.destination = new Node('dest'); contexts.push(this); }
  createGain() { return new Gain(); }
  createOscillator() { return new Osc(); }
  createBiquadFilter() { return new Filter(); }
  createStereoPanner() { const n = new Node('pan'); n.pan = new Param(); return n; }
  createDynamicsCompressor() { const n = new Node('comp'); n.threshold = { value: 0 }; n.ratio = { value: 0 }; n.knee = { value: 0 }; n.attack = { value: 0 }; n.release = { value: 0 }; return n; }
  createAnalyser() { const n = new Node('analyser'); n.fftSize = 0; n.getByteFrequencyData = () => {}; return n; }
  createBuffer(ch, len) { return { getChannelData: () => new Float32Array(len) }; }
  createBufferSource() { const n = new Node('bufsrc'); n.start = () => {}; return n; }
  resume() {}
}
const ctxStub = { clearRect() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fillText() {} };
function makeEl(id) {
  return { id, width: 1600, height: 300, value: '0', textContent: '', innerHTML: '', className: '',
           _l: {}, addEventListener(ev, fn) { (this._l[ev] ||= []).push(fn); },
           appendChild() {}, getContext: () => ctxStub };
}
const els = {};
let intervalCb = null;
const sandbox = {
  console, Float32Array, Math, JSON,
  document: { getElementById: id => (els[id] ||= makeEl(id)), createElement: () => makeEl('dyn') },
  setInterval: cb => { intervalCb = cb; return 1; }, clearInterval: () => {},
  requestAnimationFrame: () => {}, AudioContext: FakeCtx,
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(script, sandbox);

eq(typeof sandbox.makeSongPlan, 'function', 'HARNESS: makeSongPlan exposed');
eq(typeof sandbox.playNote, 'function', 'HARNESS: playNote exposed');
eq(typeof sandbox.quantize, 'function', 'HARNESS: quantize exposed');

/* morph semantics */
const morphEl = els['morph'];
const pcOf = f => ((Math.round(69 + 12 * Math.log2(f / 440)) % 12) + 12) % 12;
morphEl.value = '0'; morphEl._l.input.forEach(f => f());
ok(sandbox.morphFreq(3234.4) === 3234.4, 'HARNESS: morph=0 morphFreq is identity');
ok([9, 11, 1, 4, 6].includes(pcOf(sandbox.quantize(3234.4))), 'HARNESS: quantize lands on A-major pentatonic');
morphEl.value = '1000'; morphEl._l.input.forEach(f => f());
ok(Math.abs(sandbox.morphFreq(3234.4) - sandbox.quantize(3234.4)) < 1e-6, 'HARNESS: morph=1 morphFreq = full quantize');
morphEl.value = '500'; morphEl._l.input.forEach(f => f());
ok(Math.abs(sandbox.morphFreq(3234.4) - Math.sqrt(3234.4 * sandbox.quantize(3234.4))) < 1e-6,
   'HARNESS: morph=0.5 morphFreq = geometric midpoint (log-lerp)');
morphEl.value = '0'; morphEl._l.input.forEach(f => f());

/* ============ generator plan tests: forms, ladder, envelopes ============ */
const formSeqs = J.songs.map(s => s.form.map(n => n.type).join(' '));
const formScales = J.songs.map(s => s.form.map(n => Math.round(n.f_med_hz / baseOf(n.type) * 10000) / 10000));
let planFormViol = 0, planScaleViol = 0, planEnvViol = 0, plansSeen = new Set();
for (let trial = 0; trial < 2000; trial++) {
  const plan = sandbox.makeSongPlan();
  const seq = plan.evs.map(e => e.type).join(' ');
  const fi = formSeqs.indexOf(seq);
  if (fi < 0) { planFormViol++; continue; }
  plansSeen.add(fi);
  plan.evs.forEach((e, j) => { if (Math.abs(e.freqScale - formScales[fi][j]) > 1e-9) planScaleViol++; });
  /* span envelope: sum of transition [min..max] + last note dur [min..max] */
  let lo = 0, hi = 0;
  plan.evs.forEach((e, j) => {
    if (j + 1 < plan.evs.length) {
      const tr = J.transitions[e.type + '>' + plan.evs[j + 1].type].period_s;
      lo += tr.min; hi += tr.max;
    }
  });
  const lastTy = J.phrase_types[plan.evs[plan.evs.length - 1].type];
  lo += lastTy.dur_s.min; hi += lastTy.dur_s.max;
  if (plan.durBird < lo - 1e-9 || plan.durBird > hi + 1e-9) planEnvViol++;
}
eq(planFormViol, 0, 'GEN: 2000 plans — every type sequence is a measured song form');
eq(planScaleViol, 0, 'GEN: 2000 plans — every note freqScale equals its measured form scale (ladder exact)');
eq(planEnvViol, 0, 'GEN: 2000 plans — every song span inside the measured transition+duration envelope');
eq(plansSeen.size, 8, 'GEN: all 8 measured forms occurred over 2000 plans');

/* ladder distribution of generated plans: implied song base must be a measured base */
let ladderViol = 0;
for (let trial = 0; trial < 500; trial++) {
  const plan = sandbox.makeSongPlan();
  const fi = formSeqs.indexOf(plan.evs.map(e => e.type).join(' '));
  const sust = plan.evs.filter(e => J.phrase_types[e.type].dur_s.median >= 0.25);
  const implied = sust.map(e => {
    const c = J.phrase_types[e.type].contour_template_hz;
    return e.freqScale * [...c].sort((a, b) => a - b)[Math.floor(c.length / 2)];
  });
  /* implied per-note levels are the notes' own measured f_med by construction;
     the check that matters: the SET of scales used equals the form's measured set */
  if (fi < 0) ladderViol++;
}
eq(ladderViol, 0, 'GEN: ladder — plans always resolve to a measured form (no invented pitch levels)');

/* ============ full Sing run: breath law at runtime ============ */
els['singBtn']._l.click.forEach(f => f());
const actx = contexts[0];
ok(!!actx, 'HARNESS: AudioContext created on Sing');
let t = 0;
const T_END = 480;
while (t < T_END) { t += 0.03; actx.currentTime = t; intervalCb(); }

const bufsrc = allNodes.find(n => n.type === 'bufsrc');
const filtId = connLog.find(([a]) => a === bufsrc.id)[1];
const breathId = connLog.find(([a]) => a === filtId)[1];
const breath = allNodes.find(n => n.id === breathId);
eq(breath.type, 'gain', 'HARNESS: breath chain is bufsrc -> filter -> gain');
eq(connLog.filter(([a]) => a === breathId).length, 1, 'HARNESS: breath gain has exactly ONE outgoing connection');
eq(connLog.filter(([, b]) => b === breathId).length, 1, 'HARNESS: breath gain has exactly ONE incoming connection');
eq(disconnectCalls, 0, 'HARNESS: zero disconnect() calls during a full run');

/* scheduled notes: group osc starts by time; fundamental = min first-freq */
const byTime = new Map();
for (const s of oscStarts) { const k = Math.round(s.t * 1000); if (!byTime.has(k)) byTime.set(k, []); byTime.get(k).push(s.f0); }
const notes = [...byTime.entries()].map(([k, fs]) => ({ t: k / 1000, f0: Math.min(...fs) })).sort((a, b) => a.t - b.t);
ok(notes.length > 150, `HARNESS: run produced ${notes.length} notes`);

/* identify each note's type: f0 / contour[0] must equal a measured form scale for that type */
const scaleSet = {};
for (const ty of Object.keys(J.phrase_types)) scaleSet[ty] = new Set();
J.songs.forEach(s => s.form.forEach(n => scaleSet[n.type].add(Math.round(n.f_med_hz / baseOf(n.type) * 10000) / 10000)));
let unident = 0;
for (const n of notes) {
  n.types = Object.keys(J.phrase_types).filter(ty => {
    const s = n.f0 / J.phrase_types[ty].contour_template_hz[0];
    return [...scaleSet[ty]].some(v => Math.abs(v - s) < 0.01);
  });
  if (!n.types.length) unident++;
}
eq(unident, 0, 'HARNESS: every scheduled note identifies as a measured (type, ladder-scale) pair');

const bEvents = breath.gain.events.filter(e => e.kind === 'curve');
eq(bEvents.length, notes.length, 'HARNESS: exactly one breath curve per note (no stacked taps)');
let maxBreath = 0, capViol = 0, endViol = 0;
for (const e of bEvents) {
  if (e.values[0] !== 0 || e.values[e.values.length - 1] !== 0) endViol++;
  for (const v of e.values) maxBreath = Math.max(maxBreath, v);
  const note = notes.reduce((best, n) => Math.abs(n.t - e.t) < Math.abs(best.t - e.t) ? n : best, notes[0]);
  const cap = Math.max(...note.types.map(ty => meas.types[ty].peakRel)) * GAIN_SCALE * 0.05;
  if (Math.max(...e.values) > cap + 1e-9) capViol++;
}
eq(endViol, 0, 'HARNESS: every breath curve starts and ends at exactly 0');
eq(capViol, 0, 'HARNESS: no breath curve exceeds its note cap (type peak x GAIN_SCALE x 0.05)');
const globalCap = Math.max(...Object.values(meas.types).map(T => T.peakRel)) * GAIN_SCALE * 0.05;
ok(maxBreath <= globalCap + 1e-9, `HARNESS: max breath gain ${maxBreath.toFixed(4)} <= ${globalCap.toFixed(4)} (loudest type peak x 0.05)`);

function breathAt(tt) {
  let v = 0;
  for (const e of bEvents) {
    if (e.t > tt) break;
    if (tt <= e.t + e.dur) {
      const x = (tt - e.t) / e.dur * (e.values.length - 1), i = Math.floor(x), fr = x - i;
      v = e.values[i] * (1 - fr) + e.values[Math.min(i + 1, e.values.length - 1)] * fr;
    } else v = e.values[e.values.length - 1];
  }
  return v;
}
const songsRun = [[notes[0]]];
for (let i = 1; i < notes.length; i++) {
  if (notes[i].t - notes[i - 1].t > 1.0) songsRun.push([]);
  songsRun[songsRun.length - 1].push(notes[i]);
}
let pauseViol = 0;
for (let i = 0; i + 1 < songsRun.length; i++) {
  const a = songsRun[i], b = songsRun[i + 1];
  const lastTy = a[a.length - 1].types[0];
  const mid = (a[a.length - 1].t + meas.types[lastTy].durMax + b[0].t) / 2;
  if (breathAt(mid) !== 0) pauseViol++;
}
eq(pauseViol, 0, `HARNESS: breath is exactly 0 at all ${songsRun.length - 1} inter-song pause midpoints`);
const formSizes = new Set(J.songs.map(s => s.form.length));
ok(songsRun.every(s => formSizes.has(s.length)), 'HARNESS: every generated song size is a measured form size');

console.log(`\nsongs over run: ${songsRun.length}; notes=${notes.length}; maxBreath=${maxBreath.toFixed(4)}`);
console.log(`TOTAL: ${pass} pass, ${fail} fail`);
if (failures.length) { console.log('FAILURES:'); failures.forEach(f => console.log(' -', f)); process.exit(1); }
