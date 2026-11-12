/* Score audit for SONG MODE: every note the bank's Minuet in G major encoding
   schedules is compared against the machine-readable transcription of the
   public-domain source score (analysis/minuet_bwv_anh114_transcription.json,
   parsed from Allen Garvin's Mutopia LilyPond typeset of BWV Anh. 114 and
   cross-checked against its source text bar by bar).
   Checks: melody pitch/duration/onset for all 190 performed notes, phrase
   rotation vs the arrangement, owl bass (one note per bar, bar's first bass
   note, pitch class exact, octave fold rule), fills (exactly two, measured
   material, in their one-beat slots), global ordering. */
const fs = require('fs');
const { S } = require('./stub_loader.js');
let pass = 0, fail = 0;
const ok = (c, m)=>{ if (c) pass++; else { fail++; console.log('  FAIL:', m); } };

const TR = JSON.parse(fs.readFileSync('/home/hatch/workspace/bird-synth/analysis/minuet_bwv_anh114_transcription.json','utf8'));
const evs = S.songEvents('minuet-g');
ok(Array.isArray(evs) && evs.length > 0, 'compiled events returned');

const REG = { cardinal:4, thrush:5, wren:5, sparrow:6, towhee:8 };
const SEMI = { C:0,'C#':1,D:2,'D#':3,E:4,F:5,'F#':6,G:7,'G#':8,A:9,'A#':10,B:11 };
const midiOf = n => SEMI[n.replace(/\d+$/,'')] + (parseInt(n.match(/\d+$/)[0],10)+1)*12;
const freqOf = n => 440*Math.pow(2,(midiOf(n)-69)/12);
const near = (a,b,tol)=>Math.abs(a-b) <= (tol||1e-9);

/* ---- performance layout (from the song's form): instance -> beat offset ---- */
const mel = TR.melody;
const byBar = {}; for (const n of mel) (byBar[n.bar] = byBar[n.bar]||[]).push(n);
function expectedMelody(){
  const out = [];
  const push = (barFrom, barTo, offset) => {
    for (let b = barFrom; b <= barTo; b++)
      for (const n of byBar[b]) out.push({ name:n.name, beats:n.beats, bar:b, beat: n.onsetBeats + offset });
  };
  push(1, 16, 0);        /* A, first time: beats 0..48   */
  push(1, 16, 49);       /* A repeat: after the 1-beat fill slot at 48 */
  push(17, 24, 97 - 48); /* B first half: score beats 48..72 -> 97..121 */
  push(25, 32, 122 - 72);/* B second half: score beats 72..96 -> 122..146 */
  return out;
}
const expMel = expectedMelody();
const gotMel = evs.filter(e=>e.kind==='melody');
console.log('== Score audit: melody ==');
console.log(`  performed melody notes: got ${gotMel.length}, expected ${expMel.length} (A x2 + B from the transcription)`);
ok(gotMel.length === expMel.length, 'melody note count');
let melBad = 0;
gotMel.forEach((e, i)=>{
  const x = expMel[i]; if (!x) return;
  if (e.name !== x.name || !near(e.durBeats, x.beats) || !near(e.beat, x.beat) || e.bar !== x.bar){
    if (melBad++ < 5) console.log(`    #${i}: got ${e.name}:${e.durBeats} @${e.beat} (bar ${e.bar}) vs expected ${x.name}:${x.beats} @${x.beat} (bar ${x.bar})`);
  }
  const want = freqOf(e.name) * REG[e.voice];
  if (!near(e.freq, want, want*1e-9)){ if (melBad++ < 5) console.log(`    #${i}: rendered freq ${e.freq} != written ${freqOf(e.name)} x register ${REG[e.voice]}`); }
});
ok(melBad === 0, 'melody pitch/duration/onset/register mismatches: '+melBad);
let strictly = true;
for (let i = 1; i < gotMel.length; i++) if (!(gotMel[i].beat > gotMel[i-1].beat)) strictly = false;
ok(strictly, 'melody onsets strictly increasing (single line, score order)');

console.log('== Score audit: phrase rotation ==');
const instance = b => b < 48 ? 'A1' : b < 97 ? 'A2' : b < 121 ? 'B1' : 'B2';
const runs = { A1:[], A2:[], B1:[], B2:[] };
for (const e of gotMel){ const r = runs[instance(e.beat)]; if (r[r.length-1] !== e.voice) r.push(e.voice); }
const wantRuns = { A1:['cardinal','sparrow','thrush','towhee'], A2:['wren','cardinal','sparrow','towhee'],
                   B1:['cardinal','thrush'], B2:['wren','towhee'] };
for (const k of Object.keys(wantRuns)){
  const same = JSON.stringify(runs[k]) === JSON.stringify(wantRuns[k]);
  console.log(`  ${k}: ${runs[k].join(' -> ')}`);
  ok(same, k+' rotation differs from the arrangement');
}
const allSeq = [...runs.A1, ...runs.A2, ...runs.B1, ...runs.B2];
ok(allSeq.every((v,i)=> i===0 || v !== allSeq[i-1]), 'no voice sings two phrases back-to-back');
for (const v of ['cardinal','thrush','wren','sparrow','towhee'])
  ok(allSeq.filter(x=>x===v).length >= 2, v+' sings at least two phrases');

console.log('== Score audit: owl bass ==');
const gotBass = evs.filter(e=>e.kind==='bass');
console.log(`  bass notes: got ${gotBass.length}, expected 48 (one per performed bar)`);
ok(gotBass.length === 48, 'bass note count');
const bassByBar = {}; for (const b of TR.bassFirstNotePerBar) bassByBar[b.bar] = b;
const instBars = [ [1,16,0], [1,16,49], [17,24,97], [25,32,122] ];
let bassBad = 0, bassSeen = 0;
for (const [b0, b1, off] of instBars){
  for (let bar = b0; bar <= b1; bar++){
    const e = gotBass[bassSeen++];
    const beat = (b0===1 ? (bar-1)*3 + off : b0===17 ? 97+(bar-17)*3 : 122+(bar-25)*3);
    const w = bassByBar[bar];
    if (!e || e.bar !== bar || !near(e.beat, beat)) { bassBad++; console.log(`    bar ${bar}: placement wrong (got beat ${e&&e.beat}, bar ${e&&e.bar}; want beat ${beat})`); continue; }
    const rm = midiOf(e.name), wm = w.midi;
    const classOk = ((rm % 12) === (wm % 12));
    const octOk = rm === wm || (freqOf(w.name) < 190 && rm === wm + 12);
    if (!classOk || !octOk){ bassBad++; console.log(`    bar ${bar}: got ${e.name}, source first bass note ${w.name}`); }
  }
}
ok(bassBad === 0, 'bass mismatches: '+bassBad);

console.log('== Score audit: fills ==');
const fills = evs.filter(e=>e.kind==='fill');
const fA = fills.filter(e=>e.beat >= 48 && e.beat < 49), fB = fills.filter(e=>e.beat >= 121 && e.beat < 122);
console.log(`  fill events: ${fills.length} total; A-joint slot: ${fA.length} (sparrow), B-midpoint slot: ${fB.length} (wren)`);
ok(fills.length === fA.length + fB.length, 'fills occur only in the two joint slots');
ok(fA.length === 6 && fA.every(e=>e.voice==='sparrow'), 'fill A: 6 sparrow notes');
ok(fB.length === 5 && fB.every(e=>e.voice==='wren'), 'fill B: 5 wren notes');
ok(fA.map(e=>e.type).join(',') === 'L,h,M,L,h,M', 'fill A uses the sparrow measured figure types L,h,M');
ok(fB.map(e=>e.type).join(',') === 'S,U,D,S,U', 'fill B uses the wren chip types S,U,D');
const gapsA = fA.slice(1).map((e,i)=>+(e.beat - fA[i].beat).toFixed(6));
ok(JSON.stringify(gapsA) === JSON.stringify([0.164,0.11,0.192,0.164,0.11]),
   'fill A spacings are the measured transition periods in beats: '+gapsA.join(','));

console.log('== Score audit: global shape ==');
let sorted = true;
for (let i = 1; i < evs.length; i++) if (evs[i].beat < evs[i-1].beat - 1e-9) sorted = false;
ok(sorted, 'all events in score order (non-decreasing beats)');
const lastEnd = Math.max(...evs.filter(e=>e.kind!=='fill').map(e=>e.beat + e.durBeats));
ok(near(lastEnd, 146), 'performance length 146 beats (got '+lastEnd+')');
ok(!evs.some(e=>e.kind==='melody' && e.beat >= 48 && e.beat < 49), 'no melody inside the fill A slot');
ok(!evs.some(e=>e.kind==='melody' && e.beat >= 121 && e.beat < 122), 'no melody inside the fill B slot');

console.log(`\nSCORE AUDIT RESULT: ${pass} checks passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
