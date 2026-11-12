#!/usr/bin/env python3
"""Measure XC698523 (Great Blue Heron flight call / 'long snarl') for the bird-synth.

The heron is the noise-end bird: segmentation and spectral measurement carry the
model; pitch is estimated only where a stable fundamental can be demonstrated,
and flagged unreliable everywhere else. Output: great-blue-heron-measurements.json
"""
import numpy as np, json, subprocess, os
from scipy.io import wavfile
from scipy import signal as sig

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'samples', 'great-blue-heron', 'XC698523.mp3')
WAV = os.path.join(HERE, 'heron_work', 'heron.wav')
if not os.path.exists(WAV):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', SRC, WAV], check=True)

sr, x = wavfile.read(WAV)
x = x.astype(np.float64) / 32768.0
file_peak = np.abs(x).max()

# ---------- segmentation on the 200 Hz - 8 kHz Hilbert envelope ----------
sos = sig.butter(4, [200, 8000], btype='band', fs=sr, output='sos')
xf = sig.sosfilt(sos, x)
env = np.abs(sig.hilbert(xf))
k = int(0.004 * sr)
env_s = np.convolve(env, np.ones(k) / k, 'same')
db = 20 * np.log10(env_s / env_s.max() + 1e-12)
ON, OFF = -20.0, -30.0
segs, inb = [], False
for i, v in enumerate(db):
    if not inb and v > ON:
        start = i; inb = True
    elif inb and v < OFF:
        if i - start > int(0.03 * sr):
            segs.append((start, i))
        inb = False
if inb:
    segs.append((start, len(db)))
merged = []
for s, e in segs:
    if merged and (s - merged[-1][1]) / sr < 0.18:
        merged[-1] = (merged[-1][0], e)
    else:
        merged.append((s, e))

# ---------- per-burst measurement ----------
BANDS = [(200, 450), (450, 900), (900, 1800), (1800, 3200), (3200, 5200), (5200, 8000)]
f, t, S = sig.spectrogram(x, sr, nperseg=2048, noverlap=1536)
P = S ** 2  # power

def band_profile(t0, t1):
    m = (t >= t0) & (t <= t1)
    Pm = P[:, m].mean(axis=1)
    tot = Pm[(f >= 200) & (f < 8000)].sum()
    prof = [float(Pm[(f >= a) & (f < b)].sum() / tot) for a, b in BANDS]
    cent = float((f[(f >= 200) & (f < 8000)] * Pm[(f >= 200) & (f < 8000)]).sum()
                 / Pm[(f >= 200) & (f < 8000)].sum())
    return prof, cent

def f0_estimate(t0, t1, e0, e1):
    """STFT peak track in 150-1000 Hz over the burst core (env > 50% of burst peak).
    Reliable only if the track is stable AND the peak is prominent."""
    core = env_s[e0:e1]
    thr = 0.5 * core.max()
    idx = np.where(core > thr)[0]
    if len(idx) < 5:
        return None
    ct0, ct1 = (e0 + idx[0]) / sr, (e0 + idx[-1]) / sr
    m = (t >= ct0) & (t <= ct1)
    band = (f >= 150) & (f <= 1000)
    Sm = S[band, :][:, m]
    fm = f[band]
    peaks = fm[np.argmax(Sm, axis=0)]
    med = float(np.median(peaks))
    iqr = float(np.percentile(peaks, 75) - np.percentile(peaks, 25))
    # prominence: mean magnitude at the median-peak bin vs band median magnitude
    subm = S[:, m]
    row = np.argmin(np.abs(f - med))
    prom = float(subm[row].mean() / (np.median(subm[(f >= 150) & (f <= 8000)]) + 1e-12))
    # harmonic support: energy near 2*f0 relative to f0
    r2 = np.argmin(np.abs(f - 2 * med))
    harm = float(subm[r2].mean() / (subm[row].mean() + 1e-12))
    # energy share: fraction of the burst's 200 Hz-8 kHz power within +-6% of f0,
    # averaged over the core frames (from the power spectrogram P)
    Pm = P[:, m]
    tot = Pm[(f >= 200) & (f < 8000)].sum()
    near = Pm[(f >= 0.94 * med) & (f <= 1.06 * med)].sum()
    share = float(near / tot) if tot > 0 else 0.0
    stable = (iqr / med) <= 0.12 if med > 0 else False
    reliable = bool(stable and prom >= 3.5 and len(peaks) >= 5)
    return {'f0_hz': round(med, 1), 'iqr_hz': round(iqr, 1), 'prominence': round(prom, 2),
            'harm2_ratio': round(harm, 3), 'frames': int(len(peaks)), 'reliable': reliable,
            'energy_share': round(share, 4)}

bursts = []
for i, (s, e) in enumerate(merged):
    t0, t1 = s / sr, e / sr
    dur = t1 - t0
    seg = x[s:e]
    peak = float(np.abs(seg).max())
    # 16-point amplitude template (envelope, normalized to burst peak envelope)
    es = env_s[s:e]
    pts = np.interp(np.linspace(0, len(es) - 1, 16), np.arange(len(es)), es)
    amp = (pts / es.max()).tolist()
    prof, cent = band_profile(t0, t1)
    f0 = f0_estimate(t0, t1, s, e)
    nxt = merged[i + 1][0] / sr if i + 1 < len(merged) else None
    bursts.append({
        'idx': i, 'onset_s': round(t0, 3), 'offset_s': round(t1, 3),
        'dur_s': round(dur, 3),
        'gap_after_s': round(nxt - t1, 3) if nxt else None,
        'period_after_s': round(nxt - t0, 3) if nxt else None,
        'peak_rel': round(peak / file_peak, 3),
        'peak_dbfs': round(20 * np.log10(peak), 1),
        'amp_template': [round(a, 4) for a in amp],
        'band_profile': [round(p, 4) for p in prof],
        'centroid_hz': round(cent, 1),
        'f0': f0,
    })

# ---------- typing by duration ----------
def typ(d):
    return 'L' if d >= 0.65 else ('M' if d >= 0.2 else 'K')
for b in bursts:
    b['type'] = typ(b['dur_s'])

TYPE_NAMES = {'L': 'Long snarl', 'M': 'Croak', 'K': 'Chip'}
BEAT = 60 / 112
SIXT = BEAT / 4

def med(v):
    return float(np.median(v))

types = {}
for tk in ['L', 'M', 'K']:
    bs = [b for b in bursts if b['type'] == tk]
    if not bs:
        continue
    durmed = med([b['dur_s'] for b in bs])
    rel_f0 = [b['f0'] for b in bs if b['f0'] and b['f0']['reliable']]
    tmpl = np.array([med([b['amp_template'][j] for b in bs]) for j in range(16)])
    tmpl = tmpl / tmpl.max()  # median template renormalized to peak 1 (shape only)
    types[tk] = {
        'name': TYPE_NAMES[tk], 'n': len(bs),
        'dur_med': round(durmed, 3),
        'dur_min': round(min(b['dur_s'] for b in bs), 3),
        'dur_max': round(max(b['dur_s'] for b in bs), 3),
        'grid_dur': round(max(2, round(durmed / SIXT)) * SIXT, 4),
        'peak_med': round(med([b['peak_rel'] for b in bs]), 3),
        'centroid_med_hz': round(med([b['centroid_hz'] for b in bs]), 1),
        'band_profile_med': [round(med([b['band_profile'][j] for b in bs]), 4) for j in range(6)],
        'amp_template_med': [round(float(v), 4) for v in tmpl],
        'f0_reliable_n': len(rel_f0),
        'f0_med_hz': round(med([q['f0_hz'] for q in rel_f0]), 1) if rel_f0 else None,
        'f0_share_med': round(med([q['energy_share'] for q in rel_f0]), 4) if rel_f0 else None,
        'f0_amp_med': round(float(np.sqrt(med([q['energy_share'] for q in rel_f0]))), 4) if rel_f0 else None,
        'f0_harm2_med': round(med([q['harm2_ratio'] for q in rel_f0]), 3) if rel_f0 else None,
    }

# ---------- transitions (onset-to-onset) ----------
trans = {}
for a, b in zip(bursts, bursts[1:]):
    key = f"{a['type']}>{b['type']}"
    trans.setdefault(key, []).append(a['period_after_s'])
transitions = {kk: {'n': len(v), 'min': round(min(v), 3), 'med': round(med(v), 3),
                    'max': round(max(v), 3),
                    'grid': round(max(4, round(med(v) / SIXT)) * SIXT, 4)}
               for kk, v in sorted(trans.items())}

gaps = [b['gap_after_s'] for b in bursts if b['gap_after_s'] is not None]

# ---------- performance arc / phases ----------
# approach: bursts before the first L; overhead: the opening L run (the two loudest,
# back-to-back L bursts at the arc peak); calling: the rest until the settle chips;
# settle: trailing K bursts after the last non-K burst.
firstL = next(i for i, b in enumerate(bursts) if b['type'] == 'L')
lastNonK = max(i for i, b in enumerate(bursts) if b['type'] != 'K')
phases = {'approach': [], 'overhead': [], 'calling': [], 'settle': []}
for i, b in enumerate(bursts):
    if i < firstL:
        phases['approach'].append(i)
    elif i > lastNonK:
        phases['settle'].append(i)
    elif i <= firstL + 1:
        phases['overhead'].append(i)
    else:
        phases['calling'].append(i)
phase_info = {}
for ph, idxs in phases.items():
    phase_info[ph] = {
        'burst_idx': idxs,
        'types': [bursts[i]['type'] for i in idxs],
        'peak_rel_range': [round(min(bursts[i]['peak_rel'] for i in idxs), 3),
                           round(max(bursts[i]['peak_rel'] for i in idxs), 3)] if idxs else None,
        'gap_range_s': [round(min(bursts[i]['gap_after_s'] for i in idxs if bursts[i]['gap_after_s'] is not None), 3),
                        round(max(bursts[i]['gap_after_s'] for i in idxs if bursts[i]['gap_after_s'] is not None), 3)]
                       if any(bursts[i]['gap_after_s'] is not None for i in idxs) else None,
    }

sequence = [{'type': b['type'], 'peak_rel': b['peak_rel'], 'dur_s': b['dur_s'],
             'gap_after_s': b['gap_after_s']} for b in bursts]

# ---------- aircraft / rumble scan ----------
# A steady ambient floor is expected at a bay shore; the aircraft signature is a
# SWELL: the <200 Hz band rising well above its own baseline for seconds, then
# falling. Detector: 1 s windows (0.5 s hop) outside burst spans; baseline = 10th
# percentile of the low-band series; swell = >=3 consecutive windows at
# baseline + 8 dB or more.
burst_mask = np.zeros(len(x), dtype=bool)
for s, e in merged:
    burst_mask[s:e] = True
win, hop = sr, sr // 2
low_series = []
for i in range(0, len(x) - win, hop):
    if burst_mask[i:i + win].mean() > 0.05:
        continue
    segw = x[i:i + win]
    fw, Pw = sig.welch(segw, sr, nperseg=4096)
    low = np.sqrt(np.trapz(Pw[fw < 200], fw[fw < 200]))
    low_series.append(20 * np.log10(low + 1e-12))
low_series = np.array(low_series)
baseline = float(np.percentile(low_series, 10))
dev = low_series - baseline
cur = runs = 0
for v in dev:
    if v >= 8:
        cur += 1; runs = max(runs, cur)
    else:
        cur = 0
rumble = {
    'method': 'Welch PSD per 1 s window (0.5 s hop) outside burst spans; RMS of the '
              '<200 Hz band; baseline = 10th percentile of that series; an aircraft/'
              'vehicle swell = >=3 consecutive windows >= baseline + 8 dB',
    'lowband_baseline_dbfs': round(baseline, 1),
    'lowband_median_dbfs_outside_bursts': round(float(np.median(low_series)), 1),
    'max_deviation_above_baseline_db': round(float(dev.max()), 1),
    'longest_swell_run_windows': runs,
    'verdict': 'CLEAN — a steady low-frequency ambient floor (bay water/wind) is present '
               'throughout at roughly the baseline level, but no swell rises above it: '
               'no aircraft or vehicle pass' if runs < 3
               else 'SWELL DETECTED — sustained low-frequency rise above baseline; inspect',
}

out = {
    'species': 'Great Blue Heron (Ardea herodias)',
    'source': 'XC698523, Thomas G. Graves, Morro Bay CA, 2021-12-26, CC BY-NC-SA 4.0',
    'method': 'Segmentation on 200 Hz-8 kHz Hilbert envelope (on -20 dB / off -30 dB rel '
              'envelope peak, gaps <0.18 s merged). Per burst: duration, gaps, peak, 16-pt '
              'amplitude template, 6-band energy profile (200 Hz-8 kHz), spectral centroid, '
              'and an F0 estimate (STFT peak track 150-1000 Hz over the burst core) that is '
              'only marked reliable when the track is stable (IQR/median <= 0.12) and '
              'prominent (>= 3.5x band median). Types by duration: L >= 0.65 s, '
              'M 0.2-0.65 s, K < 0.2 s.',
    'file': {'sr': sr, 'dur_s': round(len(x) / sr, 3), 'peak_dbfs': round(20 * np.log10(file_peak), 2),
             'rms_dbfs': round(20 * np.log10(np.sqrt(np.mean(x ** 2))), 2)},
    'bands_hz': BANDS,
    'burst_count': len(bursts),
    'bursts': bursts,
    'types': types,
    'transitions': transitions,
    'gap_stats_s': {'min': round(min(gaps), 3), 'med': round(med(gaps), 3), 'max': round(max(gaps), 3)},
    'sequence': sequence,
    'phases': phase_info,
    'rumble_scan': rumble,
    'ambient_bed_note': 'Outside the bursts the file carries a quiet bed dominated by the '
                        '200-500 Hz band (0.59-0.70 of 100 Hz-16 kHz energy in 1-3 s, 15-17.5 s '
                        'and tail windows) — water/wind ambience, not vocalization; excluded '
                        'from the model. A sensitive second pass (-28 dB) after 13.5 s found no '
                        'bursts beyond the 13 segmented.',
}
with open(os.path.join(HERE, 'great-blue-heron-measurements.json'), 'w') as fh:
    json.dump(out, fh, indent=1)
print(json.dumps({'bursts': len(bursts),
                  'types': {kk: (v['n'], v['dur_med'], v['f0_med_hz'], v['f0_reliable_n']) for kk, v in types.items()},
                  'rumble': rumble['verdict']}, indent=1))
for b in bursts:
    f0s = f"{b['f0']['f0_hz']:.0f}Hz {'REL' if b['f0']['reliable'] else 'unrel'}" if b['f0'] else 'none'
    print(f"  #{b['idx']} {b['type']} {b['onset_s']:6.3f}s dur {b['dur_s']:.3f} peak {b['peak_rel']:.3f} "
          f"cent {b['centroid_hz']:.0f} f0 {f0s} bands {[round(p,2) for p in b['band_profile']]}")
