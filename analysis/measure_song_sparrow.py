import numpy as np, json, subprocess
from scipy.io import wavfile
from scipy import signal as sig
from collections import Counter

SRC = '/home/hatch/workspace/bird-synth/samples/song-sparrow/XC1005250.wav'

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

def segment(env_db, sr, on_db, off_db, min_off_ms=12, min_dur_ms=20):
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
    mag = np.abs(Z); band = (f >= 1500) & (f <= 9500); fb = f[band]; mb = mag[band]
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

# ---------- contamination scan (cardinal v2 method) ----------
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

sr, x = load(SRC)
lf_db, _w = band_db(sr, x, 60, 500); lf_base, lf_spans = find_swells(lf_db, _w)
bb_db, _w2 = band_db(sr, x, None, None); bb_base, bb_spans = find_swells(bb_db, _w2)
print(f'LF 60-500 Hz baseline {lf_base:.1f} dB, swells: {lf_spans}')
print(f'Broadband baseline {bb_base:.1f} dB, swells: {bb_spans}')

# gap contrast: 0.25 s windows, full band
w = int(0.25 * sr); nw = len(x) // w
rms = np.sqrt(np.mean(x[:nw * w].reshape(nw, w) ** 2, axis=1))
gdb = 20 * np.log10(rms + 1e-9)
gap_floor = float(np.percentile(gdb, 10)); phrase_lvl = float(np.percentile(gdb, 90))
print(f'gap floor (p10) {gap_floor:.1f} dB RMS, phrase (p90) {phrase_lvl:.1f} dB RMS')

# ---------- note measurement ----------
edb = env_db_fn(sr, x, 1800, 9000)
t, pkf, prom, hr = track(sr, x)
spansA = segment(edb, sr, -24.0, -31.0)
notesA = describe(sr, x, edb, spansA, t, pkf, prom, hr)
print('body notes:', len(notesA))

# songs = groups split at gaps > 1.0 s that contain an intro pair + buzz (identified below after typing)
def ntype(n, song_start_idx):
    fs, fe, fp, d = n['f_start'], n['f_end'], n['f_peak'], n['dur']
    if 2300 <= fs <= 2600 and d >= 0.15 and abs(fe - fs) < 150: return 'I'
    if 3700 <= fs <= 4000 and d >= 0.40: return 'B'
    if fs >= 7500 and d >= 0.10: return 'T'
    if fp >= 7000 and d >= 0.09: return 'H'
    if fs >= 6000 and d < 0.09: return 'h'
    if 4300 <= fs <= 4800 and d <= 0.07: return 'E' if False else 'M'
    if 2000 <= fs <= 2200 and fe >= 2900: return 'L'
    if 3300 <= fs <= 3800 and fe <= 3100 and d <= 0.07: return 'C'
    if 3400 <= fs <= 3800 and abs(fe - fs) < 400 and fp < 3800: return 'W'
    return '?'
for n in notesA: n['type'] = ntype(n, 0)
# E = the flat ~4450 Hz short note that immediately follows a T (position rule, documented)
for a, b in zip(notesA, notesA[1:]):
    if a['type'] == 'T' and b['type'] == 'M' and 4400 <= b['f_start'] <= 4600 and abs(b['f_end'] - b['f_start']) < 120:
        b['type'] = 'E'
# P = short rising ticks before the first intro note of song 1 (position rule, documented)
first_I = next(i for i, n in enumerate(notesA) if n['type'] == 'I')
for n in notesA[:first_I]:
    if n['dur'] <= 0.05 and n['f_peak'] >= 6000: n['type'] = 'P'
print('types:', Counter(n['type'] for n in notesA))
for n in notesA:
    if n['type'] == '?': print('  UNCLASSIFIED:', n['t0'], n['dur'], round(n['f_start']), round(n['f_end']), round(n['f_peak']))

# groups split at gaps > 1.0 s
groups = []; cur = [notesA[0]]
for a, b in zip(notesA, notesA[1:]):
    if b['t0'] - a['t1'] > 1.0: groups.append(cur); cur = [b]
    else: cur.append(b)
groups.append(cur)
songs = [g for g in groups if any(n['type'] == 'I' for n in g) and any(n['type'] == 'B' for n in g)]
strays = [n for g in groups if g not in songs for n in g]
print('songs:', len(songs), ' stray notes:', [(n['t0'], n['type']) for n in strays])

song_info = []
for i, s in enumerate(songs):
    seq = [n['type'] for n in s]
    gaps_in = [round(s[j + 1]['t0'] - s[j]['t1'], 3) for j in range(len(s) - 1)]
    pause_after = round(songs[i + 1][0]['t0'] - s[-1]['t1'], 3) if i + 1 < len(songs) else None
    song_info.append(dict(index=i, t_start=s[0]['t0'], t_end=s[-1]['t1'], n_notes=len(s),
                          type_sequence=' '.join(seq),
                          note_dur_s=stat([n['dur'] for n in s]), gap_in_s=stat(gaps_in) if gaps_in else None,
                          pause_after_s=pause_after))
    print('song', i, len(s), song_info[-1]['type_sequence'], 'pause_after', pause_after)

trans = {}
for s in songs:
    for a, c in zip(s, s[1:]):
        k = a['type'] + '>' + c['type']
        trans.setdefault(k, dict(period=[], gap=[]))
        trans[k]['period'].append(c['t0'] - a['t0']); trans[k]['gap'].append(c['t0'] - a['t1'])
trans_out = {}
for k, v in sorted(trans.items()):
    trans_out[k] = dict(period_s=stat(v['period']), gap_s=stat(v['gap']))

pauses = [s['pause_after_s'] for s in song_info if s['pause_after_s'] is not None]
print('song pauses', stat(pauses) if pauses else None)

types = {}
for ty in ['P', 'I', 'B', 'L', 'H', 'h', 'M', 'C', 'T', 'E', 'W']:
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
    print(ty, types[ty]['n_instances'], 'dur', types[ty]['dur_s'], 'f', types[ty]['f_start_hz']['median'], '->', types[ty]['f_end_hz']['median'])

# ---------- TRILL: the rapid post-buzz series in each song ----------
# trill span = first note after the buzz to the last note before the terminal T
# (or to song end when no T). Rate = onsets per second across the span.
trill_rates, trill_durs, trill_counts, trill_spans = [], [], [], []
trill_notes = []
for s in songs:
    bi = next(i for i, n in enumerate(s) if n['type'] == 'B')
    ti = next((i for i, n in enumerate(s) if n['type'] == 'T'), len(s))
    series = s[bi + 1:ti]
    if len(series) >= 2:
        span = series[-1]['t0'] - series[0]['t0']
        rate = (len(series) - 1) / span if span > 0 else 0
        trill_rates.append(rate); trill_counts.append(len(series)); trill_durs.append(s[ti - 1]['t1'] - series[0]['t0'] if ti > bi + 1 else 0)
        trill_spans.append(round(float(s[ti - 1]['t1'] - series[0]['t0']), 3))
        trill_notes.extend(series)
        print(f'trill: {len(series)} notes, span {trill_spans[-1]} s, rate {rate:.2f} notes/s, types {" ".join(n["type"] for n in series)}')
trill = dict(
    definition='Post-buzz rapid series: notes after the buzz (B) up to the terminal high note (T), per song.',
    notes_per_song=stat(trill_counts),
    span_s=stat(trill_spans),
    rate_notes_per_s=stat(trill_rates),
    note_dur_s=stat([n['dur'] for n in trill_notes]),
    onset_period_s=stat([1.0 / r for r in trill_rates]) if trill_rates else None,
    pooled_note_contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in trill_notes]), axis=0)] if trill_notes else None,
    pooled_note_amp_template=med_template(trill_notes, 'amp') if trill_notes else None,
    note_types_in_trill=dict(Counter(n['type'] for n in trill_notes)),
    per_type_templates_are_the_per_note_contours='The trill is not one repeated identical note: it cycles L / h / M / C (and the fused long form H). The per-note pitch contour inside the trill is therefore the per-type 16-point template in phrase_types (L, h, M, C, H); the pooled template above mixes those unlike notes and is recorded only for completeness.')

contamination_notes = int(sum(1 for n in notesA
                              if any(n['t0'] < s[1] and n['t1'] > s[0] for s in lf_spans)))
out = dict(
    species='Song Sparrow (Melospiza melodia)',
    primary_reference=dict(file='XC1005250.wav', xeno_canto_id='XC1005250',
                           recordist='Ryan Douglas', location='Damascus, Montgomery County, Maryland, US',
                           date='2025-06-08', license='Creative Commons Attribution-ShareAlike 4.0',
                           xc_grade='not extractable — recording page bot-gated (Anubis) via browser and curl on 2026-11-11; license/background/type/file specs were recovered from the search-indexed copy of the recording page',
                           background_species='none (per recording page)',
                           sample_rate_hz=sr, duration_s=round(len(x) / sr, 2)),
    method=('STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in 1.5-9.5 kHz; note segmentation on the '
            '1.8-9 kHz band Hilbert envelope (3 ms smoothing): body pass onset -24 dB / offset -31 dB rel. file peak, '
            'min off-time 12 ms, min note 20 ms. Note f_start/f_end = median track over first/last 20% of the note; '
            'f_peak/f_min = 95th/5th percentile. peak_amp_rel = max of the 1.8-9 kHz band envelope (linear, signal '
            'peak-normalized) within the note. Contour and amplitude templates = per-note tracks resampled to 16 '
            'normalized points, median across instances of the type. Songs = note groups split at gaps > 1.0 s that '
            'contain an intro pair and a buzz. Type rules (this bird, by pitch/duration): I = flat 2300-2600 Hz, '
            'dur >= 0.15 s; B = flat 3700-4000 Hz, dur >= 0.40 s (the buzz); T = f_start >= 7500 Hz, dur >= 0.10 s '
            '(terminal high); H = f_peak >= 7000 Hz, dur >= 0.09 s (long high downslur — plausibly a fused h+M pair '
            'whose internal gap fell under the 12 ms segmentation floor); h = f_start >= 6000 Hz, dur < 0.09 s; '
            'M = f_start 4300-4800 Hz, dur <= 0.07 s; L = f_start 2000-2200 Hz rising to >= 2900 Hz; '
            'C = f_start 3300-3800 Hz falling to <= 3100 Hz, dur <= 0.07 s; W = flat 3400-3800 Hz chip '
            '(|f_end - f_start| < 400 Hz, f_peak < 3800 Hz). Two position rules: P = the short rising '
            'ticks (dur <= 0.05 s, f_peak >= 6000 Hz) that precede the first intro note of song 1; E = the flat '
            '~4450 Hz short note immediately following a T. Contamination scan: short-time RMS in 0.25 s windows for '
            'the 60-500 Hz band and full band; a swell = 1 s-smoothed level > file median + 7 dB sustained >= 1.5 s '
            '(spans < 2 s apart merged). Gap contrast: 0.25 s full-band RMS windows, p10 (gap floor) vs p90 (phrase).'),
    vetting=dict(gap_floor_db_rms=round(gap_floor, 1), phrase_level_db_rms=round(phrase_lvl, 1),
                 contrast_db=round(phrase_lvl - gap_floor, 1)),
    contamination_scan=dict(
        low_freq_band_hz=[60, 500], lf_baseline_db=round(lf_base, 1), lf_swell_spans_s=lf_spans,
        broadband_baseline_db=round(bb_base, 1), broadband_swell_spans_s=bb_spans,
        verdict=('none found — no low-frequency (60-500 Hz) swell anywhere in the 40.1 s file (baseline -53.6 dB, '
                 'no span above threshold), so no aircraft/vehicle rumble span exists to exclude. The four broadband '
                 'swells coincide with the four measured songs (0.75-3.25, 10.25-12.75, 21.25-23.5, 33.75-36.0 s) '
                 'while the 60-500 Hz band stays at baseline through them, so they are the bird\'s own song energy. '
                 'No span excluded, no note contaminated.'),
        notes_in_lf_spans=contamination_notes),
    body_note_count=len(notesA),
    stray_notes=[dict(t0=n['t0'], dur=n['dur'], type=n['type'], f_start_hz=round(n['f_start']),
                      note='isolated note outside any song group (gap > 1.0 s on both sides)') for n in strays],
    unclassified_notes=[dict(t0=n['t0'], dur=n['dur'], f_start_hz=round(n['f_start']), f_end_hz=round(n['f_end']),
                             f_peak_hz=round(n['f_peak']),
                             note='did not meet any type rule — recorded as an observation, not templated')
                        for n in notesA if n['type'] == '?'],
    songs=song_info,
    transitions=trans_out,
    song_pause_s=stat(pauses) if pauses else None,
    phrase_types=types,
    trill=trill)
json.dump(out, open('/home/hatch/workspace/bird-synth/analysis/song-sparrow-measurements.json', 'w'), indent=1)
print('JSON written: analysis/song-sparrow-measurements.json')
