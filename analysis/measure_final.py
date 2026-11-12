import numpy as np, json
from scipy.io import wavfile
from scipy import signal as sig

CARD = '/home/hatch/workspace/bird-synth/samples/cardinal/'

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64); x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def env_db_fn(sr, x, lo, hi):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(0.003*sr)); env = np.convolve(env, np.ones(k)/k, mode='same')
    return 20*np.log10(env + 1e-6)

def segment(env_db, sr, on_db, off_db, min_off_ms=15, min_dur_ms=25):
    notes = []; state = False; start = 0; below = 0
    min_off = int(min_off_ms/1000*sr)
    for i in range(len(env_db)):
        if not state:
            if env_db[i] > on_db: state = True; start = i; below = 0
        else:
            if env_db[i] < off_db:
                below += 1
                if below >= min_off:
                    end = i - below
                    if (end-start)/sr*1000 >= min_dur_ms: notes.append((start/sr, end/sr))
                    state = False; below = 0
            else: below = 0
    return notes

def track(sr, x):
    f, t, Z = sig.stft(x, fs=sr, nperseg=1024, noverlap=1024-128, window='hann')
    mag = np.abs(Z); band = (f >= 1300) & (f <= 9500); fb = f[band]; mb = mag[band]
    pk = np.argmax(mb, axis=0); pkf = fb[pk]; pkm = mb[pk, np.arange(mb.shape[1])]
    prom = 20*np.log10(pkm/(np.median(mb, axis=0)+1e-12))
    hr = np.zeros(mb.shape[1])
    for j in range(mb.shape[1]):
        i2 = np.argmin(np.abs(fb - 2*pkf[j]))
        if fb[i2] < 9500: hr[j] = mb[i2, j]/(pkm[j]+1e-12)
    return t, pkf, prom, hr

def rs(vals, npts=16):
    if len(vals) < 2: return [float(vals[0])]*npts
    return [float(v) for v in np.interp(np.linspace(0,1,npts), np.linspace(0,1,len(vals)), vals)]

def describe(sr, x, env_db, spans, t, pkf, prom, hr):
    hop = t[1]-t[0]; out = []
    for (t0, t1) in spans:
        j0, j1 = int(t0/hop), max(int(t1/hop), int(t0/hop)+2)
        seg = pkf[j0:j1].copy()
        if len(seg) >= 5: seg = sig.medfilt(seg, 3)
        e0, e1 = int(t0*sr), int(t1*sr)
        es = env_db[e0:e1]; amp = 10**((es - es.max())/20.0)
        n = len(seg)
        out.append(dict(t0=round(float(t0),3), t1=round(float(t1),3), dur=round(float(t1-t0),3),
            f_start=float(np.median(seg[:max(1,n//5)])), f_end=float(np.median(seg[-max(1,n//5):])),
            f_peak=float(np.percentile(seg,95)), f_min=float(np.percentile(seg,5)),
            prom_db=float(np.median(prom[j0:j1])), harm2=float(np.median(hr[j0:j1])),
            contour=rs(seg), amp=rs(amp)))
    return out

def stat(vals):
    v = np.array(vals, dtype=float)
    return dict(median=round(float(np.median(v)), 3), min=round(float(v.min()), 3),
                max=round(float(v.max()), 3), n=int(len(v)))

def med_template(notes, key):
    arr = np.array([n[key] for n in notes])
    return [round(float(v), 4) for v in np.median(arr, axis=0)]

# ---------- XC1093538 ----------
sr, x = load(CARD+'XC1093538.wav')
edb = env_db_fn(sr, x, 1500, 9000)
t, pkf, prom, hr = track(sr, x)
spansA = segment(edb, sr, -24.0, -31.0)
notesA = describe(sr, x, edb, spansA, t, pkf, prom, hr)
spansB = segment(edb, sr, -32.0, -38.0)
candB = describe(sr, x, edb, spansB, t, pkf, prom, hr)
leadins = []
for c in candB:
    ov = any(min(c['t1'], a['t1']) - max(c['t0'], a['t0']) > 0.2*c['dur'] for a in notesA)
    if not ov and c['prom_db'] >= 10 and 0.03 <= c['dur'] <= 0.25:
        leadins.append(c)
print('body notes:', len(notesA), ' lead-in candidates:', [(c['t0'], c['dur'], round(c['f_start']), round(c['f_end'])) for c in leadins])

def ntype(n):
    if n['dur'] >= 0.098 and n['f_start'] < 2100 and n['f_peak'] > 3400: return 'F'
    if n['f_peak'] <= 2100 and n['f_start'] < 2100: return 'L'
    if n['f_start'] >= 3400 and n['f_end'] >= 2800: return 'V'
    if n['f_start'] >= 3000 and n['f_end'] < 2800: return 'H'
    return '?'
for n in notesA: n['type'] = ntype(n)
from collections import Counter
print('types:', Counter(n['type'] for n in notesA))
for n in notesA:
    if n['type'] == '?': print('  unclassified:', n['t0'], n['dur'], round(n['f_start']), round(n['f_end']), round(n['f_peak']))

# bouts on body notes (gap > 1.0 s)
bouts = []; cur = [notesA[0]]
for a, b in zip(notesA, notesA[1:]):
    if b['t0'] - a['t1'] > 1.0: bouts.append(cur); cur = [b]
    else: cur.append(b)
bouts.append(cur)
bout_info = []
for i, b in enumerate(bouts):
    gaps_in = [round(b[j+1]['t0']-b[j]['t1'], 3) for j in range(len(b)-1)]
    pause_after = round(bouts[i+1][0]['t0'] - b[-1]['t1'], 3) if i+1 < len(bouts) else None
    bout_info.append(dict(index=i, t_start=b[0]['t0'], t_end=b[-1]['t1'], n_notes=len(b),
        type_sequence=''.join(n['type'] for n in b),
        note_dur_s=stat([n['dur'] for n in b]), gap_in_s=stat(gaps_in) if gaps_in else None,
        pause_after_s=pause_after))
    print('bout', i, len(b), ''.join(n['type'] for n in b), 'pause_after', pause_after)

# L->H and H->L gaps within bouts
lh, hl = [], []
for b in bouts:
    for a, c in zip(b, b[1:]):
        g = c['t0'] - a['t1']
        if a['type'] == 'L' and c['type'] == 'H': lh.append(g)
        if a['type'] == 'H' and c['type'] == 'L': hl.append(g)
print('gap L->H', stat(lh), ' gap H->L', stat(hl))
# pair period: successive L onsets
lon = []
for b in bouts:
    ls = [n['t0'] for n in b if n['type'] == 'L']
    lon += [round(v-u, 3) for u, v in zip(ls, ls[1:])]
print('L onset period', stat(lon))

types = {}
for ty in ['L', 'H', 'F', 'V']:
    ns = [n for n in notesA if n['type'] == ty]
    if not ns: continue
    types[ty] = dict(n_instances=len(ns),
        dur_s=stat([n['dur'] for n in ns]),
        f_start_hz=stat([n['f_start'] for n in ns]), f_end_hz=stat([n['f_end'] for n in ns]),
        f_peak_hz=stat([n['f_peak'] for n in ns]), f_min_hz=stat([n['f_min'] for n in ns]),
        harm2_ratio=stat([n['harm2'] for n in ns]),
        contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in ns]), axis=0)],
        amp_template=med_template(ns, 'amp'))
    print(ty, types[ty]['n_instances'], 'dur', types[ty]['dur_s']['median'], 'f', types[ty]['f_start_hz']['median'], '->', types[ty]['f_end_hz']['median'])

# ---------- XC10170 ----------
import subprocess
subprocess.run(['ffmpeg','-y','-v','error','-i',CARD+'XC10170.mp3','/tmp/xc10170.wav'], check=True)
sr2, x2 = load('/tmp/xc10170.wav')
edb2 = env_db_fn(sr2, x2, 1300, 9000)
t2, pkf2, prom2, hr2 = track(sr2, x2)
spans2 = segment(edb2, sr2, -22.0, -30.0)
notes2 = describe(sr2, x2, edb2, spans2, t2, pkf2, prom2, hr2)
ds = [n for n in notes2 if 0.45 <= n['dur'] <= 0.80 and 3400 <= n['f_start'] <= 4100 and 1400 <= n['f_end'] <= 1900]
print('XC10170 main downslurs selected:', len(ds))
down = dict(n_instances=len(ds), dur_s=stat([n['dur'] for n in ds]),
    f_start_hz=stat([n['f_start'] for n in ds]), f_end_hz=stat([n['f_end'] for n in ds]),
    f_peak_hz=stat([n['f_peak'] for n in ds]), f_min_hz=stat([n['f_min'] for n in ds]),
    harm2_ratio=stat([n['harm2'] for n in ds]),
    contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in ds]), axis=0)],
    amp_template=med_template(ds, 'amp'))
print('downslur:', down['dur_s'], down['f_start_hz'], down['f_end_hz'])

out = dict(
  species='Northern Cardinal (Cardinalis cardinalis)',
  primary_reference=dict(file='XC1093538.wav', xeno_canto_id='XC1093538',
    recordist='Mario Reyes Jr', location='Lexington, Fayette County, Kentucky, US',
    license='CC BY-NC-SA 4.0', sample_rate_hz=sr, duration_s=round(len(x)/sr, 2)),
  phrase_shape_reference=dict(file='XC10170.mp3', xeno_canto_id='XC10170',
    recordist='Paul Jaszczak', location='Greenville, Pennsylvania, US', license='CC BY-NC-ND 2.5'),
  method=('STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in 1.3-9.5 kHz; note segmentation on the '
          '1.5-9 kHz band Hilbert envelope (3 ms smoothing): body pass onset -24 dB / offset -31 dB rel. file peak, '
          'min off-time 15 ms, min note 25 ms; quiet lead-in pass onset -32 / offset -38 dB, kept only if non-overlapping '
          'with body notes and spectral-peak prominence >= 10 dB. Note f_start/f_end = median track over first/last 20% '
          'of the note; f_peak/f_min = 95th/5th percentile. Contour and amplitude templates = per-note tracks resampled '
          'to 16 normalized points, median across instances of the type. Type rules: L = peak <= 2100 Hz; '
          'F = dur >= 0.098 s with low start and peak > 3400 Hz (fused L+H token); V = start >= 3400 Hz, end >= 2800 Hz; '
          'H = start >= 3000 Hz, end < 2800 Hz.'),
  body_note_count=len(notesA),
  lead_in_notes=[dict(t0=c['t0'], dur=c['dur'], f_start_hz=round(c['f_start']), f_end_hz=round(c['f_end']), f_peak_hz=round(c['f_peak'])) for c in leadins],
  bouts=bout_info,
  gap_L_to_H_s=stat(lh), gap_H_to_L_s=stat(hl), pair_period_L_onsets_s=stat(lon),
  phrase_types=types,
  xc10170_main_downslur=down)
json.dump(out, open('/home/hatch/workspace/bird-synth/analysis/cardinal-measurements.json', 'w'), indent=1)
print('JSON written')
