/* Gate 1 v2 verification: constant audit vs cardinal-measurements-xc75501.json,
   static breath-path audit, and a functional run of the page's Sing engine on a
   stub Web Audio graph (records every scheduled breath-gain value). */
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('/home/hatch/workspace/bird-synth/cardinal.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const J = JSON.parse(fs.readFileSync('/home/hatch/workspace/bird-synth/analysis/cardinal-measurements-xc75501.json', 'utf8'));

let pass = 0, fail = 0;
const failures = [];
function ok(cond, label) { if (cond) pass++; else { fail++; failures.push(label); console.log('FAIL:', label); } }
function eq(a, b, label) { ok(a === b, `${label}: page=${JSON.stringify(a)} json=${JSON.stringify(b)}`); }
function eqArr(a, b, label) { ok(JSON.stringify(a) === JSON.stringify(b), `${label}: page=${JSON.stringify(a)} json=${JSON.stringify(b)}`); }

/* ================= 1. CONSTANT AUDIT ================= */
const meas = JSON.parse(script.match(/const MEAS = (\{[\s\S]*?\n\});/)[1]);
const SIXTEENTH = 60 / 112 / 4;
const gridOf = med => Math.round(Math.max(1, Math.round(med / SIXTEENTH)) * SIXTEENTH * 10000) / 10000;
const maxAmp = Math.max(...Object.values(J.phrase_types).map(T => T.peak_amp_rel.median));
const VOICE = { Ua: 1, Ub: 1, D: 0, C: 1 };

for (const ty of ['Ua', 'Ub', 'D', 'C']) {
  const P = meas.types[ty], T = J.phrase_types[ty];
  eq(P.n, T.n_instances, `${ty}.n`);
  eq(P.durMed, T.dur_s.median, `${ty}.durMed`);
  eq(P.durMin, T.dur_s.min, `${ty}.durMin`);
  eq(P.durMax, T.dur_s.max, `${ty}.durMax`);
  eq(P.fStart, Math.round(T.f_start_hz.median * 10) / 10, `${ty}.fStart`);
  eq(P.fEnd, Math.round(T.f_end_hz.median * 10) / 10, `${ty}.fEnd`);
  eq(P.harm2, T.harm2_ratio.median, `${ty}.harm2`);
  eqArr(P.contour, T.contour_template_hz, `${ty}.contour`);
  eqArr(P.amp, T.amp_template, `${ty}.amp`);
  eq(P.gridDur, gridOf(T.dur_s.median), `${ty}.gridDur (16th rule)`);
  eq(P.peak, Math.round(0.46 * T.peak_amp_rel.median / maxAmp * 1000) / 1000, `${ty}.peak (formula)`);
  eq(P.voice, VOICE[ty], `${ty}.voice`);
}
for (const k of ['Ua>Ub', 'Ub>D', 'D>D', 'D>C', 'C>C']) {
  const P = meas.grammar.transitions[k], T = J.transitions[k].period_s;
  eq(P.min, T.min, `tr ${k} min`); eq(P.med, T.median, `tr ${k} med`); eq(P.max, T.max, `tr ${k} max`);
  eq(P.grid, gridOf(T.median), `tr ${k} grid (16th rule)`);
}
eqArr(meas.grammar.boutPause, [J.bout_pause_s.min, J.bout_pause_s.median, J.bout_pause_s.max], 'grammar.boutPause');
eq(meas.grammar.gridBoutPause, 4.286, 'grammar.gridBoutPause (design: 8 beats @112)');
eq(meas.grammar.forms.A, 3 / 5, 'forms.A = 3/5 observed');
eq(meas.grammar.forms.B, 1 / 5, 'forms.B = 1/5 observed');
eq(meas.grammar.forms.C, 1 / 5, 'forms.C = 1/5 observed');
eqArr(meas.grammar.aRun, [4, 5, 6], 'aRun = observed A-form D-run lengths');
eq(meas.grammar.bRun, 7, 'bRun = observed B-form C-run length');
eq(meas.grammar.cRun, 10, 'cRun = observed C-form length');
const landmarks = script.match(/const LANDMARKS = \[([^\]]+)\]/)[1].split(',').map(s => parseInt(s));
eqArr(landmarks, [Math.round(J.phrase_types.D.f_end_hz.median), Math.round(J.phrase_types.D.f_peak_hz.median),
                  Math.round(J.phrase_types.Ua.f_end_hz.median), Math.round(J.phrase_types.C.f_start_hz.median)],
      'LANDMARKS = measured medians');
eq(Object.keys(meas.types).length, 4, 'exactly 4 phrase types (Kentucky types + W retired)');
ok(!/XC1093538|XC10170/.test(script.replace(/retired|Kentucky/g, '')), 'no live references to retired sources in code');
console.log(`constant audit: ${pass} pass, ${fail} fail so far`);

/* ================= 2. STATIC BREATH-PATH AUDIT ================= */
/* connection/count checks run on comment-stripped code so prose mentions don't count */
const codeOnly = script.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
const count = (re) => (codeOnly.match(re) || []).length;
eq(count(/noiseSrc\.connect\(/g), 1, 'STATIC: exactly one noiseSrc.connect()');
eq(count(/nf\.connect\(breathGain\)/g), 1, 'STATIC: exactly one nf.connect(breathGain)');
eq(count(/breathGain\.connect\(/g), 1, 'STATIC: exactly one breathGain.connect() (to master)');
eq(count(/\.disconnect\(/g), 0, 'STATIC: zero disconnect() calls in the whole script');
eq(count(/breathBus/g), 0, 'STATIC: zero breathBus references (v1 bus gone)');
eq(count(/breathGain\.gain\.setValueCurveAtTime/g), 1, 'STATIC: breath gain shaped in exactly one place (playNote)');
eq(count(/breathGain\.gain/g), 2, 'STATIC: breathGain.gain touched only at init (=0) and in playNote');
ok(/const BREATH_REL = 0\.05/.test(codeOnly), 'STATIC: BREATH_REL = 0.05 cap constant present');
ok(/i===0 \|\| i===T\.amp\.length-1\) \? 0 :/.test(codeOnly), 'STATIC: breath curve endpoints forced to 0');
ok(count(/createDynamicsCompressor/g) >= 1, 'STATIC: master DynamicsCompressor present');
ok(/master\.connect\(comp\)/.test(codeOnly) && /comp\.connect\(analyser\)/.test(codeOnly),
   'STATIC: master -> compressor -> analyser -> destination chain');
ok(!/bTap/.test(codeOnly), 'STATIC: no per-note breath tap nodes (v1 pattern gone)');
console.log(`static audit: cumulative ${pass} pass, ${fail} fail`);

/* ================= 3. FUNCTIONAL HARNESS (stub Web Audio) ================= */
let nodeSeq = 0, disconnectCalls = 0;
const connLog = [];            /* [fromId, toId] */
const oscStarts = [];          /* {t, firstFreq} for fundamental oscs */
const allNodes = [];
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
  createDynamicsCompressor() { const n = new Node('comp'); n.threshold = { value: 0 }; n.ratio = { value: 0 }; n.knee = { value: 0 }; return n; }
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

eq(typeof sandbox.makeBoutPlan, 'function', 'HARNESS: makeBoutPlan exposed');
eq(typeof sandbox.playNote, 'function', 'HARNESS: playNote exposed');
eq(typeof sandbox.quantize, 'function', 'HARNESS: quantize exposed');

/* morph semantics spot-checks via the captured input handler.
   quantize(f) is the full snap (not morph-aware); morphFreq is the morph-aware lerp. */
const morphEl = els['morph'];
const pcOf = f => ((Math.round(69 + 12 * Math.log2(f / 440)) % 12) + 12) % 12;
morphEl.value = '0'; morphEl._l.input.forEach(f => f());
ok(sandbox.morphFreq(3079.2) === 3079.2, 'HARNESS: morph=0 morphFreq is identity');
ok([9, 11, 1, 4, 6].includes(pcOf(sandbox.quantize(3079.2))), 'HARNESS: quantize lands on the A-major pentatonic scale');
morphEl.value = '1000'; morphEl._l.input.forEach(f => f());
ok(Math.abs(sandbox.morphFreq(3079.2) - sandbox.quantize(3079.2)) < 1e-6, 'HARNESS: morph=1 morphFreq = full quantize');
morphEl.value = '500'; morphEl._l.input.forEach(f => f());
ok(Math.abs(sandbox.morphFreq(3079.2) - Math.sqrt(3079.2 * sandbox.quantize(3079.2))) < 1e-6,
   'HARNESS: morph=0.5 morphFreq = geometric midpoint (log-lerp)');
morphEl.value = '0'; morphEl._l.input.forEach(f => f());

/* press Sing and run fake time through ~60 bouts */
els['singBtn']._l.click.forEach(f => f());
const actx = contexts[0];
ok(!!actx, 'HARNESS: AudioContext created on Sing');
let t = 0;
const T_END = 480;
while (t < T_END) { t += 0.03; actx.currentTime = t; intervalCb(); }

/* breath node identification: bufsrc -> filter -> gain */
const bufsrc = allNodes.find(n => n.type === 'bufsrc');
const filtId = connLog.find(([a]) => a === bufsrc.id)[1];
const breathId = connLog.find(([a]) => a === filtId)[1];
const breath = allNodes.find(n => n.id === breathId);
eq(breath.type, 'gain', 'HARNESS: breath chain is bufsrc -> filter -> gain');
eq(connLog.filter(([a]) => a === breathId).length, 1, 'HARNESS: breath gain has exactly ONE outgoing connection');
eq(connLog.filter(([, b]) => b === breathId).length, 1, 'HARNESS: breath gain has exactly ONE incoming connection');
eq(disconnectCalls, 0, 'HARNESS: zero disconnect() calls during a full run');

/* notes from osc starts: group by time, fundamental = min first-freq of the pair */
const byTime = new Map();
for (const s of oscStarts) { const k = Math.round(s.t * 1000); if (!byTime.has(k)) byTime.set(k, []); byTime.get(k).push(s.f0); }
const notes = [...byTime.entries()].map(([k, fs]) => ({ t: k / 1000, f0: Math.min(...fs) })).sort((a, b) => a.t - b.t);
const typeOf = f0 => ['Ua', 'Ub', 'D', 'C'].reduce((best, ty) =>
  Math.abs(meas.types[ty].contour[0] - f0) < Math.abs(meas.types[best].contour[0] - f0) ? ty : best, 'Ua');
for (const n of notes) n.type = typeOf(n.f0);
ok(notes.length > 300, `HARNESS: run produced ${notes.length} notes`);

/* per-note breath caps + endpoints */
const bEvents = breath.gain.events.filter(e => e.kind === 'curve');
eq(bEvents.length, notes.length, 'HARNESS: exactly one breath curve per note (no stacked taps)');
let maxBreath = 0, capViol = 0, endViol = 0;
for (const e of bEvents) {
  if (e.values[0] !== 0 || e.values[e.values.length - 1] !== 0) endViol++;
  for (const v of e.values) { maxBreath = Math.max(maxBreath, v); }
  const note = notes.reduce((best, n) => Math.abs(n.t - e.t) < Math.abs(best.t - e.t) ? n : best, notes[0]);
  const cap = meas.types[note.type].peak * 0.05;
  if (Math.max(...e.values) > cap + 1e-9) capViol++;
}
eq(endViol, 0, 'HARNESS: every breath curve starts and ends at exactly 0');
eq(capViol, 0, 'HARNESS: no breath curve exceeds its note cap (type peak x 0.05)');
ok(maxBreath <= 0.46 * 0.05 + 1e-9, `HARNESS: max breath gain ${maxBreath.toFixed(4)} <= 0.0230 (loudest note peak x 0.05)`);

/* breath value at time t, from recorded events */
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
/* bouts + pauses from note onsets */
const bouts = [[notes[0]]];
for (let i = 1; i < notes.length; i++) {
  if (notes[i].t - notes[i - 1].t > 1.0) bouts.push([]);
  bouts[bouts.length - 1].push(notes[i]);
}
let pauseViol = 0, pauseChecked = 0;
for (let i = 0; i + 1 < bouts.length; i++) {
  const a = bouts[i], b = bouts[i + 1];
  const lastDur = meas.types[a[a.length - 1].type].durMax;
  const mid = (a[a.length - 1].t + lastDur + b[0].t) / 2;
  pauseChecked++; if (breathAt(mid) !== 0) pauseViol++;
}
eq(pauseViol, 0, `HARNESS: breath is exactly 0 at all ${pauseChecked} inter-bout pause midpoints`);

/* generator envelopes */
const formOf = seq => {
  if (seq.every(s => s === 'C')) return 'C';
  if (seq.slice(0, 2).join() === 'Ua,Ub' && seq.slice(2).every(s => s === 'D')) return 'A';
  if (seq.slice(0, 3).join() === 'Ua,Ub,D' && seq.slice(3).every(s => s === 'C')) return 'B';
  return 'other';
};
const formCount = { A: 0, B: 0, C: 0, other: 0 };
let sizeViol = 0, transViol = 0;
const validTr = new Set(Object.keys(meas.grammar.transitions));
for (const b of bouts) {
  const seq = b.map(n => n.type);
  formCount[formOf(seq)]++;
  if (b.length < 6 || b.length > 10) sizeViol++;
  for (let i = 0; i + 1 < seq.length; i++) if (!validTr.has(seq[i] + '>' + seq[i + 1])) transViol++;
}
eq(formCount.other, 0, 'HARNESS: every generated bout matches a measured form');
eq(sizeViol, 0, 'HARNESS: every bout size inside measured 6-10 notes');
eq(transViol, 0, 'HARNESS: every generated transition is a measured transition');
ok(formCount.A > 0 && formCount.B > 0 && formCount.C > 0,
   `HARNESS: all three forms occurred (A=${formCount.A} B=${formCount.B} C=${formCount.C} over ${bouts.length} bouts)`);

console.log(`\nforms over ${bouts.length} generated bouts: A=${formCount.A} B=${formCount.B} C=${formCount.C}; notes=${notes.length}; maxBreath=${maxBreath.toFixed(4)}`);
console.log(`TOTAL: ${pass} pass, ${fail} fail`);
if (failures.length) { console.log('FAILURES:'); failures.forEach(f => console.log(' -', f)); process.exit(1); }
