'use strict';
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const meas = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
fs.writeFileSync('/tmp/heron_script.js', script);

/* ---------- constant audit ---------- */
const measJs = script.match(/const MEAS = (\{[\s\S]*?\n\});/)[1];
const M = JSON.parse(measJs);
let compared = 0, mismatches = [];
function cmp(label, a, b) {
  compared++;
  if (typeof a === 'number' && typeof b === 'number') {
    if (Math.abs(a - b) > 1e-9) mismatches.push(`${label}: page ${a} vs json ${b}`);
  } else if (a !== b) mismatches.push(`${label}: page ${a} vs json ${b}`);
}
function cmpArr(label, a, b) { a.forEach((v, i) => cmp(`${label}[${i}]`, v, b[i])); }
for (const tk of ['L', 'M', 'K']) {
  const P = M.types[tk], J = meas.types[tk];
  cmp(tk + '.n', P.n, J.n);
  cmp(tk + '.durMed', P.durMed, J.dur_med); cmp(tk + '.durMin', P.durMin, J.dur_min);
  cmp(tk + '.durMax', P.durMax, J.dur_max); cmp(tk + '.gridDur', P.gridDur, J.grid_dur);
  cmp(tk + '.peakMed', P.peakMed, J.peak_med); cmp(tk + '.centroid', P.centroid, J.centroid_med_hz);
  cmpArr(tk + '.profile', P.profile, J.band_profile_med);
  cmpArr(tk + '.amp', P.amp, J.amp_template_med);
  cmp(tk + '.f0', P.f0, J.f0_med_hz); cmp(tk + '.f0Share', P.f0Share, J.f0_share_med);
  cmp(tk + '.f0RelN', P.f0RelN, J.f0_reliable_n); cmp(tk + '.harm2', P.harm2, J.f0_harm2_med);
}
for (const kk of Object.keys(meas.transitions)) {
  const P = M.transitions[kk], J = meas.transitions[kk];
  cmp(`tr.${kk}.min`, P.min, J.min); cmp(`tr.${kk}.med`, P.med, J.med);
  cmp(`tr.${kk}.max`, P.max, J.max); cmp(`tr.${kk}.grid`, P.grid, J.grid);
}
cmp('gapPool.min', M.gapPool.min, meas.gap_stats_s.min);
cmp('gapPool.med', M.gapPool.med, meas.gap_stats_s.med);
cmp('gapPool.max', M.gapPool.max, meas.gap_stats_s.max);
cmp('arc.approachK', M.arc.approachK, meas.bursts[0].peak_rel);
cmp('arc.approachM', M.arc.approachM, meas.bursts[1].peak_rel);
cmp('arc.overhead1.med', M.arc.overhead1[1], meas.bursts[2].peak_rel);
cmp('arc.overhead2.med', M.arc.overhead2[1], meas.bursts[3].peak_rel);
const cp = meas.phases.calling.burst_idx.map(i => meas.bursts[i].peak_rel);
cmp('arc.calling.min', M.arc.calling[0], Math.min(...cp));
cmp('arc.calling.max', M.arc.calling[2], Math.max(...cp));
cmp('arc.calling.med', M.arc.calling[1], cp.slice().sort((a, b) => a - b)[3]);
cmp('arc.callingLShare', M.arc.callingLShare, Math.round(2 / 7 * 10000) / 10000);
cmp('arc.settle.min', M.arc.settle[0], meas.bursts[11].peak_rel);
cmp('arc.settle.max', M.arc.settle[2], meas.bursts[12].peak_rel);
cmp('arc.settle.med', M.arc.settle[1], Math.round((meas.bursts[11].peak_rel + meas.bursts[12].peak_rel) / 2 * 1000) / 1000);
M.sequence.forEach((s, i) => {
  const J = meas.bursts[i];
  cmp(`seq[${i}].t`, s.t, J.type); cmp(`seq[${i}].peak`, s.peak, J.peak_rel);
  cmp(`seq[${i}].dur`, s.dur, J.dur_s); cmp(`seq[${i}].period`, s.period, J.period_after_s);
});
console.log(`CONSTANT AUDIT: ${compared} values compared, ${mismatches.length} mismatches`);
mismatches.forEach(m => console.log('  MISMATCH', m));

/* ---------- generator logic tests ---------- */
const logic = script.match(/\/\* ==== LOGIC-BEGIN[\s\S]*?==== LOGIC-END ==== \*\//)[0];
const sandbox = { Math, console };
vm.createContext(sandbox);
vm.runInContext(logic, sandbox);
let fails = [];
for (let trial = 0; trial < 2000; trial++) {
  const plan = vm.runInContext('makePerformance()', sandbox);
  const evs = plan.evs;
  const peakIdx = evs.findIndex(e => e.peak >= 0.55);
  if (peakIdx < 0 || peakIdx > 2) { fails.push(`trial ${trial}: overhead starts at ${peakIdx}`); break; }
  const approach = evs.slice(0, peakIdx), rest = evs.slice(peakIdx);
  if (!approach.every(e => e.peak <= 0.16)) { fails.push(`trial ${trial}: approach peak too loud`); break; }
  if (!(rest[0].type === 'L' && rest[1].type === 'L' && rest[0].peak >= 0.55 && rest[0].peak <= 0.72 && rest[1].peak >= 0.92 && rest[1].peak <= 1.0)) {
    fails.push(`trial ${trial}: overhead pair wrong: ${JSON.stringify(rest.slice(0, 2))}`); break;
  }
  const settleStart = evs.length - 1 - [...evs].reverse().findIndex(e => e.type !== 'K' || e.peak > 0.23);
  const settle = evs.slice(settleStart + 1).filter(e => e.type === 'K');
  const calling = evs.slice(peakIdx + 2, settleStart + 1);
  if (calling.length < 5 || calling.length > 7) { fails.push(`trial ${trial}: calling count ${calling.length}`); break; }
  if (!calling.every(e => e.peak >= 0.224 && e.peak <= 0.41)) { fails.push(`trial ${trial}: calling peak out of range`); break; }
  if (settle.length < 1 || settle.length > 2 || !evs.slice(-settle.length).every(e => e.type === 'K' && e.peak >= 0.164 && e.peak <= 0.22)) {
    fails.push(`trial ${trial}: settle wrong`); break;
  }
  for (let i = 1; i < evs.length; i++) {
    const pb = evs[i].birdOff - evs[i - 1].birdOff, pg = evs[i].gridOff - evs[i - 1].gridOff;
    if (!(pb > 0.5 && pb < 1.96)) { fails.push(`trial ${trial}: bird period ${pb}`); break; }
    if (!(pg >= 0.6696 - 1e-9 && pg <= 1.2054 + 1e-9)) { fails.push(`trial ${trial}: grid period ${pg}`); break; }
  }
  if (!(plan.durBird > 4 && plan.durBird < 17)) { fails.push(`trial ${trial}: span ${plan.durBird}`); break; }
  if (fails.length) break;
}
console.log(`GENERATOR TESTS: 2000 performances, ${fails.length} failures`);
fails.forEach(f => console.log('  FAIL', f));
/* morph identity / quantization */
vm.runInContext('morph=0', sandbox);
const idOk = vm.runInContext('morphFreq(914.1)===914.1 && morphFreq(300)===300', sandbox);
vm.runInContext('morph=1', sandbox);
const q = vm.runInContext('quantize(914.1)', sandbox);
const qpc = ((Math.round(69 + 12 * Math.log2(q / 440)) % 12) + 12) % 12;
console.log(`MORPH: identity at 0: ${idOk}; quantize(914.1)=${q.toFixed(1)} Hz, pitch class ${qpc} in A-major pentatonic: ${[9, 11, 1, 4, 6].includes(qpc)}`);

/* ---------- static noise-path audit ---------- */
const count = (re) => (script.match(re) || []).length;
const playBurstBody = script.match(/function playBurst[\s\S]*?\n\}\n/)[0];
const audit = {
  'createBufferSource (noise sources)': count(/createBufferSource/g),
  'noiseSrc.connect(': count(/noiseSrc\.connect\(/g),
  'band g.connect(noiseGain)': count(/g\.connect\(noiseGain\)/g),
  'noiseGain.connect(voiceBus)': count(/noiseGain\.connect\(voiceBus\)/g),
  'disconnect( anywhere': count(/\.disconnect\(/g),
  'createDynamicsCompressor': count(/createDynamicsCompressor/g),
  'master.connect(comp)': count(/master\.connect\(comp\)/g),
  'noiseGain.gain.setValueCurveAtTime in playBurst': (playBurstBody.match(/noiseGain\.gain\.setValueCurveAtTime/g) || []).length,
  'bandGains setTargetAtTime in playBurst': (playBurstBody.match(/bandGains\.forEach/g) || []).length,
  'connect references to noise nodes inside playBurst': (playBurstBody.match(/noiseSrc\.connect|noiseGain\.connect|noiseSrc\.disconnect|noiseGain\.disconnect/g) || []).length,
};
console.log('STATIC NOISE-PATH AUDIT:');
Object.entries(audit).forEach(([k, v]) => console.log(`  ${k}: ${v}`));
const auditOk = audit['createBufferSource (noise sources)'] === 1 &&
  audit['noiseSrc.connect('] === 1 && audit['band g.connect(noiseGain)'] === 1 &&
  audit['noiseGain.connect(voiceBus)'] === 1 && audit['disconnect( anywhere'] === 0 &&
  audit['createDynamicsCompressor'] === 1 && audit['master.connect(comp)'] === 1 &&
  audit['noiseGain.gain.setValueCurveAtTime in playBurst'] === 1 &&
  audit['connect references to noise nodes inside playBurst'] === 0;
console.log(`NOISE-PATH AUDIT VERDICT: ${auditOk ? 'PASS — one fixed noise chain, zero per-burst connect/disconnect' : 'FAIL'}`);
