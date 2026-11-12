import numpy as np, subprocess, json
from scipy.io import wavfile
from scipy import signal as sig

SRC = '/home/hatch/workspace/bird-synth/samples/cardinal/XC75501.ogg'
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', SRC, '/tmp/xc75501.wav'], check=True)

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64); x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def env_db_fn(sr, x, lo, hi):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(0.003 * sr)); env = np.convolve(env, np.ones(k) / k, mode='same')
    return 20 * np.log10(env + 1e-6)

def segment(env_db, sr, on_db, off_db, min_off_ms=15, min_dur_ms=25):
    notes = []; state = False; start = 0; below = 0
    min_off = int(min_off_ms / 1000 * sr)
    for i in range(len(env_db)):
        if not state:
            if env_db[i] > on_db: state = True; start = i; below = 0
        else:
            if env_db[i] < off_db:
                below += 1
                if below >= min_off:
                    end = i - below
                    if (end - start) / sr * 1000 >= min_dur_ms: notes.append((start / sr, end / sr))
                    state = False; below = 0
            else: below = 0
    return notes

def track(sr, x):
    f, t, Z = sig.stft(x, fs=sr, nperseg=1024, noverlap=1024 - 128, window='hann')
    mag = np.abs(Z); band = (f >= 1300) & (f <= 9500); fb = f[band]; mb = mag[band]
    pk = np.argmax(mb, axis=0); pkf = fb[pk]; pkm = mb[pk, np.arange(mb.shape[1])]
    prom = 20 * np.log10(pkm / (np.median(mb, axis=0) + 1e-12))
    hr = np.zeros(mb.shape[1])
    for j in range(mb.shape[1]):
        i2 = np.argmin(np.abs(fb - 2 * pkf[j]))
        if fb[i2] < 9500: hr[j] = mb[i2, j] / (pkm[j] + 1e-12)
    return t, pkf, prom, hr

def rs(vals, npts=16):
    if len(vals) < 2: return [float(vals[0])] * npts
    return [float(v) for v in np.interp(np.linspace(0, 1, npts), np.linspace(0, 1, len(vals)), vals)]

def describe(sr, x, env_db, spans, t, pkf, prom, hr):
    hop = t[1] - t[0]; out = []
    for (t0, t1) in spans:
        j0, j1 = int(t0 / hop), max(int(t1 / hop), int(t0 / hop) + 2)
        seg = pkf[j0:j1].copy()
        if len(seg) >= 5: seg = sig.medfilt(seg, 3)
        e0, e1 = int(t0 * sr), int(t1 * sr)
        es = env_db[e0:e1]; amp = 10 ** ((es - es.max()) / 20.0)
        n = len(seg)
        out.append(dict(t0=round(float(t0), 3), t1=round(float(t1), 3), dur=round(float(t1 - t0), 3),
                        f_start=float(np.median(seg[:max(1, n // 5)])), f_end=float(np.median(seg[-max(1, n // 5):])),
                        f_peak=float(np.percentile(seg, 95)), f_min=float(np.percentile(seg, 5)),
                        prom_db=float(np.median(prom[j0:j1])), harm2=float(np.median(hr[j0:j1])),
                        contour=rs(seg), amp=rs(amp)))
    return out

sr, x = load('/tmp/xc75501.wav')
dur_total = len(x) / sr
print(f'sr={sr} duration={dur_total:.2f}s')

# ---------- contamination scan: LF rumble + broadband swells ----------
def band_db(sr, x, lo, hi, win_s=0.25):
    if lo is None:
        xb = x
    else:
        sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
        xb = sig.sosfiltfilt(sos, x)
    w = int(win_s * sr)
    n = len(xb) // w
    rms = np.sqrt(np.mean(xb[:n * w].reshape(n, w) ** 2, axis=1))
    return 20 * np.log10(rms + 1e-9), win_s

def find_swells(db, win_s, rise_db=7.0, min_dur_s=1.5, merge_gap_s=2.0, smooth_s=1.0):
    k = max(1, int(smooth_s / win_s))
    sm = np.convolve(db, np.ones(k) / k, mode='same')
    base = np.median(sm)
    above = sm > base + rise_db
    spans = []; run = 0; start = 0
    for i, a in enumerate(above):
        if a and run == 0: start = i; run = 1
        elif a: run += 1
        elif run: spans.append([start * win_s, i * win_s, float(sm[start:i].max() - base)]); run = 0
    if run: spans.append([start * win_s, len(above) * win_s, float(sm[start:].max() - base)])
    spans = [s for s in spans if s[1] - s[0] >= min_dur_s]
    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] <= merge_gap_s:
            merged[-1][1] = s[1]; merged[-1][2] = max(merged[-1][2], s[2])
        else: merged.append(list(s))
    return base, merged

lf_db, w = band_db(sr, x, 60, 500)
lf_base, lf_spans = find_swells(lf_db, w)
print(f'LF band 60-500 Hz: baseline {lf_base:.1f} dB, swell spans: {[(round(a,2), round(b,2), round(c,1)) for a,b,c in lf_spans]}')
bb_db, w2 = band_db(sr, x, None, None)
bb_base, bb_spans = find_swells(bb_db, w2)
print(f'Broadband: baseline {bb_base:.1f} dB, swell spans: {[(round(a,2), round(b,2), round(c,1)) for a,b,c in bb_spans]}')
# also print LF level profile every 1 s for eyeballing
prof = lf_db.reshape(-1, 4).mean(axis=1) if len(lf_db) % 4 == 0 else lf_db
print('LF dB per ~1s:', ' '.join(f'{v:.0f}' for v in prof))

# ---------- note segmentation (same method as v1) ----------
edb = env_db_fn(sr, x, 1500, 9000)
t, pkf, prom, hr = track(sr, x)
spansA = segment(edb, sr, -24.0, -31.0)
notesA = describe(sr, x, edb, spansA, t, pkf, prom, hr)
spansB = segment(edb, sr, -32.0, -38.0)
candB = describe(sr, x, edb, spansB, t, pkf, prom, hr)
extras = []
for c in candB:
    ov = any(min(c['t1'], a['t1']) - max(c['t0'], a['t0']) > 0.2 * c['dur'] for a in notesA)
    if not ov and c['prom_db'] >= 10 and 0.03 <= c['dur'] <= 0.25:
        extras.append(c)
print(f'\nbody notes: {len(notesA)}  sensitive-pass extras (prom>=10): {len(extras)}')
for c in extras: print('  extra:', c['t0'], c['dur'], round(c['f_start']), round(c['f_end']), 'prom', round(c['prom_db'], 1))

print('\nall body notes:')
for n in notesA:
    print(f"  t0={n['t0']:6.3f} dur={n['dur']:.3f} f {n['f_start']:7.0f} -> {n['f_end']:7.0f} peak {n['f_peak']:7.0f} min {n['f_min']:7.0f} prom {n['prom_db']:5.1f} h2 {n['harm2']:.3f}")

# bouts (gap > 1.0 s)
if notesA:
    bouts = []; cur = [notesA[0]]
    for a, b in zip(notesA, notesA[1:]):
        if b['t0'] - a['t1'] > 1.0: bouts.append(cur); cur = [b]
        else: cur.append(b)
    bouts.append(cur)
    print(f'\nbouts: {len(bouts)}')
    for i, b in enumerate(bouts):
        pause = round(bouts[i + 1][0]['t0'] - b[-1]['t1'], 3) if i + 1 < len(bouts) else None
        onsets = [round(n['t0'], 3) for n in b]
        print(f'  bout {i}: {len(b)} notes, {b[0]["t0"]:.2f}-{b[-1]["t1"]:.2f}s, pause_after={pause}, onsets={onsets}')

json.dump(dict(notes=notesA, extras=extras,
               lf_spans=lf_spans, bb_spans=bb_spans,
               lf_base=float(lf_base), bb_base=float(bb_base)),
          open('/tmp/xc75501_explore.json', 'w'), indent=1)
print('\nwrote /tmp/xc75501_explore.json')
