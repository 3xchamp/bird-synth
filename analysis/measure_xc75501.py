import numpy as np, json, subprocess
from scipy.io import wavfile
from scipy import signal as sig
from collections import Counter

CARD = '/home/hatch/workspace/bird-synth/samples/cardinal/'
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', CARD + 'XC75501.ogg', '/tmp/xc75501.wav'], check=True)

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

# ---------- contamination scan (added for v2 at Jimmy's direction) ----------
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

sr, x = load('/tmp/xc75501.wav')
lf_base, lf_spans = band_db(sr, x, 60, 500)[0], None
lf_db, _w = band_db(sr, x, 60, 500); lf_base, lf_spans = find_swells(lf_db, _w)
bb_db, _w2 = band_db(sr, x, None, None); bb_base, bb_spans = find_swells(bb_db, _w2)
print(f'LF 60-500 Hz baseline {lf_base:.1f} dB, swells: {lf_spans}')
print(f'Broadband baseline {bb_base:.1f} dB, swells: {bb_spans}')

# ---------- note measurement (same pipeline as v1) ----------
edb = env_db_fn(sr, x, 1500, 9000)
t, pkf, prom, hr = track(sr, x)
spansA = segment(edb, sr, -24.0, -31.0)
notesA = describe(sr, x, edb, spansA, t, pkf, prom, hr)
spansB = segment(edb, sr, -32.0, -38.0)
candB = describe(sr, x, edb, spansB, t, pkf, prom, hr)
extras = []
for c in candB:
    ov = any(min(c['t1'], a['t1']) - max(c['t0'], a['t0']) > 0.2 * c['dur'] for a in notesA)
    if not ov and c['prom_db'] >= 10 and 0.03 <= c['dur'] <= 0.25: extras.append(c)
print('body notes:', len(notesA), ' sensitive-pass extras:', [(c['t0'], c['dur']) for c in extras])

def ntype(n):
    if n['f_end'] - n['f_start'] >= 600:            # rising whistle (upslur)
        return 'Ua' if n['dur'] < 0.44 else 'Ub'
    if n['f_start'] >= 3400 and n['f_end'] <= 2700 and (n['f_start'] - n['f_end']) >= 1700:  # steep high plunge
        return 'C'
    if n['f_start'] <= 2600 and n['f_end'] <= 1750 and n['f_peak'] <= 2600:
        return 'D'
    return '?'
for n in notesA: n['type'] = ntype(n)
print('types:', Counter(n['type'] for n in notesA))
for n in notesA:
    if n['type'] == '?': print('  UNCLASSIFIED:', n['t0'], n['dur'], round(n['f_start']), round(n['f_end']), round(n['f_peak']))

# bouts (gap > 1.0 s)
bouts = []; cur = [notesA[0]]
for a, b in zip(notesA, notesA[1:]):
    if b['t0'] - a['t1'] > 1.0: bouts.append(cur); cur = [b]
    else: cur.append(b)
bouts.append(cur)

def bout_form(seq):
    if all(s == 'C' for s in seq): return 'C'
    if seq[:2] == ['Ua', 'Ub'] and all(s == 'D' for s in seq[2:]): return 'A'
    if seq[:3] == ['Ua', 'Ub', 'D'] and all(s == 'C' for s in seq[3:]): return 'B'
    return 'other'
bout_info = []
for i, b in enumerate(bouts):
    seq = [n['type'] for n in b]
    gaps_in = [round(b[j + 1]['t0'] - b[j]['t1'], 3) for j in range(len(b) - 1)]
    pause_after = round(bouts[i + 1][0]['t0'] - b[-1]['t1'], 3) if i + 1 < len(bouts) else None
    bout_info.append(dict(index=i, t_start=b[0]['t0'], t_end=b[-1]['t1'], n_notes=len(b),
                          form=bout_form(seq), type_sequence=' '.join(seq),
                          note_dur_s=stat([n['dur'] for n in b]), gap_in_s=stat(gaps_in) if gaps_in else None,
                          pause_after_s=pause_after))
    print('bout', i, bout_info[-1]['form'], len(b), bout_info[-1]['type_sequence'], 'pause_after', pause_after)

# transitions: onset-to-onset period + offset-to-onset gap, per ordered pair
trans = {}
for b in bouts:
    for a, c in zip(b, b[1:]):
        k = a['type'] + '>' + c['type']
        trans.setdefault(k, dict(period=[], gap=[]))
        trans[k]['period'].append(c['t0'] - a['t0']); trans[k]['gap'].append(c['t0'] - a['t1'])
trans_out = {}
for k, v in sorted(trans.items()):
    trans_out[k] = dict(period_s=stat(v['period']), gap_s=stat(v['gap']))
    print('transition', k, 'period', trans_out[k]['period_s'], 'gap', trans_out[k]['gap_s'])

pauses = [b['pause_after_s'] for b in bout_info if b['pause_after_s'] is not None]
print('bout pauses', stat(pauses))

types = {}
for ty in ['Ua', 'Ub', 'D', 'C']:
    ns = [n for n in notesA if n['type'] == ty]
    if not ns: continue
    types[ty] = dict(n_instances=len(ns),
                     dur_s=stat([n['dur'] for n in ns]),
                     f_start_hz=stat([n['f_start'] for n in ns]), f_end_hz=stat([n['f_end'] for n in ns]),
                     f_peak_hz=stat([n['f_peak'] for n in ns]), f_min_hz=stat([n['f_min'] for n in ns]),
                     harm2_ratio=stat([n['harm2'] for n in ns]),
                     peak_amp_rel=stat([n['peak_amp'] for n in ns]),
                     contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in ns]), axis=0)],
                     amp_template=med_template(ns, 'amp'))
    print(ty, types[ty]['n_instances'], 'dur', types[ty]['dur_s'], 'f', types[ty]['f_start_hz']['median'],
          '->', types[ty]['f_end_hz']['median'], 'peakAmp', types[ty]['peak_amp_rel']['median'])

contamination_notes = int(sum(1 for n in notesA
                              if any(n['t0'] < s[1] and n['t1'] > s[0] for s in lf_spans)))
out = dict(
    species='Northern Cardinal (Cardinalis cardinalis)',
    primary_reference=dict(file='XC75501.ogg', xeno_canto_id='XC75501',
                           recordist='Jonathon Jongsma', location='Wood Lake, Richfield, Hennepin County, Minnesota, US',
                           date='2011-04-09', license='CC BY-SA 3.0', xc_grade='B',
                           sample_rate_hz=sr, duration_s=round(len(x) / sr, 2),
                           supplied_by='Jimmy (via Wikimedia Commons), 2026-11-11 — replaced XC1093538 at his ruling'),
    method=('Same pipeline as the v1 (XC1093538) measurement: STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in '
            '1.3-9.5 kHz; note segmentation on the 1.5-9 kHz band Hilbert envelope (3 ms smoothing): body pass onset '
            '-24 dB / offset -31 dB rel. file peak, min off-time 15 ms, min note 25 ms; sensitive pass onset -32 / '
            'offset -38 dB, extras kept only if non-overlapping with body notes and spectral-peak prominence >= 10 dB. '
            'Note f_start/f_end = median track over first/last 20% of the note; f_peak/f_min = 95th/5th percentile. '
            'peak_amp_rel = max of the 1.5-9 kHz band envelope (linear, signal peak-normalized) within the note. '
            'Contour and amplitude templates = per-note tracks resampled to 16 normalized points, median across '
            'instances of the type. Bouts = note groups split at gaps > 1.0 s. Type rules (this bird, by contour): '
            'U (upslur) = f_end - f_start >= 600 Hz, split by duration: Ua = dur < 0.44 s, Ub = dur >= 0.44 s; '
            'C (high chip) = f_start >= 3400 Hz, f_end <= 2700 Hz and f_start - f_end >= 1700 Hz (steep plunge; '
            'two of the 17 land near 2.5 kHz instead of 1.65 kHz — same gesture, shallower landing); '
            'D (downslur) = f_start <= 2600 Hz, f_end <= 1750 Hz, f_peak <= 2600 Hz. '
            'Contamination scan (new in v2): short-time RMS in 0.25 s windows for the 60-500 Hz band and full band; '
            'a swell = 1 s-smoothed level > file median + 7 dB sustained >= 1.5 s (spans < 2 s apart merged).'),
    contamination_scan=dict(
        low_freq_band_hz=[60, 500], lf_baseline_db=round(lf_base, 1), lf_swell_spans_s=lf_spans,
        broadband_baseline_db=round(bb_base, 1), broadband_swell_spans_s=bb_spans,
        broadband_spans_explained=('The broadband rises coincide with cardinal bouts 0-3 (0.4-3.5, 8.7-11.5, '
                                   '15.5-19.0, 24.1-26.5 s); through those same spans the 60-500 Hz band stays at its '
                                   'flat baseline (-52 to -56 dB/s), so the energy is the bird\'s own 1.5-9 kHz song, '
                                   'not vehicle/aircraft rumble.'),
        verdict='none found — no low-frequency rumble swell and no unexplained broadband swell anywhere in the '
                '35.2 s file; no span excluded, no note contaminated.',
        notes_in_lf_spans=contamination_notes),
    body_note_count=len(notesA),
    sensitive_pass_extras=[dict(t0=c['t0'], dur=c['dur'], f_start_hz=round(c['f_start']), f_end_hz=round(c['f_end']),
                                f_peak_hz=round(c['f_peak']), note='soft short note inside bout 3, between the two '
                                'upslurs (n=1) — recorded as an observation, not templated as a phrase type')
                           for c in extras],
    bouts=bout_info,
    transitions=trans_out,
    bout_pause_s=stat(pauses),
    phrase_types=types)
json.dump(out, open('/home/hatch/workspace/bird-synth/analysis/cardinal-measurements-xc75501.json', 'w'), indent=1)
print('JSON written: analysis/cardinal-measurements-xc75501.json')
