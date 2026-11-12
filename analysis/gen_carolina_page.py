import json
M=json.load(open('/home/hatch/workspace/bird-synth/analysis/carolina-wren-measurements.json'))
BEAT=60/112; SIX=BEAT/4
def grid_dur(d): return round(max(1,round(d/SIX))*SIX,4)
def grid_period(p): return round(max(1,round(p/SIX))*SIX,4)
names={'D':'Down-chip','U':'Up-chirp','L':'Long ringing syllable','S':'Short high fragment'}
voices={'D':0,'U':1,'L':0,'S':1}
types={}
for k,v in M['phrase_types'].items():
    types[k]=dict(name=names[k],n=v['n_instances'],durMed=v['dur_s']['median'],durMin=v['dur_s']['min'],durMax=v['dur_s']['max'],
        fStart=round(v['f_start_hz']['median'],1),fEnd=round(v['f_end_hz']['median'],1),gridDur=grid_dur(v['dur_s']['median']),
        harm2=v['harm2_ratio']['median'],harm3=v['harm3_ratio']['median'],peak=v['peak_amp_rel']['median'],voice=voices[k],
        contour=v['contour_template_hz'],amp=v['amp_template'])
trans={}
for k,v in M['transitions'].items():
    trans[k]=dict(min=v['period_s']['min'],med=v['period_s']['median'],max=v['period_s']['max'],grid=grid_period(v['period_s']['median']))
# fallback: min of mins, max of maxes, n-weighted mean of medians (derived, documented)
tot=sum(v['period_s']['n'] for v in M['transitions'].values())
fb=dict(min=min(v['period_s']['min'] for v in M['transitions'].values()),
        med=round(sum(v['period_s']['median']*v['period_s']['n'] for v in M['transitions'].values())/tot,3),
        max=max(v['period_s']['max'] for v in M['transitions'].values()),grid=grid_period(0.14))
bp=M['bout_pause_s']
seqs=[b['type_sequence'].split() for b in M['bouts']]
meas=dict(types=types,grammar=dict(transitions=trans,boutPause=[bp['min'],bp['median'],bp['max']],
    gridBoutPause=round(round(bp['median']/BEAT)*BEAT,4),sequences=seqs,fallback=fb))
meas_js=json.dumps(meas,indent=2)
html=open('/tmp/cw_template.html').read()
html=html.replace('__MEAS_JSON__',meas_js)
# landmarks: D fEnd, U fEnd, L fStart, S fEnd (medians)
lm=[round(M['phrase_types']['D']['f_end_hz']['median']),round(M['phrase_types']['U']['f_end_hz']['median']),
    round(M['phrase_types']['L']['f_start_hz']['median']),round(M['phrase_types']['S']['f_end_hz']['median'])]
html=html.replace('__LANDMARKS__',json.dumps(lm))
open('/home/hatch/workspace/bird-synth/carolina-wren.html','w').write(html)
print('page written; landmarks',lm,'transitions',len(trans),'seq syllables',sum(len(s) for s in seqs))
