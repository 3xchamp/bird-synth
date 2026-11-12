import numpy as np, json, subprocess, os
from scipy.io import wavfile
from scipy import signal as sig
from collections import Counter

SRC = '/home/hatch/workspace/bird-synth/samples/hermit-thrush/XC1048898.wav'

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64); x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def env_db_fn(sr, x, lo, hi, smooth_ms=3):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(smooth_ms / 1000 * sr)); env = np.convolve(env, np.ones(k) / k, mode='same')
    return 20 * np.log10(env + 1e-6)

def segment(env_db, sr, on_db, off_db, min_off_ms=15, min_dur_ms=30):
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
    """Dominant-peak track in 1.3-9.5 kHz + harmonic ratios rel. to that peak
    (harm2, harm3) and a subharmonic check (energy at f/2)."""
    f, t, Z = sig.stft(x, fs=sr, nperseg=1024, noverlap=1024 - 128, window='hann')
    mag = np.abs(Z); band = (f >= 1300) & (f <= 9500); fb = f[band]; mb = mag[band]
    pk = np.argmax(mb, axis=0); pkf = fb[pk]; pkm = mb[pk, np.arange(mb.shape[1])]
    prom = 20 * np.log10(pkm / (np.median(mb, axis=0) + 1e-12))
    def ratio_at(mult):
        r = np.zeros(mb.shape[1])
        for j in range(mb.shape[1]):
            tgt = mult * pkf[j]
            if tgt > 9500: r[j] = 0.0; continue
            i2 = np.argmin(np.abs(fb - tgt))
            r[j] = mb[i2, j] / (pkm[j] + 1e-12)
        return r
    hr2 = ratio_at(2.0); hr3 = ratio_at(3.0); sub = ratio_at(0.5)
    return t, pkf, prom, hr2, hr3, sub

def rs(vals, npts=16):
    if len(vals) < 2: return [float(vals[0])] * npts
    return [float(v) for v in np.interp(np.linspace(0, 1, npts), np.linspace(0, 1, len(vals)), vals)]

def tremolo(sr, x, t0, t1):
    """AM shimmer within a note: FFT of the 1.5-9 kHz band envelope (1 ms
    smoothing), peak in 8-60 Hz; depth from envelope percentiles."""
    sos = sig.butter(4, [1500, 9000], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(0.001 * sr)); env = np.convolve(env, np.ones(k) / k, mode='same')
    e = env[int(t0 * sr):int(t1 * sr)]
    if len(e) < int(0.15 * sr): return None
    e = e - np.mean(e)
    w = np.hanning(len(e))
    sp = np.abs(np.fft.rfft(e * w)); fr = np.fft.rfftfreq(len(e), 1 / sr)
    band = (fr >= 8) & (fr <= 60)
    if not band.any(): return None
    j = np.argmax(sp[band]); rate = float(fr[band][j])
    raw = env[int(t0 * sr):int(t1 * sr)]
    p5, p95 = np.percentile(raw, 5), np.percentile(raw, 95)
    depth = float((p95 - p5) / (p95 + p5 + 1e-12))
    return dict(rate_hz=round(rate, 1), depth_index=round(depth, 3),
                peak_to_mean_db=round(float(20 * np.log10(sp[band][j] / (np.mean(sp[band]) + 1e-12))), 1))

def describe(sr, x, env_db, spans, t, pkf, prom, hr2, hr3, sub, src_pass):
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
                        f_med=float(np.median(seg)),
                        f_peak=float(np.percentile(seg, 95)), f_min=float(np.percentile(seg, 5)),
                        prom_db=float(np.median(prom[j0:j1])),
                        harm2=float(np.median(hr2[j0:j1])), harm3=float(np.median(hr3[j0:j1])),
                        subharm=float(np.median(sub[j0:j1])),
                        peak_amp=float(np.max(10 ** (es / 20.0))),
                        contour=rs(seg), amp=rs(amp), pass_=src_pass))
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

w = int(0.25 * sr); nw = len(x) // w
rms = np.sqrt(np.mean(x[:nw * w].reshape(nw, w) ** 2, axis=1))
gdb = 20 * np.log10(rms + 1e-9)
gap_floor = float(np.percentile(gdb, 10)); phrase_lvl = float(np.percentile(gdb, 90))
print(f'gap floor (p10) {gap_floor:.1f} dB RMS, phrase (p90) {phrase_lvl:.1f} dB RMS')

# ---------- note measurement: body pass + sensitive pass (cardinal method) ----------
edb = env_db_fn(sr, x, 1500, 9000)
t, pkf, prom, hr2, hr3, sub = track(sr, x)
spansA = segment(edb, sr, -26.0, -33.0)
notesA = describe(sr, x, edb, spansA, t, pkf, prom, hr2, hr3, sub, 'body')
print('body notes:', len(notesA))
spansB = segment(edb, sr, -38.0, -45.0, min_off_ms=20, min_dur_ms=40)
newB = [s for s in spansB if not any(s[0] < a[1] and s[1] > a[0] for a in spansA)]
notesB = [n for n in describe(sr, x, edb, newB, t, pkf, prom, hr2, hr3, sub, 'sensitive')
          if n['prom_db'] >= 8.0]
print('sensitive-pass additions (prom >= 8 dB):', len(notesB),
      [(n['t0'], n['dur'], round(n['f_med'])) for n in notesB])

notes = sorted(notesA + notesB, key=lambda n: n['t0'])
print('total notes:', len(notes))
for n in notes:
    print(f"  {n['t0']:6.2f}-{n['t1']:6.2f} dur {n['dur']:.3f} f {n['f_start']:6.0f}->{n['f_end']:6.0f} "
          f"med {n['f_med']:6.0f} pk {n['f_peak']:6.0f} h2 {n['harm2']:.3f} h3 {n['harm3']:.3f} "
          f"sub {n['subharm']:.2f} prom {n['prom_db']:.0f} amp {n['peak_amp']:.3f} [{n['pass_']}]")

# ---------- songs: groups split at gaps > 1.2 s ----------
groups = []; cur = [notes[0]]
for a, b in zip(notes, notes[1:]):
    if b['t0'] - a['t1'] > 1.2: groups.append(cur); cur = [b]
    else: cur.append(b)
groups.append(cur)
print('song groups (gap > 1.2 s):', len(groups))
for i, g in enumerate(groups):
    print(f'  song {i}: {g[0]["t0"]:.2f}-{g[-1]["t1"]:.2f}, {len(g)} notes, '
          f'base(med of f_med) {np.median([n["f_med"] for n in g]):.0f} Hz')

# ---------- tremolo on sustained notes ----------
print('tremolo (notes dur >= 0.25 s):')
for n in notes:
    tr = tremolo(sr, x, n['t0'], n['t1']) if n['dur'] >= 0.25 else None
    n['tremolo'] = tr
    if tr: print(f"  note @{n['t0']:.2f} dur {n['dur']:.2f}: {tr}")

# ---------- typing (contour x duration rules, stated in the JSON method) ----------
def ntype(n, is_first):
    d = n['dur']; rise = (n['f_end'] - n['f_start']) / n['f_start']
    if is_first and d >= 0.15 and abs(rise) < 0.03: return 'W'   # flat lead whistle
    if d < 0.15:
        if d < 0.07: return 'C'
        if rise >= 0.08: return 'u'
        if rise <= -0.08: return 'd'
        return 'C'
    if rise >= 0.10: return 'U'
    if rise <= -0.15: return 'D'
    return 'S'
for g in groups:
    for i, n in enumerate(g):
        n['type'] = ntype(n, i == 0)
frag = [n for n in notes if n['pass_'] == 'sensitive' and n['t0'] < 0.3]
for n in frag: n['type'] = 'x'   # 0.16 s fragment: unreliable contour, observation only
for n in notes:
    if 'type' not in n: n['type'] = '?'
print('types:', Counter(n['type'] for n in notes))

TYPE_NAMES = {'W': 'Lead whistle', 'S': 'Sustained flute', 'U': 'Up-slur flute',
              'D': 'Down-slur flute', 'C': 'Chip', 'u': 'Short up-chirp', 'd': 'Short down-chirp'}
TYPE_VOICE = {'W': 1, 'S': 0, 'U': 1, 'D': 0, 'C': 1, 'u': 1, 'd': 0}  # design: high types right

def grid_dur(d):  # nearest 32nd-note multiple at 112 BPM (0.067 s), floor 1 step
    step = (60 / 112) / 8
    return round(max(step, round(d / step) * step), 3)
def grid_period(p):  # same grid, floor 2 steps
    step = (60 / 112) / 8
    return round(max(2 * step, round(p / step) * step), 3)

types = {}
for ty in ['W', 'S', 'U', 'D', 'C', 'u', 'd']:
    ns = [n for n in notes if n['type'] == ty]
    if not ns: continue
    trs = [n['tremolo'] for n in ns if n.get('tremolo')]
    types[ty] = dict(name=TYPE_NAMES[ty], n_instances=len(ns),
                     dur_s=stat([n['dur'] for n in ns]),
                     f_start_hz=stat([n['f_start'] for n in ns]), f_end_hz=stat([n['f_end'] for n in ns]),
                     f_med_hz=stat([n['f_med'] for n in ns]),
                     f_peak_hz=stat([n['f_peak'] for n in ns]), f_min_hz=stat([n['f_min'] for n in ns]),
                     harm2_ratio=stat([n['harm2'] for n in ns]), harm3_ratio=stat([n['harm3'] for n in ns]),
                     peak_amp_rel=stat([n['peak_amp'] for n in ns]),
                     contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in ns]), axis=0)],
                     amp_template=med_template(ns, 'amp'),
                     tremolo=(dict(rate_hz=stat([t['rate_hz'] for t in trs]),
                                   depth_index=stat([t['depth_index'] for t in trs]),
                                   n_measured=len(trs)) if trs else None),
                     voice=TYPE_VOICE[ty], grid_dur_s=grid_dur(stat([n['dur'] for n in ns])['median']))
    print(ty, types[ty]['n_instances'], 'dur', types[ty]['dur_s']['median'],
          'f', round(types[ty]['f_start_hz']['median']), '->', round(types[ty]['f_end_hz']['median']),
          'h2', types[ty]['harm2_ratio']['median'], 'h3', types[ty]['harm3_ratio']['median'],
          'trem', types[ty]['tremolo']['rate_hz']['median'] if types[ty]['tremolo'] else None)

# ---------- songs, ladder, transitions ----------
song_info = []; ladder = []
for i, g in enumerate(groups):
    seq = [n['type'] for n in g]
    sust = [n for n in g if n['dur'] >= 0.25 and n['type'] != 'x']
    base = float(np.median([n['f_med'] for n in sust])) if sust else float(np.median([n['f_med'] for n in g]))
    longest = max(g, key=lambda n: n['dur'])
    wnote = g[0] if g[0]['type'] == 'W' else None
    pause_after = round(groups[i + 1][0]['t0'] - g[-1]['t1'], 3) if i + 1 < len(groups) else None
    song_info.append(dict(index=i, t_start=g[0]['t0'], t_end=g[-1]['t1'], n_notes=len(g),
                          type_sequence=' '.join(seq),
                          base_freq_hz=round(base, 1),
                          intro_freq_hz=round(wnote['f_med'], 1) if wnote else None,
                          longest_note_freq_hz=round(longest['f_med'], 1),
                          freq_span_hz=[round(min(n['f_min'] for n in g), 1), round(max(n['f_peak'] for n in g), 1)],
                          form=[dict(type=n['type'], f_med_hz=round(n['f_med'], 1)) for n in g if n['type'] != 'x'],
                          pause_after_s=pause_after))
    ladder.append(round(base, 1))
    print(f'song {i}: base {base:.0f} Hz, intro {song_info[-1]["intro_freq_hz"]}, '
          f'seq {song_info[-1]["type_sequence"]}, pause_after {pause_after}')
base_med = float(np.median(ladder))
ladder_out = [dict(song=i, base_freq_hz=b, ratio_to_median=round(b / base_med, 4),
                   semitones_from_median=round(12 * np.log2(b / base_med), 2))
              for i, b in enumerate(ladder)]
print('ladder (Hz):', ladder)
print('ladder ratios:', [l['ratio_to_median'] for l in ladder_out])

trans = {}
for g in groups:
    for a, c in zip(g, g[1:]):
        if a['type'] == 'x' or c['type'] == 'x': continue
        k = a['type'] + '>' + c['type']
        trans.setdefault(k, dict(period=[], gap=[]))
        trans[k]['period'].append(c['t0'] - a['t0']); trans[k]['gap'].append(c['t0'] - a['t1'])
trans_out = {}
for k, v in sorted(trans.items()):
    ps = stat(v['period'])
    trans_out[k] = dict(period_s=ps, gap_s=stat(v['gap']), grid_period_s=grid_period(ps['median']))

pauses = [s['pause_after_s'] for s in song_info if s['pause_after_s'] is not None]
pause_stat = stat(pauses)
grid_pause = round(max(1, round(pause_stat['median'] / (60 / 112))) * (60 / 112), 3)

trem_all = [n['tremolo'] for n in notes if n.get('tremolo')]
tremolo_out = dict(present=True,
                   measured_on_notes=len(trem_all),
                   rate_hz=stat([t['rate_hz'] for t in trem_all]),
                   depth_index=stat([t['depth_index'] for t in trem_all]),
                   note=('Every sustained note (dur >= 0.25 s, n=18) carries periodic amplitude '
                         'modulation: FFT of the 1.5-9 kHz band envelope peaks at 8-22 Hz '
                         '(median ~11 Hz) with peak-to-mean spectral prominence 6-12 dB, and the '
                         'envelope percentile depth index (p95-p5)/(p95+p5) is 0.59-0.93 — the '
                         'phrase notes are strongly pulsed/shimmering, not steady tones. The page '
                         'renders this as a gain LFO per note at the per-type median rate; depth in '
                         'the page is a design scaling of this index (see BUILD-hermit-thrush.md).'))

contamination_notes = int(sum(1 for n in notes
                              if any(n['t0'] < s[1] and n['t1'] > s[0] for s in lf_spans)))
out = dict(
    species='Hermit Thrush (Catharus guttatus)',
    primary_reference=dict(file='XC1048898.mp3', xeno_canto_id='XC1048898',
                           recordist='AUDEVARD Aurélien', location='Homer, Kenai Peninsula, Alaska, US',
                           date='2022-06-20', license='Creative Commons Attribution-NonCommercial-ShareAlike 4.0',
                           xc_grade='A', background_species='none (per recording page)',
                           sample_rate_hz=sr, duration_s=round(len(x) / sr, 2),
                           decoded_wav='XC1048898.wav (48 kHz mono decode of the MP3, same folder)'),
    method=('STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in 1.3-9.5 kHz; note segmentation on the '
            '1.5-9 kHz band Hilbert envelope (3 ms smoothing): body pass onset -26 dB / offset -33 dB rel. file '
            'peak (min off-time 15 ms, min note 30 ms), plus a sensitive pass (onset -38 / offset -45 dB, min '
            'off 20 ms, min note 40 ms) whose additions were kept only with median pitch prominence >= 8 dB. '
            'Note f_start/f_end = median track over first/last 20%; f_med = whole-note median; f_peak/f_min = '
            '95th/5th percentile. harm2/harm3 = median ratio of STFT magnitude at 2x/3x the tracked peak to the '
            'peak itself; subharm = same at f/2. peak_amp_rel = max of the band envelope (linear, signal '
            'peak-normalized) within the note. Templates = per-note tracks resampled to 16 normalized points, '
            'median across instances. Songs = note groups split at gaps > 1.2 s. Song base frequency = median '
            'f_med of the song\'s sustained notes (dur >= 0.25 s). Type rules (this bird, by duration/contour): '
            'W = song-initial note, dur >= 0.15 s, |f_end-f_start|/f_start < 3% (flat lead whistle); sustained '
            'notes (dur >= 0.15 s): rise >= 10% -> U, fall >= 15% -> D, else S; short notes (dur < 0.15 s): '
            'dur < 0.07 s -> C, rise >= 8% -> u, fall >= 8% -> d, else C. The one sensitive-pass fragment at '
            '0.16 s (unreliable contour, amp 0.014) is typed x and NOT templated. Tremolo: per sustained note, '
            'FFT of the 1.5-9 kHz band envelope (1 ms smoothing) — peak rate in 8-60 Hz and a percentile depth '
            'index. Contamination scan: short-time RMS in 0.25 s windows for the 60-500 Hz band and full band; '
            'a swell = 1 s-smoothed level > file median + 7 dB sustained >= 1.5 s (spans < 2 s apart merged). '
            'Gap contrast: 0.25 s full-band RMS windows, p10 (gap floor) vs p90 (phrase). Grid values (durations, '
            'transition periods, song pause) are design choices for the electronic end of the morph: nearest '
            '32nd-note multiple at 112 BPM (0.067 s) with floors of 1 step (durations) / 2 steps (periods); '
            'song pause to the nearest beat.'),
    vetting=dict(gap_floor_db_rms=round(gap_floor, 1), phrase_level_db_rms=round(phrase_lvl, 1),
                 contrast_db=round(phrase_lvl - gap_floor, 1),
                 note='SOURCES.md vetting (Mordecai, eye + 0.25 s windows on the MP3) measured gaps at '
                      '-51.6 dB RMS vs phrase peaks -16.4 dB; this pipeline\'s p10/p90 percentiles over the '
                      'decoded WAV are the values above (different statistic, same conclusion: ~25-35 dB '
                      'phrase-to-floor separation on a near-silent floor).'),
    contamination_scan=dict(
        low_freq_band_hz=[60, 500], lf_baseline_db=round(lf_base, 1), lf_swell_spans_s=lf_spans,
        broadband_baseline_db=round(bb_base, 1), broadband_swell_spans_s=bb_spans,
        verdict=('none found — no low-frequency (60-500 Hz) swell anywhere in the 41.9 s file (baseline '
                 '-48.0 dB, zero spans above threshold), so no aircraft/vehicle rumble span exists to exclude. '
                 'The five broadband swells coincide with song clusters (0.75-2.25, 4.75-7.0, 26.25-29.0, '
                 '34.25-35.75, 38.75-40.5 s) while the 60-500 Hz band stays at baseline through them — the '
                 'bird\'s own song energy (the three quieter songs at 11, 17 and 23.8 s do not cross the '
                 '+7 dB broadband threshold). No span excluded, no note contaminated. Faint low-frequency '
                 'wisps visible in a 0.25 s profile at ~21.5, 29.6, 31.3, 32.3, 36.5, 37.5 s are spectrally '
                 'dominated by 0.8-1.4 kHz content (mic/wind floor wobble), never cross the swell threshold, '
                 'and produced no pitch-prominent segments.'),
        notes_in_lf_spans=contamination_notes),
    body_note_count=len(notes),
    templated_note_count=int(sum(1 for n in notes if n['type'] != 'x')),
    song_count=len(groups),
    song_count_note=('SOURCES.md\'s spectrogram count was nine phrase clusters; the stated segmentation '
                     'resolves eight song groups (gap rule > 1.2 s). The difference is song 0: its quiet '
                     'intro complex (~0.3-1.05 s, 15-20 dB below the phrase, fragmented at measurement '
                     'thresholds) reads as a separate cluster on a spectrogram but belongs to song 0 by the '
                     'gap rule, and the 23.8 s / 26.1 s songs are separated by a real 1.39 s pause. The '
                     'generator uses the eight measured forms.'),
    faint_material=[dict(t0=0.16, t1=0.29,
                         note='sensitive-pass fragment opening song 0; contour unreliable (track jumps '
                              '1.4-6.2 kHz), amp 0.014. Part of a quiet intro complex (~0.3-1.05 s) that sits '
                              '15-20 dB below the phrase and fragments at segmentation thresholds. Recorded '
                              'as an observation; NOT templated, NOT in any form.'),
                    dict(t_approx=25.4, note='faint wisp ~25.3-25.9 s (~3 kHz, ~10 dB above floor in 50 ms '
                         'maxima) before song 5; produced no pitch-prominent segment. Not templated.')],
    songs=song_info,
    pitch_ladder=dict(definition='Per-song base frequency (median f_med of sustained notes), in performance '
                                 'order, with ratio/semitone distance to the median base. Each song sits at its '
                                 'own pitch level; successive levels are unrelated by any staircase rule in '
                                 'this performance (ratios range widely). The page generator replays the '
                                 'measured song forms with each note transposed by its own measured '
                                 'f_med / type-template-base ratio, so the ladder is reproduced exactly.',
                      median_base_freq_hz=round(base_med, 1), levels=ladder_out),
    transitions=trans_out,
    song_pause_s=pause_stat, grid_song_pause_s=grid_pause,
    phrase_types=types,
    tremolo=tremolo_out,
    all_notes=[dict(t0=n['t0'], t1=n['t1'], type=n['type'], f_med_hz=round(n['f_med'], 1)) for n in notes])
json.dump(out, open('/home/hatch/workspace/bird-synth/analysis/hermit-thrush-measurements.json', 'w'), indent=1)
print('JSON written: analysis/hermit-thrush-measurements.json')

