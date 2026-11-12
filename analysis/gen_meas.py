"""Generate the MEAS block for cardinal.html (v2) from cardinal-measurements-xc75501.json.

Derivation rules (all documented in BUILD.md):
- gridDur(type)  = max(1, round(durMed / 16th)) * 16th, 16th = 60/112/4 s (112 BPM grid, design choice)
- grid period    = max(1, round(periodMed / 16th)) * 16th per transition
- peak(type)     = round(0.46 * peak_amp_rel.median(type) / max over types, 3)  (0.46 = loudest-type gain, design scaling of a measurement)
- voice          = v1 convention by pitch region: D (low figure) -> 0 (left), Ua/Ub/C -> 1 (right)
- fStart/fEnd    = measured medians rounded to 0.1 Hz; harm2 = measured median ratio
"""
import json

SIXTEENTH = 60 / 112 / 4
d = json.load(open('/home/hatch/workspace/bird-synth/analysis/cardinal-measurements-xc75501.json'))
types = d['phrase_types']
max_amp = max(T['peak_amp_rel']['median'] for T in types.values())

NAMES = {'Ua': 'First upslur', 'Ub': 'Second upslur', 'D': 'Downslur', 'C': 'High chip'}
VOICE = {'Ua': 1, 'Ub': 1, 'D': 0, 'C': 1}
ORDER = ['Ua', 'Ub', 'D', 'C']

def grid_of(med):
    return round(max(1, round(med / SIXTEENTH)) * SIXTEENTH, 4)

out = []
out.append('const MEAS = {')
out.append('  "types": {')
for i, ty in enumerate(ORDER):
    T = types[ty]
    peak = round(0.46 * T['peak_amp_rel']['median'] / max_amp, 3)
    out.append(f'    "{ty}": {{"name":"{NAMES[ty]}","n":{T["n_instances"]},'
               f'"durMed":{T["dur_s"]["median"]},"durMin":{T["dur_s"]["min"]},"durMax":{T["dur_s"]["max"]},')
    out.append(f'      "fStart":{round(T["f_start_hz"]["median"], 1)},"fEnd":{round(T["f_end_hz"]["median"], 1)},'
               f'"gridDur":{grid_of(T["dur_s"]["median"])},"harm2":{T["harm2_ratio"]["median"]},'
               f'"peak":{peak},"voice":{VOICE[ty]},')
    out.append(f'      "contour":{json.dumps(T["contour_template_hz"])},')
    out.append(f'      "amp":{json.dumps(T["amp_template"])}}}' + (',' if i < len(ORDER) - 1 else ''))
out.append('  },')
out.append('  "grammar": {')
out.append('    "transitions": {')
tr = d['transitions']
keys = ['Ua>Ub', 'Ub>D', 'D>D', 'D>C', 'C>C']
for i, k in enumerate(keys):
    P = tr[k]['period_s']
    out.append(f'      "{k}": {{"min":{P["min"]},"med":{P["median"]},"max":{P["max"]},"grid":{grid_of(P["median"])}}}'
               + (',' if i < len(keys) - 1 else ''))
out.append('    },')
bp = d['bout_pause_s']
out.append(f'    "boutPause":[{bp["min"]},{bp["median"]},{bp["max"]}], "gridBoutPause":4.286,')
out.append('    "forms":{"A":0.6,"B":0.2,"C":0.2},')
out.append('    "aRun":[4,5,6], "bRun":7, "cRun":10')
out.append('  }')
out.append('};')
block = '\n'.join(out)
open('/tmp/meas_block.txt', 'w').write(block)
print(block)

# splice into cardinal.html
html = open('/home/hatch/workspace/bird-synth/cardinal.html').read()
i = html.index('const MEAS = {')
j = html.index('\n};', i) + len('\n};')
html = html[:i] + block + html[j:]
open('/home/hatch/workspace/bird-synth/cardinal.html', 'w').write(html)
print('\nspliced into cardinal.html')
