"""Generate the MEAS block for owl.html from great-horned-owl-measurements.json.

Derivation rules — identical to the cardinal v2 generator (documented in BUILD-owl.md):
- gridDur(type)  = max(1, round(durMed / 16th)) * 16th, 16th = 60/112/4 s (112 BPM grid, design choice)
- grid period    = max(1, round(periodMed / 16th)) * 16th per transition
- peak(type)     = round(0.46 * peak_amp_rel.median(type) / max over types, 3)  (0.46 = loudest-type gain, design scaling of a measurement)
- voice          = 1 for all positions: the hoots never overlap and come from one voice (design choice)
- fStart/fEnd/harm2/harm3 = measured medians; gridSeriesPause = 4.286 s (8 beats at 112 BPM, design choice)
"""
import json

SIXTEENTH = 60 / 112 / 4
d = json.load(open('/home/hatch/workspace/bird-synth/analysis/great-horned-owl-measurements.json'))
pos = d['positions']
max_amp = max(P['peak_amp_rel']['median'] for P in pos.values())

NAMES = {'1': 'Hoot 1 — the knock', '2': 'Hoot 2', '3': 'Hoot 3 — the long one', '4': 'Hoot 4 — the closer'}
ORDER = ['1', '2', '3', '4']

def grid_of(med):
    return round(max(1, round(med / SIXTEENTH)) * SIXTEENTH, 4)

out = []
out.append('const MEAS = {')
out.append('  "types": {')
for i, p in enumerate(ORDER):
    T = pos[p]
    peak = round(0.46 * T['peak_amp_rel']['median'] / max_amp, 3)
    out.append(f'    "P{p}": {{"name":"{NAMES[p]}","n":{T["n_instances"]},'
               f'"durMed":{T["dur_s"]["median"]},"durMin":{T["dur_s"]["min"]},"durMax":{T["dur_s"]["max"]},')
    out.append(f'      "fStart":{round(T["f_start_hz"]["median"], 1)},"fEnd":{round(T["f_end_hz"]["median"], 1)},'
               f'"gridDur":{grid_of(T["dur_s"]["median"])},"harm2":{T["harm2_ratio"]["median"]},'
               f'"harm3":{T["harm3_ratio"]["median"]},"peak":{peak},"voice":1,')
    out.append(f'      "contour":{json.dumps(T["contour_template_hz"])},')
    out.append(f'      "amp":{json.dumps(T["amp_template"])}}}' + (',' if i < len(ORDER) - 1 else ''))
out.append('  },')
out.append('  "grammar": {')
out.append('    "transitions": {')
tr = d['transitions']
keys = ['P1>P2', 'P2>P3', 'P3>P4']
for i, k in enumerate(keys):
    P = tr[k]['period_s']
    out.append(f'      "{k}": {{"min":{P["min"]},"med":{P["median"]},"max":{P["max"]},"grid":{grid_of(P["median"])}}}'
               + (',' if i < len(keys) - 1 else ''))
out.append('    },')
sp = d['series_pause_s']
out.append(f'    "seriesPause":[{sp["min"]},{sp["median"]},{sp["max"]}], "gridSeriesPause":4.286')
out.append('  }')
out.append('};')
block = '\n'.join(out)
open('/tmp/meas_block_owl.txt', 'w').write(block)
print(block)
