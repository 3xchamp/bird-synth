/* Song-mode harness: drives SYRINX·6 in the stub graph through the mode
   toggle, the cross-mode guards, the song transport, STOP, and full song
   renders at morph 0 / 0.5 / 1. Asserts: guards block SING/CHORUS/keyboard
   in song mode and PLAY in free play; per-note animation callbacks fire
   for song notes (one per scheduled event); STOP mid-song leaves nothing
   scheduled; a mode switch mid-song stops the song; breath caps hold. */
const { S, documentStub, graph, pump, clickId } = require('./stub_loader.js');
let pass = 0, fail = 0;
const ok = (c, m)=>{ if (c) pass++; else { fail++; console.log('  FAIL:', m); } };
const IDS = ['cardinal','owl','thrush','wren','sparrow','towhee'];

let cbCount = 0; const cbByVoice = {};
S.onNote(ev=>{ cbCount++; cbByVoice[ev.voice]=(cbByVoice[ev.voice]||0)+1; });
S.init();

console.log('== Song harness: library + default mode ==');
ok(S.state().mode === 'free', 'bank boots in FREE PLAY');
ok(S.songs.length === 1 && S.songs[0].id === 'minuet-g', 'one song in the library');
ok(S.songs[0].credit === 'Christian Petzold', 'composer credit is Christian Petzold');
ok(documentStub.getElementById('songmeta').innerHTML.includes('Christian Petzold'), 'song meta credits Petzold');
ok(documentStub.getElementById('songpick').children.length === 1, 'picker holds the library');

console.log('== Song harness: PLAY is inert in FREE PLAY ==');
{
  const n0 = S.stats.notes;
  S.startSong();
  ok(S.state().songPlaying === false, 'startSong blocked in free play');
  pump(5);
  ok(S.stats.notes === n0, 'no notes scheduled by the blocked startSong');
}

console.log('== Song harness: enter SONG mode, cross-mode guards ==');
clickId('mode-song');
ok(S.state().mode === 'song', 'mode toggle switches to SONG');
ok(Math.abs(S.state().fullness - 0.5) < 1e-9, 'first SONG entry auto-sets the untouched FULLNESS knob to the 0.5 demo default');
S.setFullness(0);
ok(S.state().fullness === 0, 'FULLNESS pinned to 0: the guards/renders below are the pre-FULLNESS baseline');
ok(S.roomWet() === 0, 'room wet gain is exactly 0 at FULLNESS 0');
{
  const n0 = S.stats.notes;
  S.setSing('cardinal', true);
  ok(S.state().singing.every(s=>!s), 'SING blocked in song mode (API)');
  clickId('sing-wren');
  ok(S.state().singing.every(s=>!s), 'SING blocked in song mode (strip button)');
  S.chorus();
  ok(S.state().chorusOn === false, 'CHORUS blocked in song mode (API)');
  clickId('btnChorus');
  ok(S.state().chorusOn === false, 'CHORUS blocked in song mode (button)');
  S.keyNote(64);
  ok(S.stats.notes === n0, 'keyboard blocked in song mode');
  pump(3);
  ok(S.stats.notes === n0, 'nothing scheduled by blocked triggers');
}

console.log('== Song harness: play, progress readout, STOP mid-song ==');
{
  clickId('songplay');
  ok(S.state().songPlaying === true, 'PLAY SONG starts the song (button)');
  ok(S.state().songId === 'minuet-g', 'state reports the playing song');
  pump(2);
  const prog = documentStub.getElementById('songprog').textContent;
  console.log('  progress at ~2 s:', JSON.stringify(prog));
  ok(prog === 'A · bar 2 — CARDINAL sings', 'progress readout tracks part/bar/bird');
  pump(28);
  ok(cbCount > 40, 'animation callbacks firing for song notes ('+cbCount+')');
  const n0 = S.stats.notes, c0 = cbCount;
  clickId('songstop');
  ok(S.state().songPlaying === false, 'STOP ends the song');
  pump(30);
  ok(S.stats.notes === n0 && cbCount === c0, 'nothing scheduled after STOP mid-song');
}

console.log('== Song harness: mode switch mid-song stops the song ==');
{
  S.startSong();
  pump(4);
  ok(S.state().songPlaying === true, 'song playing again');
  clickId('mode-free');
  ok(S.state().mode === 'free' && S.state().songPlaying === false, 'switching to FREE PLAY stops the song');
  const n0 = S.stats.notes;
  pump(10);
  ok(S.stats.notes === n0, 'no song notes after the mode switch');
  clickId('mode-song');
  ok(S.state().mode === 'song', 'back in SONG mode');
}

console.log('== Song harness: full renders at morph 0 / 0.5 / 1 ==');
for (const m of [0, 0.5, 1]){
  S.setMasterMorph(m);
  const n0 = S.stats.notes, c0 = cbCount;
  const before = { ...cbByVoice };
  S.startSong();
  ok(S.state().songPlaying === true, 'song starts at morph '+m);
  pump(130);
  ok(S.state().songPlaying === false, 'song runs to completion at morph '+m);
  const dn = S.stats.notes - n0, dc = cbCount - c0;
  console.log(`  morph ${m}: ${dn} notes scheduled, ${dc} animation callbacks`);
  ok(dn === 249, 'full note count at morph '+m+' (melody 190 + bass 48 + fills 11)');
  ok(dc === 249, 'one animation callback per song note at morph '+m);
  for (const id of IDS) ok((cbByVoice[id]||0) > (before[id]||0), 'morph '+m+': '+id+' sang in the song');
  const prog = documentStub.getElementById('songprog').textContent;
  ok(/finished/.test(prog), 'progress readout shows completion at morph '+m);
}
S.setMasterMorph(0);

console.log('== Song harness: FULLNESS compiled layers (harmony + bass movement) ==');
const renders = []; S.onNote(ev=>renders.push(ev));
const evsAll = S.songEvents('minuet-g');
const harmEvs = evsAll.filter(e=>e.kind==='harmony');
const b3Evs = evsAll.filter(e=>e.kind==='bass3');
ok(harmEvs.length === 96, 'compiled harmony events: 2 per bar x 48 performed bars (got '+harmEvs.length+')');
ok(b3Evs.length === 48, 'compiled bass-movement events: 1 per performed bar (got '+b3Evs.length+')');
/* the chord chart, derived independently from the source bass staff read
   against the melody (beats 2-3 harmony); tones are [third, fifth] pcs */
const CHART = { A:['G','G','C','G','Am','G','G','D','G','G','C','G','Am','G','D','G'],
                B:['G','D','Em','A','A','D','D','D','G','C','G','D','D','G','G','G'] };
const TONES = { G:['B','D'], C:['E','G'], D:['F#','A'], Em:['G','B'], Am:['C','E'], A:['C#','E'] };
const SEMI = { C:0,'C#':1,D:2,'D#':3,E:4,F:5,'F#':6,G:7,'G#':8,A:9,'A#':10,B:11 };
const pcOf = n => n.replace(/\d+$/,'');
const freqOfName = n => 440*Math.pow(2, ((SEMI[pcOf(n)] + (parseInt(n.match(/\d+$/)[0],10)+1)*12) - 69)/12);
const chartOf = e => CHART[e.section][e.bar - (e.section==='A' ? 1 : 17)];
let chartBad = 0;
for (const e of harmEvs) if (!TONES[chartOf(e)].includes(pcOf(e.name))) chartBad++;
ok(chartBad === 0, 'every harmony pitch is a chord tone of its bar ('+chartBad+' bad)');
const key2 = e => e.part+'|'+e.bar;
const melBars = new Set(evsAll.filter(e=>e.kind==='melody').map(key2));
let harmBarsOk = melBars.size === 48;
for (const k of melBars) if (harmEvs.filter(e=>key2(e)===k).length !== 2) harmBarsOk = false;
ok(harmBarsOk, 'harmony present (exactly 2 notes) in every performed bar');
let b3BarsOk = true;
for (const k of melBars) if (b3Evs.filter(e=>key2(e)===k).length !== 1) b3BarsOk = false;
ok(b3BarsOk, 'bass beat-3 movement present in every performed bar');
const melVoiceByBar = {}; for (const e of evsAll) if (e.kind==='melody') melVoiceByBar[key2(e)] = e.voice;
ok(harmEvs.every(e=> melVoiceByBar[key2(e)] !== e.voice), 'harmony voice never equals the melody voice (same bar, same phrase)');
ok(harmEvs.every(e=> ['towhee','sparrow','wren'].includes(e.voice)), 'harmony voices come from the towhee/sparrow/wren pool');
ok(new Set(harmEvs.map(e=>e.voice)).size === 3, 'all three harmony voices are used across the song');
const HREG = { cardinal:2, thrush:2.5, wren:2.5, sparrow:3, towhee:4 };
ok(harmEvs.every(e=> Math.abs(e.freq - freqOfName(e.name)*HREG[e.voice]) < 1e-6),
   'harmony renders at half the voice melody register (one octave below, constant per voice)');
ok(!harmEvs.some(e=> (e.beat>=48 && e.beat<49) || (e.beat>=121 && e.beat<122)), 'no harmony inside the two fill slots');
ok(harmEvs.every(e=> Number.isInteger(e.beat)), 'harmony onsets land on bar beats 2 and 3');
const bassByBar = {}; for (const e of evsAll) if (e.kind==='bass') bassByBar[key2(e)] = e;
let b3Bad = 0;
for (const e of b3Evs){
  const b = bassByBar[key2(e)]; if (!b){ b3Bad++; continue; }
  const pcF = ((Math.round(69 + 12*Math.log2(e.freq/440)) % 12) + 12) % 12;
  if (!(e.freq > b.freq && e.freq <= b.freq*2 + 1e-6)) b3Bad++;
  if (pcF !== SEMI[pcOf(b.name)] && pcF !== SEMI[TONES[chartOf(e)][1]]) b3Bad++;
}
ok(b3Bad === 0, 'bass movement sits above the beat-1 note within its octave, as root or chord fifth ('+b3Bad+' bad)');

console.log('== Song harness: FULLNESS renders at 0 / 0.5 / 1 ==');
for (const F of [0, 0.5, 1]){
  S.setFullness(F);
  ok(Math.abs(S.state().fullness - F) < 1e-9, 'FULLNESS set to '+F);
  const n0 = S.stats.notes, c0 = cbCount, bd0 = S.stats.body, r0 = renders.length;
  S.startSong();
  ok(S.state().songPlaying === true, 'song starts at FULLNESS '+F);
  pump(130);
  ok(S.state().songPlaying === false, 'song runs to completion at FULLNESS '+F);
  const dn = S.stats.notes - n0, dc = cbCount - c0, db = S.stats.body - bd0;
  const want = F === 0 ? 249 : 393;
  console.log(`  FULLNESS ${F}: ${dn} notes, ${dc} callbacks, ${db} body layers`);
  ok(dn === want, 'note count at FULLNESS '+F+' (want '+want+')');
  ok(dc === want, 'one animation callback per note at FULLNESS '+F);
  if (F === 0){
    ok(db === 0, 'FULLNESS 0: no body sources created — the baseline is exact');
    ok(S.roomWet() === 0, 'FULLNESS 0: room wet gain exactly 0 during the render');
  } else {
    ok(db === dn, 'FULLNESS '+F+': one body layer per rendered note ('+db+' vs '+dn+')');
    const rc = renders.slice(r0);
    const h = rc.filter(e=>Math.abs(e.gainScale - 0.35*F) < 1e-9);
    const b3 = rc.filter(e=>Math.abs(e.gainScale - 0.6*F) < 1e-9);
    ok(h.length === 96, 'FULLNESS '+F+': 96 harmony callbacks at gainScale 0.35xF');
    ok(b3.length === 48 && b3.every(e=>e.voice==='owl'), 'FULLNESS '+F+': 48 owl bass-movement callbacks at 0.6xF');
    ok(rc.filter(e=>e.gainScale === 1).length === 249, 'FULLNESS '+F+': base events keep gainScale 1');
    ok(h.every(e=>e.gainScale < 1), 'FULLNESS '+F+': harmony gain below melody gain');
    ok(Math.abs(S.roomWet() - F*0.35) < 1e-9, 'FULLNESS '+F+': room wet gain = F x 0.35');
  }
  const prog = documentStub.getElementById('songprog').textContent;
  ok(/finished/.test(prog), 'progress readout shows completion at FULLNESS '+F);
}
{ /* STOP still leaves nothing scheduled, now with layers armed */
  S.setFullness(1);
  S.startSong(); pump(6);
  ok(S.state().songPlaying === true, 'song playing at FULLNESS 1');
  const n0 = S.stats.notes, c0 = cbCount;
  clickId('songstop');
  ok(S.state().songPlaying === false, 'STOP ends the song at FULLNESS 1');
  pump(20);
  ok(S.stats.notes === n0 && cbCount === c0, 'nothing scheduled after STOP at FULLNESS 1');
  S.setFullness(0);
}

console.log('== Song harness: wire pan positions ==');
const PANS = { cardinal:-0.7, owl:-0.35, thrush:-0.12, wren:0.15, sparrow:0.4, towhee:0.7 };
for (const id of IDS)
  ok(S.voices[id].panNode && Math.abs(S.voices[id].panNode.pan.value - PANS[id]) < 1e-9,
     id+' voice chain panned at its wire position ('+PANS[id]+')');

console.log('== Song harness: FULLNESS body in free play (keyboard / SING / chorus) ==');
clickId('mode-free');
ok(S.state().mode === 'free', 'back in FREE PLAY for the body checks');
S.setFullness(1);
{
  const b0 = S.stats.body, n0 = S.stats.notes;
  let err = null;
  try {
    for (const id of IDS){ S.select(id); S.keyNote(64); }
    S.setMasterMorph(1); S.select('cardinal'); S.keyNote(64); S.setMasterMorph(0);
    S.setSing('wren', true); pump(2); S.setSing('wren', false);
    S.chorus(); pump(1); S.stopAll();
  } catch(e){ err = e; }
  ok(!err, 'keyboard/SING/chorus run at FULLNESS 1 without errors'+(err ? ': '+err.message : ''));
  ok(S.stats.notes > n0, 'notes scheduled in free play at FULLNESS 1');
  ok(S.stats.body > b0, 'body layers scheduled in free play at FULLNESS 1 ('+(S.stats.body-b0)+' body sources)');
}
S.setFullness(0);

console.log('== Song harness: breath caps held through the song ==');
for (const id of IDS){
  const v = S.voices[id];
  const maxPeak = Math.max(...Object.values(v.meas.types).map(T=>v.def.peakOf(T)));
  const cap = 0.05*maxPeak + 1e-9;
  const entries = graph.curveLog.filter(e=>e.node===v.breathEnv && e.param==='gain');
  const mx = entries.reduce((a,e)=>Math.max(a,e.max), 0);
  console.log(`  ${id}: breath curves ${entries.length}, max ${mx.toFixed(5)}, cap ${cap.toFixed(5)}`);
  ok(entries.length > 0 && mx <= cap, id+' breath cap respected in song mode');
}
ok(S.stats.guardHits === 0, 'no grammar fallback used');

console.log('== Song harness: a throwing render mid-song can never stall or repeat the sequence ==');
{
  /* The stub graph's fakes never throw, so a real host's render failure
     (a rejected AudioParam curve, a missing node constructor) is the one
     failure this harness cannot reach on its own. Simulate it: poison
     one voice's play() to throw on every event. The scheduler must skip
     each poisoned note exactly once and still complete the song with
     every other voice's count exact — no stall, no re-fired event. */
  clickId('mode-song');
  S.setFullness(0); S.setMasterMorph(0);
  const base = evsAll.filter(e=>['melody','bass','fill'].includes(e.kind));
  const wantByVoice = {}; for (const e of base) wantByVoice[e.voice] = (wantByVoice[e.voice]||0)+1;
  const before = { ...cbByVoice };
  const origPlay = S.voices.sparrow.play;
  let attempts = 0;
  S.voices.sparrow.play = ()=>{ attempts++; throw new Error('simulated host render failure'); };
  S.startSong();
  ok(S.state().songPlaying === true, 'song starts with a poisoned voice');
  pump(130);
  S.voices.sparrow.play = origPlay;
  ok(S.state().songPlaying === false, 'song completes despite every sparrow render throwing');
  ok(/finished/.test(documentStub.getElementById('songprog').textContent), 'progress readout shows completion after the poisoned run');
  ok(attempts === (wantByVoice.sparrow||0), 'each poisoned event attempted exactly once — none re-fired ('+attempts+' attempts vs '+(wantByVoice.sparrow||0)+' sparrow events)');
  ok(((cbByVoice.sparrow||0) - (before.sparrow||0)) === 0, 'no sparrow callbacks from the poisoned run');
  for (const id of IDS){
    if (id === 'sparrow') continue;
    const got = (cbByVoice[id]||0) - (before[id]||0);
    ok(got === (wantByVoice[id]||0), id+' count exact in the poisoned run ('+got+' vs '+(wantByVoice[id]||0)+') — no event repeated or lost');
  }
}

console.log(`\nSONG HARNESS RESULT: ${pass} checks passed, ${fail} failed; total notes scheduled: ${S.stats.notes}`);
process.exit(fail ? 1 : 0);
