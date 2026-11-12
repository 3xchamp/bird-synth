import numpy as np, json
from scipy.io import wavfile
from scipy import signal as sig

SRC = '/home/hatch/workspace/bird-synth/samples/eastern-towhee/XC1015083.wav'

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64); x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def band_env(sr, x, lo, hi, smooth_ms=3.0):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(smooth_ms / 1000 * sr)); env = np.convolve(env, np.ones(k) / k, mode='same')
    return env

def segment(env, sr, on, off, min_off_ms, min_dur_ms, absolute=False, peak=None):
    if absolute:
        on_l, off_l = on, off
    else:
        on_l, off_l = on, off  # env already in dB if caller passes dB
    notes = []; state = False; start = 0; below = 0
    min_off = int(min_off_ms / 1000 * sr)
    for i in range(len(env)):
        if not state:
            if env[i] > on_l: state = True; start = i; below = 0
        else:
            if env[i] < off_l:
                below += 1
                if below >= min_off:
                    end = i - below
                    if (end - start) / sr * 1000 >= min_dur_ms: notes.append((start / sr, end / sr))
                    state = False; below = 0
            else: below = 0
    if state and (len(env) - start) / sr * 1000 >= min_dur_ms:
        notes.append((start / sr, len(env) / sr))
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

def stat(vals):
    v = np.array(vals, dtype=float)
    return dict(median=round(float(np.median(v)), 3), min=round(float(v.min()), 3),
                max=round(float(v.max()), 3), n=int(len(v)))

def describe_note(sr, edb, t, pkf, hr, t0, t1):
    hop = t[1] - t[0]
    j0, j1 = int(t0 / hop), max(int(t1 / hop), int(t0 / hop) + 2)
    seg = pkf[j0:j1].copy()
    if len(seg) >= 5: seg = sig.medfilt(seg, 3)
    e0, e1 = int(t0 * sr), int(t1 * sr)
    es = edb[e0:e1]; amp = 10 ** ((es - es.max()) / 20.0)
    n = len(seg)
    return dict(t0=round(float(t0), 3), t1=round(float(t1), 3), dur=round(float(t1 - t0), 3),
                f_start=float(np.median(seg[:max(1, n // 5)])), f_end=float(np.median(seg[-max(1, n // 5):])),
                f_peak=float(np.percentile(seg, 95)), f_min=float(np.percentile(seg, 5)),
                harm2=float(np.median(hr[j0:j1])), peak_amp=float(np.max(10 ** (es / 20.0))),
                contour=rs(seg), amp=rs(amp))

# ---- contamination scan (cardinal method) ----
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
    base = float(np.median(sm)); above = sm > base + rise_db
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
print(f'LF baseline {lf_base:.1f} dB swells {lf_spans}')
print(f'BB baseline {bb_base:.1f} dB swells {bb_spans}')
# gap contrast: 0.25 s full-band windows
w = int(0.25 * sr); n = len(x) // w
rms = np.sqrt(np.mean(x[:n * w].reshape(n, w) ** 2, axis=1)); gdb = 20 * np.log10(rms + 1e-9)
gap_floor = round(float(np.percentile(gdb, 10)), 1); phrase_lvl = round(float(np.percentile(gdb, 90)), 1)
print(f'gap floor p10 {gap_floor} dB, phrase p90 {phrase_lvl} dB, min {gdb.min():.1f}, max {gdb.max():.1f}')

env = band_env(sr, x, 1500, 9000, 3.0); edb = 20 * np.log10(env + 1e-6)
t, pkf, prom, hr = track(sr, x)

# ---- songs ----
song_spans = segment(edb, sr, -28, -34, 400, 300)
songs = []
for (a, b) in song_spans:
    pk = float(edb[int(a * sr):int(b * sr)].max())
    songs.append(dict(t0=a, t1=b, peak_db=round(pk, 1)))
loud = [s for s in songs if s['peak_db'] > -15]
faint = [s for s in songs if s['peak_db'] <= -15]
print(f'songs total {len(songs)}, loud {len(loud)}, faint(distant, excluded) {len(faint)}')

env1 = band_env(sr, x, 1500, 9000, 1.0); edb1 = 20 * np.log10(env1 + 1e-6)
intro1, intro2, trills, trill_notes_all = [], [], [], []
song_info = []
for s in loud:
    a, b = s['t0'], s['t1']
    fine = segment(edb[int(a * sr):int((b + 0.35) * sr)], sr, -30, -36, 8, 12)
    fine = [(a + u, a + v) for (u, v) in fine if u < b - a + 0.1]
    # trill = last fine element with dur >= 0.30 s; intros = elements before it
    tri_idx = None
    for i, (u, v) in enumerate(fine):
        if v - u >= 0.30: tri_idx = i
    if tri_idx is None:
        print(f'  song {a:.2f}: NO trill blob; fine={[(round(u,2), round(v-u,2)) for u,v in fine]}'); continue
    intros = fine[:tri_idx]; tr = fine[tri_idx]
    notes_desc = [describe_note(sr, edb, t, pkf, hr, u, v) for (u, v) in intros]
    if len(notes_desc) >= 1: intro1.append(notes_desc[0])
    if len(notes_desc) >= 2: intro2.append(notes_desc[1])
    # trill notes: threshold segmentation on 1 ms env inside trill at 40% of trill peak (linear)
    ta, tb = tr
    seg_env = env1[int(ta * sr):int(tb * sr)]
    thr = 0.40 * seg_env.max()
    tn = segment(seg_env, sr, thr, thr * 0.8, 6, 8, absolute=True)
    tn = [(ta + u, ta + v) for (u, v) in tn]
    onsets = [u for (u, v) in tn]
    rate = (len(onsets) - 1) / (onsets[-1] - onsets[0]) if len(onsets) > 1 else 0
    tn_desc = [describe_note(sr, edb, t, pkf, hr, u, v) for (u, v) in tn]
    trill_notes_all += tn_desc
    trill_desc = describe_note(sr, edb, t, pkf, hr, ta, tb)
    trills.append(dict(desc=trill_desc, n_notes=len(tn), rate_per_s=round(float(rate), 2),
                       note_onsets=[round(u, 3) for u in onsets]))
    gap_it = round(tr[0] - intros[-1][1], 3) if intros else None
    gaps_intro = [round(intros[i + 1][0] - intros[i][1], 3) for i in range(len(intros) - 1)]
    song_info.append(dict(t_start=round(a, 3), n_intros=len(intros), intro_gaps_s=gaps_intro,
                          intro_to_trill_gap_s=gap_it, trill_dur_s=round(tr[1] - tr[0], 3),
                          trill_notes=len(tn), trill_rate_per_s=round(float(rate), 2),
                          song_dur_s=round(tr[1] - a, 3)))
    print(f'  song {a:.2f}: intros={len(intros)} gaps={gaps_intro} intro->trill={gap_it} trill dur={tr[1]-tr[0]:.3f} notes={len(tn)} rate={rate:.1f}/s')

trill_ends = [s['t_start'] + s['song_dur_s'] for s in song_info]
pauses = [round(song_info[i + 1]['t_start'] - trill_ends[i], 3) for i in range(len(song_info) - 1)]
print('inter-song pauses (loud songs):', pauses)

def type_block(notes):
    if not notes: return None
    return dict(n_instances=len(notes), dur_s=stat([n['dur'] for n in notes]),
                f_start_hz=stat([n['f_start'] for n in notes]), f_end_hz=stat([n['f_end'] for n in notes]),
                f_peak_hz=stat([n['f_peak'] for n in notes]), f_min_hz=stat([n['f_min'] for n in notes]),
                harm2_ratio=stat([n['harm2'] for n in notes]), peak_amp_rel=stat([n['peak_amp'] for n in notes]),
                contour_template_hz=[round(float(v), 1) for v in np.median(np.array([n['contour'] for n in notes]), axis=0)],
                amp_template=[round(float(v), 4) for v in np.median(np.array([n['amp'] for n in notes]), axis=0)])

types = {'I1': type_block(intro1), 'I2': type_block(intro2),
         'TRILL': type_block([tr['desc'] for tr in trills]),
         'TN': type_block(trill_notes_all)}
for k, v in types.items():
    if v: print(k, v['n_instances'], 'dur', v['dur_s'], 'f', v['f_start_hz']['median'], '->', v['f_end_hz']['median'], 'harm2', v['harm2_ratio']['median'])

out = dict(
    species='Eastern Towhee (Pipilo erythrophthalmus)',
    primary_reference=dict(file='XC1015083.wav', xeno_canto_id='XC1015083',
                           recordist='Stanislas Wroza', location='La Haute-Yamaska (near Shefford), Estrie, Québec, Canada',
                           date='2025-06-07', time='06:30', license='UNVERIFIED — recording page bot-gated (Anubis) from this host 2026-11-11; see SOURCES.md',
                           xc_grade='UNVERIFIED — recording page bot-gated (Anubis) from this host 2026-11-11; listing carries no background-species [also] marker',
                           sample_rate_hz=sr, duration_s=round(len(x) / sr, 2)),
    method=('STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in 1.3-9.5 kHz; song segmentation on the 1.5-9 kHz band '
            'Hilbert envelope (3 ms smoothing), onset -28 dB / offset -34 dB rel. file peak, min off-time 400 ms, min song 300 ms. '
            'Songs with band peak <= -15 dB are distant countersongs and are excluded from templates. Within a loud song, fine '
            'segmentation (onset -30 / offset -36 dB, min off 8 ms, min note 12 ms) splits intro notes from the trill; the trill is '
            'the fine element >= 0.30 s. Trill notes are segmented inside the trill on a 1 ms envelope at 40% of the trill peak '
            '(offset 32%), min note 8 ms, min off 6 ms; trill rate = (n-1)/(last onset - first onset). Note f_start/f_end = median '
            'track over first/last 20%; f_peak/f_min = 95th/5th percentile; contour/amp templates = per-note tracks resampled to '
            '16 points, median across instances. Contamination scan: 0.25 s window RMS, 60-500 Hz band and full band; a swell = '
            '1 s-smoothed level > file median + 7 dB sustained >= 1.5 s (spans < 2 s apart merged).'),
    contamination_scan=dict(low_freq_band_hz=[60, 500], lf_baseline_db=round(lf_base, 1), lf_swell_spans_s=lf_spans,
                            broadband_baseline_db=round(bb_base, 1), broadband_swell_spans_s=bb_spans,
                            gap_floor_p10_db=gap_floor, phrase_p90_db=phrase_lvl,
                            verdict='see SOURCES.md'),
    songs_total=len(songs), songs_loud=len(song_info), songs_faint_excluded=len(faint),
    faint_song_peaks_db=[s['peak_db'] for s in faint],
    song_info=song_info,
    intros_per_song=stat([s['n_intros'] for s in song_info]),
    intro_gap_s=stat([g for s in song_info for g in s['intro_gaps_s']]) if any(s['intro_gaps_s'] for s in song_info) else None,
    intro_to_trill_gap_s=stat([s['intro_to_trill_gap_s'] for s in song_info if s['intro_to_trill_gap_s'] is not None]),
    inter_song_pause_s=stat(pauses) if pauses else None,
    trill_notes_per_song=stat([s['trill_notes'] for s in song_info]),
    trill_rate_per_s=stat([s['trill_rate_per_s'] for s in song_info]),
    phrase_types=types)
json.dump(out, open('/home/hatch/workspace/bird-synth/analysis/eastern-towhee-measurements.json', 'w'), indent=1)
print('JSON written')
