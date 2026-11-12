"""Verify owl.html: node --check, constant audit vs measurements JSON,
headless series-generator logic tests, static breath-path audit."""
import json, re, subprocess, sys

HTML = open('/home/hatch/workspace/bird-synth/owl.html').read()
MEASJ = json.load(open('/home/hatch/workspace/bird-synth/analysis/great-horned-owl-measurements.json'))

script = HTML.split('<script>')[1].split('</script>')[0]
open('/tmp/owl_script.js', 'w').write(script)
r = subprocess.run(['node', '--check', '/tmp/owl_script.js'], capture_output=True, text=True)
print('node --check:', 'PASS' if r.returncode == 0 else 'FAIL\n' + r.stderr)
assert r.returncode == 0

# ---------- constant audit ----------
meas_txt = script[script.index('const MEAS = {'):script.index('\n};') + 3]
meas = json.loads(meas_txt.replace('const MEAS = ', '').rstrip(';'))
SIXTEENTH = 60 / 112 / 4
def grid_of(med): return round(max(1, round(med / SIXTEENTH)) * SIXTEENTH, 4)

checks = 0; fails = []
def cmp(label, a, b, tol=1e-9):
    global checks; checks += 1
    if abs(a - b) > tol: fails.append(f'{label}: page {a} != measured {b}')

pos = MEASJ['positions']
max_amp = max(P['peak_amp_rel']['median'] for P in pos.values())
for p in ['1', '2', '3', '4']:
    T, J = meas['types']['P' + p], pos[p]
    cmp(f'P{p}.n', T['n'], J['n_instances'])
    for pk, jk in (('durMed', 'median'), ('durMin', 'min'), ('durMax', 'max')):
        cmp(f'P{p}.{pk}', T[pk], J['dur_s'][jk])
    cmp(f'P{p}.fStart', T['fStart'], round(J['f_start_hz']['median'], 1))
    cmp(f'P{p}.fEnd', T['fEnd'], round(J['f_end_hz']['median'], 1))
    cmp(f'P{p}.harm2', T['harm2'], J['harm2_ratio']['median'])
    cmp(f'P{p}.harm3', T['harm3'], J['harm3_ratio']['median'])
    cmp(f'P{p}.peak', T['peak'], round(0.46 * J['peak_amp_rel']['median'] / max_amp, 3))
    cmp(f'P{p}.gridDur', T['gridDur'], grid_of(J['dur_s']['median']))
    cmp(f'P{p}.voice', T['voice'], 1)
    for i, (a, b) in enumerate(zip(T['contour'], J['contour_template_hz'])):
        cmp(f'P{p}.contour[{i}]', a, b)
    for i, (a, b) in enumerate(zip(T['amp'], J['amp_template'])):
        cmp(f'P{p}.amp[{i}]', a, b)
for k, J in MEASJ['transitions'].items():
    T = meas['grammar']['transitions'][k]
    for pk, jk in (('min', 'min'), ('med', 'median'), ('max', 'max')):
        cmp(f'{k}.{pk}', T[pk], J['period_s'][jk])
    cmp(f'{k}.grid', T['grid'], grid_of(J['period_s']['median']))
sp = MEASJ['series_pause_s']
for i, jk in enumerate(('min', 'median', 'max')):
    cmp(f'seriesPause[{i}]', meas['grammar']['seriesPause'][i], sp[jk])
cmp('gridSeriesPause', meas['grammar']['gridSeriesPause'], 4.286)
print(f'constant audit: {checks} values compared, {len(fails)} mismatches')
for f in fails: print('  MISMATCH', f)
assert not fails

# ---------- headless generator logic tests ----------
i0 = script.index('const MEAS = {'); i1 = script.index('\n};', i0) + 3
block = script[i0:i1]
for fn in ('function quantize', 'function morphFreq', 'function sampleIn', 'function makeSeriesPlan'):
    j0 = script.index(fn); j1 = script.index('\n}\n', j0) + 3
    block += '\n' + script[j0:j1]
block += '\nconst lerp=(a,b,t)=>a+(b-a)*t;\n' if 'const lerp' not in block else ''
# lerp is defined before sampleIn in the page; pull its real definition instead
j0 = script.index('const lerp'); j1 = script.index('\n', j0)
block = block.replace('\nconst lerp=(a,b,t)=>a+(b-a)*t;\n', '\n' + script[j0:j1] + '\n')
block += """
let morph=0;
let bad=0, spans=[];
for (let n=0;n<2000;n++){
  const plan = makeSeriesPlan();
  if (plan.evs.length!==4) bad++;
  if (plan.evs.map(e=>e.type).join(',')!=='P1,P2,P3,P4') bad++;
  for (let i=1;i<4;i++) if (!(plan.evs[i].birdOff>plan.evs[i-1].birdOff)) bad++;
  for (let i=1;i<4;i++) if (!(plan.evs[i].gridOff>plan.evs[i-1].gridOff)) bad++;
  spans.push(plan.durBird);
}
spans.sort((a,b)=>a-b);
console.log('plans: 2000, structural failures:', bad, '| span min', spans[0].toFixed(3), 'max', spans[spans.length-1].toFixed(3));
if (bad) process.exit(1);
if (spans[0] < 2.50 || spans[spans.length-1] > 2.58) { console.log('SPAN OUT OF ENVELOPE'); process.exit(1); }
morph=0; if (morphFreq(323.0)!==323.0) { console.log('morph identity FAIL'); process.exit(1); }
morph=1;
const PENTA=new Set([9,11,1,4,6]);
for (const f of [301.5,312.2,317.6,323.0,306.8]){
  const q = quantize(f), pc = ((Math.round(69+12*Math.log2(q/440))%12)+12)%12;
  if (!PENTA.has(pc)) { console.log('quantize off-scale FAIL', f, q); process.exit(1); }
}
console.log('morph identity at 0: PASS | quantize lands on A-major-pentatonic for all template landmarks: PASS');
"""
open('/tmp/owl_logic.js', 'w').write(block)
r = subprocess.run(['node', '/tmp/owl_logic.js'], capture_output=True, text=True)
print(r.stdout.strip()); print(r.stderr.strip())
assert r.returncode == 0

# ---------- static breath-path audit ----------
def count(pat): return len(re.findall(pat, script))
audit = {}
audit['noise source creations (createBufferSource)'] = count(r'createBufferSource\(\)')
audit['noiseSrc.connect calls (noise -> bandpass, once)'] = count(r'noiseSrc\.connect\(')
audit['breathGain.connect calls (breath -> master, once)'] = count(r'breathGain\.connect\(')
audit['DynamicsCompressor creations'] = count(r'createDynamicsCompressor\(\)')
audit['breathGain.gain.setValueCurveAtTime calls'] = count(r'breathGain\.gain\.setValueCurveAtTime')
audit['BREATH_REL = 0.05 declaration'] = count(r'const BREATH_REL = 0\.05')
pn = script[script.index('function playNote'):script.index('/* ================= Sing')]
audit['connect() calls inside playNote'] = len(re.findall(r'\.connect\(', pn))
audit['breath/noise connect or disconnect inside playNote'] = len(re.findall(r'(breathGain|noiseSrc|nf)\.(connect|disconnect)', pn))
audit['disconnect() calls anywhere in script'] = count(r'\.disconnect\(')
audit['breath endpoints forced to 0'] = 1 if '(i===0 || i===T.amp.length-1) ? 0' in pn else 0
audit['breath curve peak factor = BREATH_REL'] = 1 if 'a*peak*BREATH_REL' in pn else 0
audit['breathGain initialized to 0'] = 1 if 'breathGain.gain.value=0' in script else 0
for k, v in audit.items(): print(f'  audit: {k} = {v}')
assert audit['noise source creations (createBufferSource)'] == 1
assert audit['noiseSrc.connect calls (noise -> bandpass, once)'] == 1
assert audit['breathGain.connect calls (breath -> master, once)'] == 1
assert audit['DynamicsCompressor creations'] == 1
assert audit['breath/noise connect or disconnect inside playNote'] == 0
assert audit['disconnect() calls anywhere in script'] == 0
assert audit['breath endpoints forced to 0'] == 1
assert audit['breath curve peak factor = BREATH_REL'] == 1
assert audit['breathGain initialized to 0'] == 1
print('breath-path audit: PASS — exactly one fixed noise path, shaped only on its single gain; per-note connect/disconnect on it: 0')
print('ALL VERIFICATION PASSED')
