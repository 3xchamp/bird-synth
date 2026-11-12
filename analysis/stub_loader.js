const fs = require('fs'), vm = require('vm');
const DIR = '/home/hatch/workspace/bird-synth/';
const html = fs.readFileSync(DIR+'syrinx6.html','utf8');
const scriptSrc = html.split('<script>')[1].split('</script>')[0];
const ok=(c,m)=>{ if(!c) throw new Error('loader check failed: '+m); };

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
  createConvolver(){ const n=new FakeNode('convolver'); n.buffer=null; return n; }
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
/* page load (shared stub loader) */
vm.runInContext(scriptSrc, sandbox, { filename:'syrinx6.js' });
const S = sandbox.SYRINX;

/* fire a real click listener on a (static or built) element by id */
function clickId(id){
  const el = documentStub.getElementById(id);
  if (!el) throw new Error('clickId: no element #'+id);
  for (const fn of (el._listeners.click||[])) fn({ preventDefault(){}, target: el });
}
module.exports = { S, sandbox, documentStub, graph, pump, clickId, staticEls };
