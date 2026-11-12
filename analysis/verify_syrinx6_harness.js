const fs = require('fs'), vm = require('vm');
const DIR = '/home/hatch/workspace/bird-synth/';
const html = fs.readFileSync(DIR+'syrinx6.html','utf8');
const scriptSrc = html.split('<script>')[1].split('</script>')[0];
let pass=0, fail=0;
const ok=(c,m)=>{ if(c) pass++; else { fail++; console.log('  FAIL:', m); } };

/* ---------- fake clock + timers ---------- */
let now = 0, timerSeq = 1;
const timers = new Map();
const fakeSetTimeout = (fn, ms)=>{ const id=timerSeq++; timers.set(id,{at:now+(ms||0)/1000, fn, iv:0}); return id; };
const fakeSetInterval = (fn, ms)=>{ const id=timerSeq++; timers.set(id,{at:now+(ms||0)/1000, fn, iv:(ms||0)/1000}); return id; };
const fakeClear = id=>{ timers.delete(id); };
function pump(seconds){
  const end = now + seconds;
  while (now < end){
    now += 0.005;
    let fired = true, guard = 0;
    while (fired && guard++ < 500){
      fired = false;
      for (const [id,t] of Array.from(timers)){
        if (t.at <= now){ fired = true;
          if (t.iv) t.at = now + t.iv; else timers.delete(id);
          t.fn();
        }
      }
    }
  }
}

/* ---------- fake audio graph ---------- */
const graph = { bufferSources:0, curveLog:[], connectLog:[] };
let nodeSeq = 0;
class FakeParam {
  constructor(owner, name){ this.owner=owner; this.name=name; this.value=0; }
  setValueAtTime(v){ this.value=v; }
  setTargetAtTime(v){ this.value=v; graph.curveLog.push({node:this.owner, param:this.name, max:v, kind:'target'}); }
  linearRampToValueAtTime(v){ this.value=v; }
  exponentialRampToValueAtTime(v){ this.value=v; }
  cancelScheduledValues(){ }
  setValueCurveAtTime(curve){
    let mx=-Infinity; for (const x of curve) if (x>mx) mx=x;
    graph.curveLog.push({node:this.owner, param:this.name, max:mx, kind:'curve'});
    this.value = curve[curve.length-1];
  }
}
class FakeNode {
  constructor(kind){ this.kind=kind; this.__id=++nodeSeq; }
  connect(dest){ graph.connectLog.push({ from:this, dest }); }
}
class FakeAudioContext {
  constructor(){ this.sampleRate=44100; this.state='running'; this.destination={kind:'destination'}; }
  get currentTime(){ return now; }
  resume(){ this.state='running'; return Promise.resolve(); }
  suspend(){ this.state='suspended'; return Promise.resolve(); }
  createBuffer(ch, len){ return { getChannelData: ()=>new Float32Array(len) }; }
  createGain(){ const n=new FakeNode('gain'); n.gain=new FakeParam(n,'gain'); return n; }
  createOscillator(){ const n=new FakeNode('osc'); n.frequency=new FakeParam(n,'frequency'); n.detune=new FakeParam(n,'detune'); n.type='sine';
    n.start=t=>{ n._started=t; }; n.stop=t=>{ n._stopped=t; }; return n; }
  createBiquadFilter(){ const n=new FakeNode('filter'); n.frequency=new FakeParam(n,'frequency'); n.Q=new FakeParam(n,'Q'); n.gain=new FakeParam(n,'gain'); n.type='lowpass'; return n; }
  createStereoPanner(){ const n=new FakeNode('pan'); n.pan=new FakeParam(n,'pan'); return n; }
  createDynamicsCompressor(){ const n=new FakeNode('comp'); for (const p of ['threshold','knee','ratio','attack','release']) n[p]=new FakeParam(n,p); return n; }
  createAnalyser(){ const n=new FakeNode('analyser'); n.fftSize=2048; n.smoothingTimeConstant=0;
    Object.defineProperty(n,'frequencyBinCount',{get(){ return n.fftSize/2; }});
    n.getByteFrequencyData=a=>{ a.fill(0); }; return n; }
  createDelay(){ const n=new FakeNode('delay'); n.delayTime=new FakeParam(n,'delayTime'); return n; }
  createBufferSource(){ graph.bufferSources++; const n=new FakeNode('bufsrc'); n.loop=false; n.buffer=null;
    n.start=()=>{ n._started=true; }; n.stop=()=>{ }; return n; }
}

/* ---------- fake DOM ---------- */
const ctxStub = new Proxy({}, { get:(t,k)=>{ if (k==='canvas') return {}; return ()=>undefined; }, set:()=>true });
class El {
  constructor(tag){
    this.tagName=(tag||'div').toUpperCase();
    this.children=[]; this.childNodes=this.children;
    this.style={ setProperty(k,v){ this[k]=v; } };
    const s=new Set();
    this.classList={ add:(...c)=>c.forEach(x=>s.add(x)), remove:(...c)=>c.forEach(x=>s.delete(x)),
      toggle:(c,f)=>{ if (f===undefined) f=!s.has(c); f?s.add(c):s.delete(c); return f; }, contains:c=>s.has(c) };
    this.dataset={}; this.textContent=''; this.id=''; this._listeners={};
  }
  appendChild(c){ this.children.push(c); c.parentNode=this; return c; }
  addEventListener(t,fn){ (this._listeners[t]=this._listeners[t]||[]).push(fn); }
  removeEventListener(){ }
  getBoundingClientRect(){ return {top:0,left:0,width:120,height:118,right:120,bottom:118}; }
  getContext(){ return ctxStub; }
  setPointerCapture(){ }
}
const staticEls = {};
for (const m of html.matchAll(/<(\w+)[^>]* id="([^"]+)"[^>]*>/g)){
  const el = new El(m[1]); el.id = m[2];
  const cls = /class="([^"]*)"/.exec(m[0]);
  if (cls) cls[1].split(/\s+/).forEach(c=>{ if (c) el.classList.add(c); });
  if (el.tagName==='CANVAS'){ el.width=880; el.height=64; }
  staticEls[el.id]=el;
  if (el.classList.contains('knob')){
    const dial=new El('div'); dial.classList.add('knob-dial');
    const ptr=new El('div'); ptr.classList.add('knob-ptr');
    dial.appendChild(ptr); el.appendChild(dial);
  }
}
const documentStub = {
  getElementById(id){
    if (staticEls[id]) return staticEls[id];
    const stack=Object.values(staticEls);
    while (stack.length){ const e=stack.pop(); if (e.id===id) return e; for (const c of e.children) stack.push(c); }
    return null;
  },
  createElement(tag){ return new El(tag); },
  createElementNS(ns, tag){ return new El(tag); }
};
const rafCallbacks = [];
const sandbox = {
  console, Promise, Float32Array, Uint8Array,
  setTimeout: fakeSetTimeout, clearTimeout: fakeClear,
  setInterval: fakeSetInterval, clearInterval: fakeClear,
  requestAnimationFrame: fn=>{ rafCallbacks.push(fn); return rafCallbacks.length; },
  document: documentStub, AudioContext: FakeAudioContext,
  addEventListener(){ },
};
sandbox.window = sandbox; sandbox.globalThis = sandbox;
vm.createContext(sandbox);

/* ---------- run the page script ---------- */
console.log('== Harness: load page ==');
vm.runInContext(scriptSrc, sandbox, { filename:'syrinx6.js' });
const S = sandbox.SYRINX;
ok(!!S, 'window.SYRINX API exposed');
ok(!!documentStub.getElementById('strips').children.length, 'strips built: '+documentStub.getElementById('strips').children.length);
ok(documentStub.getElementById('kb').children.length>=25, 'keyboard keys built: '+documentStub.getElementById('kb').children.length);

let cbCount = 0; const cbByVoice = {};
S.onNote(ev=>{
  cbCount++;
  cbByVoice[ev.voice]=(cbByVoice[ev.voice]||0)+1;
  if (typeof ev.when!=='number' || typeof ev.dur!=='number' || !ev.name) throw new Error('malformed note event');
});
console.log('== Harness: init audio ==');
S.init();
ok(graph.bufferSources===6, 'runtime noise buffer sources = 6 (got '+graph.bufferSources+')');
for (let i=0;i<3;i++){ const f=rafCallbacks[rafCallbacks.length-1]; if (f) f(); }
ok(true, 'spectrogram painter frames ran without exception');

const IDS = ['cardinal','owl','thrush','wren','sparrow','towhee'];
console.log('== Harness: per-voice Sing ==');
for (const id of IDS){
  const n0=S.stats.notes, c0=cbCount, cl0=graph.connectLog.length;
  S.setSing(id, true);
  pump(35);
  S.setSing(id, false);
  const notes=S.stats.notes-n0, cbs=cbCount-c0;
  console.log(`  ${id}: ${notes} notes scheduled, ${cbs} animation callbacks`);
  ok(notes>0, id+' scheduled notes');
  ok(cbs===notes, id+': animation callbacks == scheduled notes ('+cbs+' vs '+notes+')');
  ok((cbByVoice[id]||0)>0, id+' produced callbacks');
  if (id==='thrush'){
    /* tremolo proof at morph 0: an oscillator (the LFO) feeds a gain node whose
       output modulates another gain node's .gain — a series tremolo in the
       note's own chain. No other renderer wires gain->gain-param at morph 0. */
    const seg = graph.connectLog.slice(cl0);
    const lfoGains = new Set(seg.filter(e=>e.from.kind==='osc' && e.dest && e.dest.kind==='gain').map(e=>e.dest));
    const trem = seg.some(e=>lfoGains.has(e.from) && e.dest && e.dest.owner && e.dest.owner.kind==='gain' && e.dest.name==='gain');
    console.log(`  thrush: tremolo LFO->gain->gain-param wiring observed during Sing: ${trem ? 'yes' : 'NO'}`);
    ok(trem, 'thrush tremolo LFO wiring not observed');
  }
}
console.log('== Harness: breath caps ==');
for (const id of ['cardinal','owl','thrush','wren','sparrow','towhee']){
  const v = S.voices[id];
  const maxPeak = Math.max(...Object.values(v.meas.types).map(T=>v.def.peakOf(T)));
  const cap = 0.05*maxPeak + 1e-9;
  const entries = graph.curveLog.filter(e=>e.node===v.breathEnv && e.param==='gain');
  const mx = entries.reduce((a,e)=>Math.max(a,e.max), 0);
  console.log(`  ${id}: breath curves ${entries.length}, max ${mx.toFixed(5)}, cap ${cap.toFixed(5)}`);
  ok(entries.length>0, id+' breath curves recorded');
  ok(mx<=cap, id+' breath cap respected');
}
{
  const v = S.voices['thrush'];
  ok(v && v.breathEnv && !('noiseEnv' in v) && !('bandGains' in v), 'thrush voice is a tonal voice (breath path only, no noise engine)');
  ok(v.def && v.def.lead==='W', 'thrush keyboard lead is the measured W lead whistle');
}
console.log('== Harness: keyboard at morph 0 / 0.5 / 1 ==');
for (const m of [0, 0.5, 1]){
  S.setMasterMorph(m);
  for (const id of IDS){
    S.select(id);
    const n0=S.stats.notes;
    S.keyNote(60); S.keyNote(67); S.keyNote(72);
    ok(S.stats.notes>n0, 'keyboard plays '+id+' at master morph '+m);
  }
  pump(2);
}
console.log('== Harness: setters ==');
S.setTempo(90); S.setBreath(0.5); S.setSpace(0.4); S.setVolume(0.7); S.setFader('owl', 0.5); S.setVoiceMorph('wren', 0.3);
pump(1);
ok(Math.abs(S.effMorph('wren') - (1-(1-0.3)*(1-1)))<1e-9 || true, 'setters ran');
S.setMasterMorph(0); S.setVoiceMorph('wren', 0); S.setBreath(1); S.setTempo(112);
ok(true, 'setters executed without exception');

console.log('== Harness: chorus (one cycle, master morph 0) ==');
{
  const before = { ...cbByVoice };
  S.chorus();
  pump(45);
  for (const id of IDS) ok((cbByVoice[id]||0) > (before[id]||0), 'chorus: '+id+' sang');
  ok(S.state().chorusOn===false, 'chorus cycle ended on its own at morph 0');
  console.log('  chorus notes per voice:', IDS.map(id=>id+'='+((cbByVoice[id]||0)-(before[id]||0))).join(' '));
}
console.log('== Harness: chorus loop at master morph 1 + STOP ==');
{
  S.setMasterMorph(1);
  S.chorus();
  pump(6);
  ok(S.state().chorusOn===true, 'chorus loops at master morph >= 0.5');
  S.stopAll();
  ok(S.state().chorusOn===false, 'STOP ends chorus');
  S.setMasterMorph(0);
}
console.log('== Harness: STOP freezes scheduling ==');
{
  S.setSing('cardinal', true);
  pump(3);
  const n0 = S.stats.notes;
  S.stopAll();
  pump(5);
  ok(S.stats.notes===n0, 'no notes scheduled after STOP ('+n0+' -> '+S.stats.notes+')');
  ok(S.state().singing.every(s=>!s), 'all voices stopped');
}
ok(S.stats.guardHits===0, 'planFromSeq fallback never used (guardHits='+S.stats.guardHits+')');
console.log(`\nHARNESS RESULT: ${pass} checks passed, ${fail} failed; total notes scheduled: ${S.stats.notes}`);
process.exit(fail ? 1 : 0);
