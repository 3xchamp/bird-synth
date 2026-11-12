import numpy as np, json, subprocess
from scipy.io import wavfile
from scipy import signal as sig
from collections import Counter

OWL = '/home/hatch/workspace/bird-synth/samples/great-horned-owl/'
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', OWL + 'XC11638.mp3', '/tmp/xc11638.wav'], check=True)

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64); x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def env_db_fn(sr, x, lo, hi):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(0.005 * sr)); env = np.convolve(env, np.ones(k) / k, mode='same')
    return 20 * np.log10(env + 1e-6)

def segment(env_db, sr, on_db, off_db, min_off_ms=60, min_dur_ms=120):
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
    if state and (len(env_db) - start) / sr * 1000 >= min_dur_ms:
        notes.append((start / sr, len(env_db) / sr))
    return notes

def track(sr, x):
    # low-frequency hoots: 4096-pt window -> 10.8 Hz bins, 256 hop -> 5.8 ms steps
    f, t, Z = sig.stft(x, fs=sr, nperseg=4096, noverlap=4096 - 256, window='hann')
    mag = np.abs(Z); band = (f >= 150) & (f <= 900); fb = f[band]; mb = mag[band]
    pk = np.argmax(mb, axis=0); pkf = fb[pk]; pkm = mb[pk, np.arange(mb.shape[1])]
    prom = 20 * np.log10(pkm / (np.median(mb, axis=0) + 1e-12))
    hr2 = np.zeros(mb.shape[1]); hr3 = np.zeros(mb.shape[1])
    for j in range(mb.shape[1]):
        for mult, arr in ((2, hr2), (3, hr3)):
            i2 = np.argmin(np.abs(f - mult * pkf[j]))
            if f[i2] < 1200: arr[j] = mag[i2, j] / (pkm[j] + 1e-12)
    return t, pkf, prom, hr2, hr3

def rs(vals, npts=16):
    if len(vals) < 2: return [float(vals[0])] * npts
    return [float(v) for v in np.interp(np.linspace(0, 1, npts), np.linspace(0, 1, len(vals)), vals)]

def describe(sr, x, env_db, spans, t, pkf, prom, hr2, hr3):
    hop = t[1] - t[0]; out = []
    for (t0, t1) in spans:
        j0, j1 = int(t0 / hop), max(int(t1 / hop), int(t0 / hop) + 2)
        # keep only frames where the band envelope is well above the -30 dB in-band
        # floor (the floor is low-frequency noise that wanders 200-290 Hz; unmasked
        # edge frames would track it instead of the hoot)
        fr = np.arange(j0, j1)
        samp = np.clip((t[fr] * sr).astype(int), 0, len(env_db) - 1)
        keep = env_db[samp] >= -22.0
        if keep.sum() < 3: keep = np.ones(len(fr), dtype=bool)
        seg = pkf[j0:j1][keep].copy()
        pr = prom[j0:j1][keep]; h2 = hr2[j0:j1][keep]; h3 = hr3[j0:j1][keep]
        if len(seg) >= 5: seg = sig.medfilt(seg, 3)
        e0, e1 = int(t0 * sr), int(t1 * sr)
        es = env_db[e0:e1]; amp = 10 ** ((es - es.max()) / 20.0)
        n = len(seg)
        out.append(dict(t0=round(float(t0), 3), t1=round(float(t1), 3), dur=round(float(t1 - t0), 3),
                        f_start=float(np.median(seg[:max(1, n // 5)])), f_end=float(np.median(seg[-max(1, n // 5):])),
                        f_med=float(np.median(seg)),
                        f_peak=float(np.percentile(seg, 95)), f_min=float(np.percentile(seg, 5)),
                        prom_db=float(np.median(pr)),
                        harm2=float(np.median(h2)), harm3=float(np.median(h3)),
                        peak_amp=float(np.max(10 ** (es / 20.0))),
                        contour=rs(seg), amp=rs(amp)))
    return out

def stat(vals):
    v = np.array(vals, dtype=float)
    return dict(median=round(float(np.median(v)), 3), min=round(float(v.min()), 3),
                max=round(float(v.max()), 3), n=int(len(v)))

def med_template(notes, key):
    arr = np.array([n[key] for n in notes])
    return [round(float(v), 4) for v in np.median(arr, axis=0)]

# ---------- contamination scan (v2 battery, same parameters as cardinal v2) ----------
def band_db(sr, x, lo, hi, win_s=0.25):
    if lo is None: xb = x
    else:
        sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
        xb = sig.sosfiltfilt(sos, x)
    w = int(win_s * sr); n = len(xb) // w
    rms = np.sqrt(np.mean(xb[:n * w].reshape(n, w) ** 2, axis=1))
    return 20 * np.log10(rms + 1e-9), win_s

def find_swells(db, win_s, rise_db=7.0, min_dur_s=1.5, merge_gap_s=2.0, smooth_s=1.0):
    k = max(1, int(smooth_s / win_s))
    sm = np.convolve(db, np.ones(k) / k, mode='same')
    base = float(np.median(sm))
    above = sm > base + rise_db
    spans = []; run = 0; start = 0
    for i, a in enumerate(above):
        if a and run == 0: start = i; run = 1
        elif a: run += 1
        elif run: spans.append([round(start * win_s, 2), round(i * win_s, 2), round(float(sm[start:i].max() - base), 1)]); run = 0
    if run: spans.append([round(start * win_s, 2), round(len(above) * win_s, 2), round(float(sm[start:].max() - base), 1)])
    spans = [s for s in spans if s[1] - s[0] >= min_dur_s]
    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] <= merge_gap_s:
            merged[-1][1] = s[1]; merged[-1][2] = max(merged[-1][2], s[2])
        else: merged.append(list(s))
    return base, merged

sr, x = load('/tmp/xc11638.wav')
lf_db, _w = band_db(sr, x, 40, 500); lf_base, lf_spans = find_swells(lf_db, _w)
bb_db, _w2 = band_db(sr, x, None, None); bb_base, bb_spans = find_swells(bb_db, _w2)
print(f'LF 40-500 Hz baseline {lf_base:.1f} dB, swells: {lf_spans}')
print(f'Broadband baseline {bb_base:.1f} dB, swells: {bb_spans}')

# ---------- hoot measurement ----------
edb = env_db_fn(sr, x, 150, 900)
t, pkf, prom, hr2, hr3 = track(sr, x)
# thresholds sit between the measured in-band floor (median -30 dB, p95 -25 dB)
# and hoot peaks (p95 -2 dB); the v1 cardinal thresholds (-24/-31) never close here
spansA = segment(edb, sr, -12.0, -17.0)
notesA = describe(sr, x, edb, spansA, t, pkf, prom, hr2, hr3)
spansB = segment(edb, sr, -16.0, -21.0)
candB = describe(sr, x, edb, spansB, t, pkf, prom, hr2, hr3)
extras = []
for c in candB:
    ov = any(min(c['t1'], a['t1']) - max(c['t0'], a['t0']) > 0.2 * c['dur'] for a in notesA)
    if not ov and c['prom_db'] >= 8: extras.append(c)
print('body hoots:', len(notesA), ' sensitive-pass extras:', [(c['t0'], c['dur']) for c in extras])
for i, n in enumerate(notesA):
    print(f"  hoot {i}: t={n['t0']:.2f}-{n['t1']:.2f} dur={n['dur']:.3f} fmed={n['f_med']:.0f} "
          f"fstart={n['f_start']:.0f} fend={n['f_end']:.0f} h2={n['harm2']:.3f} h3={n['harm3']:.3f} "
          f"peakAmp={n['peak_amp']:.3f} prom={n['prom_db']:.1f}")

allnotes = sorted(notesA + extras, key=lambda n: n['t0'])
# series split at gaps > 3 s
series = []; cur = [allnotes[0]]
for a, b in zip(allnotes, allnotes[1:]):
    if b['t0'] - a['t1'] > 3.0: series.append(cur); cur = [b]
    else: cur.append(b)
series.append(cur)
for si, s in enumerate(series):
    for pi, n in enumerate(s): n['position'] = pi + 1; n['series'] = si
    print(f"series {si}: {len(s)} hoots, t={s[0]['t0']:.2f}-{s[-1]['t1']:.2f}")

series_info = []
for i, s in enumerate(series):
    gaps_in = [round(s[j + 1]['t0'] - s[j]['t1'], 3) for j in range(len(s) - 1)]
    pause_after = round(series[i + 1][0]['t0'] - s[-1]['t1'], 3) if i + 1 < len(series) else None
    series_info.append(dict(index=i, t_start=s[0]['t0'], t_end=s[-1]['t1'], n_hoots=len(s),
                            hoot_dur_s=stat([n['dur'] for n in s]),
                            gap_in_s=stat(gaps_in) if gaps_in else None,
                            pause_after_s=pause_after))
    print(' series', i, series_info[-1])

# transitions within series: onset-to-onset period + gap, pooled and by position pair
trans = {}
for s in series:
    for a, c in zip(s, s[1:]):
        k = f"P{a['position']}>P{c['position']}"
        trans.setdefault(k, dict(period=[], gap=[]))
        trans[k]['period'].append(c['t0'] - a['t0']); trans[k]['gap'].append(c['t0'] - a['t1'])
trans_out = {}
for k, v in sorted(trans.items()):
    trans_out[k] = dict(period_s=stat(v['period']), gap_s=stat(v['gap']))
    print('transition', k, 'period', trans_out[k]['period_s'], 'gap', trans_out[k]['gap_s'])

# per-position stats across series
positions = {}
maxpos = max(n['position'] for n in allnotes)
for p in range(1, maxpos + 1):
    ns = [n for n in allnotes if n['position'] == p]
    positions[str(p)] = dict(position=p, n_instances=len(ns),
                             dur_s=stat([n['dur'] for n in ns]),
                             f_start_hz=stat([n['f_start'] for n in ns]),
                             f_med_hz=stat([n['f_med'] for n in ns]),
                             f_end_hz=stat([n['f_end'] for n in ns]),
                             f_peak_hz=stat([n['f_peak'] for n in ns]),
                             f_min_hz=stat([n['f_min'] for n in ns]),
                             harm2_ratio=stat([n['harm2'] for n in ns]),
                             harm3_ratio=stat([n['harm3'] for n in ns]),
                             peak_amp_rel=stat([n['peak_amp'] for n in ns]),
                             contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in ns]), axis=0)],
                             amp_template=med_template(ns, 'amp'))
    print(f"position {p}: n={len(ns)} dur={positions[str(p)]['dur_s']} fmed={positions[str(p)]['f_med_hz']}")

pauses = [s['pause_after_s'] for s in series_info if s['pause_after_s'] is not None]
hoot_spans = [[s[0]['t0'], s[-1]['t1']] for s in series]
def overlaps(span, spans):
    return any(span[0] < e and span[1] > b for b, e in spans)
lf_explained = all(overlaps(s, hoot_spans) for s in lf_spans)
bb_explained = all(overlaps(s, hoot_spans) for s in bb_spans)
print('LF spans all coincide with hoot series:', lf_explained, '| BB spans likewise:', bb_explained)

out = dict(
    species='Great Horned Owl (Bubo virginianus)',
    primary_reference=dict(file='XC11638.mp3', xeno_canto_id='XC11638',
                           recordist='Nathan Pieplow', location='Boulder, Colorado, US (1700 m)',
                           date='2007-03-16 05:30', license='CC BY-NC-ND 2.5', xc_grade='A',
                           background_species='none',
                           sample_rate_hz=sr, duration_s=round(len(x) / sr, 2),
                           supplied_by='Jimmy (xeno-canto.org/11638), 2026-11-11'),
    method=('Owl retune of the v1 pipeline: STFT (4096-pt Hann, 256 hop -> 10.8 Hz bins, 5.8 ms steps) dominant-peak '
            'pitch track in 150-900 Hz; hoot segmentation on the 150-900 Hz band Hilbert envelope (5 ms smoothing): '
            'body pass onset -12 dB / offset -17 dB rel. file peak, min off-time 60 ms, min hoot 120 ms; sensitive '
            'pass onset -16 / offset -21 dB, extras kept only if non-overlapping with body hoots and spectral-peak '
            'prominence >= 8 dB. The thresholds were set from this file\'s measured in-band floor (envelope median '
            '-30 dB, p95 -25 dB between series; hoot peaks p95 -2 dB) — the v1 cardinal thresholds (-24/-31 dB) sit '
            'inside this floor and never close, which is why the first pass fused the whole file into one span. '
            'Within each hoot, pitch/harmonic statistics use only frames whose band envelope is >= -22 dB, because '
            'the quiet floor is broad low-frequency noise wandering 200-290 Hz and unmasked edge frames track it '
            'instead of the hoot. Per hoot: f_start/f_end = median track over first/last 20% of kept frames, f_med = '
            'whole hoot, f_peak/f_min = 95th/5th percentile; harm2/harm3 = median frame ratio of the STFT magnitude '
            'at 2f0 / 3f0 to the fundamental; peak_amp_rel = max of the band envelope (linear, file peak-normalized). '
            'Contour and amplitude templates = per-hoot tracks resampled to 16 normalized points, median across '
            'instances of the position. Series = hoot groups split at gaps > 3.0 s; positions numbered from 1 '
            'within each series. Contamination scan (v2 battery): short-time RMS in 0.25 s windows for the 40-500 Hz '
            'band and full band; a swell = 1 s-smoothed level > file median + 7 dB sustained >= 1.5 s (spans < 2 s '
            'apart merged).'),
    contamination_scan=dict(
        low_freq_band_hz=[40, 500], lf_baseline_db=round(lf_base, 1), lf_swell_spans_s=lf_spans,
        broadband_baseline_db=round(bb_base, 1), broadband_swell_spans_s=bb_spans,
        spans_explained=('For this recording the owl IS a low-frequency source: every LF and broadband swell span '
                         'coincides with one of the two hoot series; the ~27 s between series stays at the flat '
                         'baseline in both bands, so there is no sustained rumble outside the bird itself.')
        if (lf_explained and bb_explained) else
        'WARNING: at least one swell span does not coincide with a hoot series — inspect before modeling.',
        verdict=('none found — no low-frequency rumble swell and no unexplained broadband swell anywhere outside '
                 'the two hoot series in the 35.0 s file; no span excluded, no hoot contaminated.')
        if (lf_explained and bb_explained) else 'SEE spans_explained — unresolved span present.',
        hoots_in_lf_spans=int(sum(1 for n in allnotes if any(n['t0'] < s[1] and n['t1'] > s[0] for s in lf_spans)))),
    body_hoot_count=len(notesA),
    sensitive_pass_extras=[dict(t0=c['t0'], dur=c['dur'], f_med_hz=round(c['f_med'])) for c in extras],
    hoots=[dict(t0=n['t0'], t1=n['t1'], dur=n['dur'], series=n['series'], position=n['position'],
                f_start_hz=round(n['f_start'], 1), f_med_hz=round(n['f_med'], 1), f_end_hz=round(n['f_end'], 1),
                harm2=round(n['harm2'], 4), harm3=round(n['harm3'], 4), peak_amp_rel=round(n['peak_amp'], 4))
           for n in allnotes],
    series=series_info,
    series_counts=stat([len(s) for s in series]),
    transitions=trans_out,
    series_pause_s=stat(pauses) if pauses else None,
    positions=positions)
json.dump(out, open('/home/hatch/workspace/bird-synth/analysis/great-horned-owl-measurements.json', 'w'), indent=1)
print('JSON written: analysis/great-horned-owl-measurements.json')
