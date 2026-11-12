import numpy as np, json, subprocess
from scipy.io import wavfile
from scipy import signal as sig
from collections import Counter

BASE='/home/hatch/workspace/bird-synth/'
subprocess.run(['ffmpeg','-y','-v','error','-i',BASE+'samples/carolina-wren/XC364592.mp3','/tmp/cw364592.wav'],check=True)

def load(path):
    sr,x=wavfile.read(path)
    if x.ndim>1: x=x[:,0]
    x=x.astype(np.float64); pk=np.max(np.abs(x)); x/= (pk+1e-12)
    return sr,x,pk

def env_db_fn(sr,x,lo,hi):
    sos=sig.butter(4,[lo,hi],btype='band',fs=sr,output='sos')
    xb=sig.sosfilt(sos,x); env=np.abs(sig.hilbert(xb))
    k=max(1,int(0.003*sr)); env=np.convolve(env,np.ones(k)/k,mode='same')
    return 20*np.log10(env+1e-6)

def segment(env_db,sr,on_db,off_db,min_off_ms=12,min_dur_ms=20):
    notes=[]; state=False; start=0; below=0; min_off=int(min_off_ms/1000*sr)
    for i in range(len(env_db)):
        if not state:
            if env_db[i]>on_db: state=True; start=i; below=0
        else:
            if env_db[i]<off_db:
                below+=1
                if below>=min_off:
                    end=i-below
                    if (end-start)/sr*1000>=min_dur_ms: notes.append((start/sr,end/sr))
                    state=False; below=0
            else: below=0
    return notes

def track(sr,x):
    f,t,Z=sig.stft(x,fs=sr,nperseg=1024,noverlap=1024-128,window='hann')
    mag=np.abs(Z); band=(f>=1200)&(f<=9500); fb=f[band]; mb=mag[band]
    pk=np.argmax(mb,axis=0); pkf=fb[pk]; pkm=mb[pk,np.arange(mb.shape[1])]
    prom=20*np.log10(pkm/(np.median(mb,axis=0)+1e-12))
    h2=np.zeros(mb.shape[1]); h3=np.zeros(mb.shape[1])
    for j in range(mb.shape[1]):
        i2=np.argmin(np.abs(fb-2*pkf[j])); 
        if fb[i2]<9500: h2[j]=mb[i2,j]/(pkm[j]+1e-12)
        i3=np.argmin(np.abs(fb-3*pkf[j]))
        if fb[i3]<9500: h3[j]=mb[i3,j]/(pkm[j]+1e-12)
    return t,pkf,prom,h2,h3

def rs(vals,npts=16):
    if len(vals)<2: return [float(vals[0])]*npts
    return [float(v) for v in np.interp(np.linspace(0,1,npts),np.linspace(0,1,len(vals)),vals)]

def describe(sr,x,env_db,spans,t,pkf,prom,h2,h3):
    hop=t[1]-t[0]; out=[]
    for (t0,t1) in spans:
        j0,j1=int(t0/hop),max(int(t1/hop),int(t0/hop)+2)
        seg=pkf[j0:j1].copy()
        if len(seg)>=5: seg=sig.medfilt(seg,3)
        e0,e1=int(t0*sr),int(t1*sr); es=env_db[e0:e1]; amp=10**((es-es.max())/20.0)
        n=len(seg)
        out.append(dict(t0=round(float(t0),3),t1=round(float(t1),3),dur=round(float(t1-t0),3),
            f_start=float(np.median(seg[:max(1,n//5)])),f_end=float(np.median(seg[-max(1,n//5):])),
            f_peak=float(np.percentile(seg,95)),f_min=float(np.percentile(seg,5)),
            prom_db=float(np.median(prom[j0:j1])),harm2=float(np.median(h2[j0:j1])),harm3=float(np.median(h3[j0:j1])),
            peak_amp=float(np.max(10**(es/20.0))),contour=rs(seg),amp=rs(amp)))
    return out

def stat(vals):
    v=np.array(vals,dtype=float)
    if len(v)==0: return None
    return dict(median=round(float(np.median(v)),3),min=round(float(v.min()),3),max=round(float(v.max()),3),n=int(len(v)))
def med_template(notes,key): return [round(float(v),4) for v in np.median(np.array([n[key] for n in notes]),axis=0)]

def band_db(sr,x,lo,hi,win_s=0.25):
    if lo is None: xb=x
    else:
        sos=sig.butter(4,[lo,hi],btype='band',fs=sr,output='sos'); xb=sig.sosfiltfilt(sos,x)
    w=int(win_s*sr); n=len(xb)//w; rms=np.sqrt(np.mean(xb[:n*w].reshape(n,w)**2,axis=1))
    return 20*np.log10(rms+1e-9),win_s
def find_swells(db,win_s,rise_db=7.0,min_dur_s=1.5,merge_gap_s=2.0,smooth_s=1.0):
    k=max(1,int(smooth_s/win_s)); sm=np.convolve(db,np.ones(k)/k,mode='same'); base=float(np.median(sm))
    above=sm>base+rise_db; spans=[]; run=0; start=0
    for i,a in enumerate(above):
        if a and run==0: start=i; run=1
        elif a: run+=1
        elif run: spans.append([round(start*win_s,2),round(i*win_s,2),round(float(sm[start:i].max()-base),1)]); run=0
    spans=[s for s in spans if s[1]-s[0]>=min_dur_s]
    merged=[]
    for s in spans:
        if merged and s[0]-merged[-1][1]<=merge_gap_s: merged[-1][1]=s[1]; merged[-1][2]=max(merged[-1][2],s[2])
        else: merged.append(list(s))
    return base,merged

sr,x,rawpeak=load('/tmp/cw364592.wav')
print(f'sr={sr} dur={len(x)/sr:.2f} rawpeak={rawpeak}')
# gap contrast 0.25s windows full band
gdb,_=band_db(sr,x,None,None)
print(f'gap windows: min {gdb.min():.1f} p5 {np.percentile(gdb,5):.1f} p10 {np.percentile(gdb,10):.1f} median {np.median(gdb):.1f} p90 {np.percentile(gdb,90):.1f} max {gdb.max():.1f}')
lf_db,w1=band_db(sr,x,60,500); lf_base,lf_spans=find_swells(lf_db,w1)
bb_db,w2=band_db(sr,x,None,None); bb_base,bb_spans=find_swells(bb_db,w2)
print('LF baseline',round(lf_base,1),'swells',lf_spans)
print('BB baseline',round(bb_base,1),'swells',bb_spans)
# per-second LF share
for s0 in range(0,int(len(x)/sr)):
    seg=x[int(s0*sr):int((s0+1)*sr)]
    sos=sig.butter(4,[60,500],btype='band',fs=sr,output='sos'); lb=sig.sosfiltfilt(sos,seg)
    share=np.mean(lb**2)/(np.mean(seg**2)+1e-12)
    print(f'  sec {s0:2d} LFshare {share:.3f} rms_db {20*np.log10(np.sqrt(np.mean(seg**2))+1e-12):.1f}')

EXCLUDE=(28.4,36.21)  # tail: loud low-frequency bursts / other vocalisations in spectrogram, not wren song phrases
edb=env_db_fn(sr,x,1500,9000)
t,pkf,prom,h2,h3=track(sr,x)
spans=segment(edb,sr,-24.0,-31.0)
notes=describe(sr,x,edb,spans,t,pkf,prom,h2,h3)
notes=[n for n in notes if n['t1']<EXCLUDE[0]]
print('syllable-notes kept (t<28.4):',len(notes))
for n in notes: print(round(n['t0'],2),round(n['dur'],3),round(n['f_start']),round(n['f_end']),round(n['f_peak']),'h2',round(n['harm2'],3),'h3',round(n['harm3'],3),'amp',round(n['peak_amp'],3))

# phrases: group syllables at gap>0.45s ; bouts: group phrases at gap>1.8s
phrases=[]; cur=[notes[0]]
for a,b in zip(notes,notes[1:]):
    if b['t0']-a['t1']>0.45: phrases.append(cur); cur=[b]
    else: cur.append(b)
phrases.append(cur)
print('phrases:',len(phrases))
phr_info=[]
for p in phrases:
    print(' phrase',p[0]['t0'],'-',p[-1]['t1'],'nsyll',len(p),'syll dur med',round(float(np.median([n['dur'] for n in p])),3),'fstart med',round(float(np.median([n['f_start'] for n in p]))),'fpeak med',round(float(np.median([n['f_peak'] for n in p]))))
    phr_info.append(p)
# Save intermediate for typing inspection
json.dump([dict(t0=p[0]['t0'],t1=p[-1]['t1'],nsyll=len(p),syll_durs=[n['dur'] for n in p],f_starts=[round(n['f_start']) for n in p],f_ends=[round(n['f_end']) for n in p],f_peaks=[round(n['f_peak']) for n in p]) for p in phrases],open('/tmp/cw_phrases.json','w'),indent=1)
json.dump(notes,open('/tmp/cw_notes.json','w'),indent=1)

# ---------- final: typing, clusters (=bouts), transitions, JSON ----------
def ntype(n):
    if n['dur']>=0.13: return 'L'
    if n['dur']<0.075 and 2400<=n['f_start']<=2800 and n['f_end']<2300: return 'D'
    if n['dur']<0.075 and 2700<=n['f_start']<=3100 and n['f_end']>2900: return 'U'
    return 'S'
for n in notes: n['type']=ntype(n)
print('types:',Counter(n['type'] for n in notes))
bouts=[]; cur=[notes[0]]
for a,b in zip(notes,notes[1:]):
    if b['t0']-a['t1']>0.45: bouts.append(cur); cur=[b]
    else: cur.append(b)
bouts.append(cur)
bout_info=[]
for i,b in enumerate(bouts):
    gaps=[round(b[j+1]['t0']-b[j]['t1'],3) for j in range(len(b)-1)]
    pause_after=round(bouts[i+1][0]['t0']-b[-1]['t1'],3) if i+1<len(bouts) else None
    bout_info.append(dict(index=i,t_start=b[0]['t0'],t_end=b[-1]['t1'],n_notes=len(b),
        type_sequence=' '.join(n['type'] for n in b),
        note_dur_s=stat([n['dur'] for n in b]),gap_in_s=stat(gaps) if gaps else None,pause_after_s=pause_after))
trans={}
for b in bouts:
    for a,c in zip(b,b[1:]):
        k=a['type']+'>'+c['type']; trans.setdefault(k,dict(period=[],gap=[]))
        trans[k]['period'].append(c['t0']-a['t0']); trans[k]['gap'].append(c['t0']-a['t1'])
trans_out={k:dict(period_s=stat(v['period']),gap_s=stat(v['gap'])) for k,v in sorted(trans.items())}
pauses=[b['pause_after_s'] for b in bout_info if b['pause_after_s'] is not None]
types={}
for ty in ['D','U','L','S']:
    ns=[n for n in notes if n['type']==ty]
    if not ns: continue
    types[ty]=dict(n_instances=len(ns),dur_s=stat([n['dur'] for n in ns]),
        f_start_hz=stat([n['f_start'] for n in ns]),f_end_hz=stat([n['f_end'] for n in ns]),
        f_peak_hz=stat([n['f_peak'] for n in ns]),f_min_hz=stat([n['f_min'] for n in ns]),
        harm2_ratio=stat([n['harm2'] for n in ns]),harm3_ratio=stat([n['harm3'] for n in ns]),
        peak_amp_rel=stat([n['peak_amp'] for n in ns]),
        contour_template_hz=[round(float(v),1) for v in np.median(np.array([n['contour'] for n in ns]),axis=0)],
        amp_template=med_template(ns,'amp'))
    print(ty,types[ty]['n_instances'],'dur',types[ty]['dur_s'],'f',types[ty]['f_start_hz']['median'],'->',types[ty]['f_end_hz']['median'],'h2',types[ty]['harm2_ratio']['median'],'h3',types[ty]['harm3_ratio']['median'],'peak',types[ty]['peak_amp_rel']['median'])
out=dict(
 species='Carolina Wren (Thryothorus ludovicianus)',
 primary_reference=dict(file='XC364592.mp3',xeno_canto_id='XC364592',recordist='Brian Murphy',
   location='Schenck Forest, Wake County, North Carolina, US',date='2017-04-14',time='11:30',
   license='UNVERIFIED — recording page bot-gated (Anubis) on 2026-11-11; see SOURCES.md',
   xc_grade='UNVERIFIED — recording page bot-gated (Anubis) on 2026-11-11; see SOURCES.md',
   sample_rate_hz=int(sr),duration_s=round(len(x)/sr,2),
   file_specs='MP3 320 kbps, 44.1 kHz mono (as downloaded from xeno-canto direct file URL)'),
 method=('STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in 1.2-9.5 kHz; syllable segmentation on the '
   '1.5-9 kHz band Hilbert envelope (3 ms smoothing): onset -24 dB / offset -31 dB rel. file peak, min off-time '
   '12 ms, min syllable 20 ms. f_start/f_end = median track over first/last 20% of the syllable; f_peak/f_min = '
   '95th/5th percentile. peak_amp_rel = max of the 1.5-9 kHz band envelope (linear, signal peak-normalized). '
   'Contour and amplitude templates = per-syllable tracks resampled to 16 normalized points, median across '
   'instances of the type. Harmonic ratios = median STFT magnitude at 2f0 / 3f0 relative to f0 within the syllable. '
   'Type rules (this bird, by contour): L (long ringing syllable) = dur >= 0.13 s; D (down-chip) = dur < 0.075 s, '
   'f_start 2400-2800 Hz, f_end < 2300 Hz; U (up-chirp) = dur < 0.075 s, f_start 2700-3100 Hz, f_end > 2900 Hz; '
   'S (short fragment) = all remaining short syllables. Bouts = syllable groups split at gaps > 0.45 s. '
   'Contamination scan: short-time RMS in 0.25 s windows for the 60-500 Hz band and full band; a swell = 1 s-smoothed '
   'level > file median + 7 dB sustained >= 1.5 s (spans < 2 s apart merged). Gap contrast: 0.25 s full-band RMS windows.'),
 gap_contrast=dict(window_s=0.25,min_db=round(float(gdb.min()),1),p10_db=round(float(np.percentile(gdb,10)),1),
   median_db=round(float(np.median(gdb)),1),p90_db=round(float(np.percentile(gdb,90)),1),max_db=round(float(gdb.max()),1),
   note='Levels are dB RMS relative to the peak-normalized file (0 dB = file peak sample). Quietest (gap) windows sit at -53 to -52 dB; phrase windows reach -13.4 dB (max) / -22.7 dB (p90): ~29-39 dB phrase-to-floor separation.'),
 contamination_scan=dict(low_freq_band_hz=[60,500],lf_baseline_db=round(float(lf_base),1),lf_swell_spans_s=lf_spans,
   broadband_baseline_db=round(float(bb_base),1),broadband_swell_spans_s=bb_spans,
   broadband_spans_explained='Broadband rises at 0.0-1.75, 5.75-7.5, 10.75-12.25, 15.75-17.5 and 21.0-22.5 s coincide with the wren bouts; through those spans the 60-500 Hz band stays at baseline, so the energy is the bird song, not rumble. The rise at 28.25-30.5 s coincides with the low-frequency swell.',
   verdict='One low-frequency swell found: 28.0-33.5 s (+33.3 dB over the -54.2 dB LF baseline), matching loud low bursts visible in the spectrogram from ~28.5 s to the end of the file. That span is EXCLUDED from all templates and grammar; no syllable at t >= 28.4 s was used. No LF swell anywhere in 0-28.4 s.',
   excluded_spans_s=[[28.4,36.21]]),
 body_note_count=len(notes),
 bouts=bout_info,transitions=trans_out,bout_pause_s=stat(pauses),phrase_types=types)
json.dump(out,open(BASE+'analysis/carolina-wren-measurements.json','w'),indent=1)
print('JSON written: analysis/carolina-wren-measurements.json')
