import numpy as np, json
from scipy.io import wavfile
from scipy import signal as sig

CARD = '/home/hatch/workspace/bird-synth/samples/cardinal/'

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64)
    x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def envelope_db(sr, x, lo=1500, hi=9000, smooth_ms=3.0):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(smooth_ms/1000*sr))
    env = np.convolve(env, np.ones(k)/k, mode='same')
    return 20*np.log10(env + 1e-6)

def segment_notes(env_db, sr, on_db=-24.0, off_db=-31.0, min_off_ms=15, min_dur_ms=28):
    above = env_db > off_db
    # find crossings
    notes = []
    i = 0; n = len(env_db)
    min_off = int(min_off_ms/1000*sr)
    state = False; start = 0; below_count = 0
    for i in range(n):
        if not state:
            if env_db[i] > on_db:
                state = True; start = i; below_count = 0
        else:
            if env_db[i] < off_db:
                below_count += 1
                if below_count >= min_off:
                    end = i - below_count
                    if (end - start)/sr*1000 >= min_dur_ms:
                        notes.append((start/sr, end/sr))
                    state = False; below_count = 0
            else:
                below_count = 0
    if state and (n - start)/sr*1000 >= min_dur_ms:
        notes.append((start/sr, n/sr))
    return notes

def pitch_track(sr, x, lo=1300, hi=9500):
    f, t, Z = sig.stft(x, fs=sr, nperseg=1024, noverlap=1024-128, window='hann')
    mag = np.abs(Z)
    band = (f >= lo) & (f <= hi)
    fb = f[band]; mb = mag[band]
    pk = np.argmax(mb, axis=0)
    pkf = fb[pk]
    pkm = mb[pk, np.arange(mb.shape[1])]
    # harmonic ratio: energy near 2f vs f
    hr = np.zeros(mb.shape[1])
    fidx = {v: i for i, v in enumerate(fb)}
    for j in range(mb.shape[1]):
        f0 = pkf[j]
        i2 = np.argmin(np.abs(fb - 2*f0))
        if fb[i2] < hi:
            hr[j] = mb[i2, j] / (pkm[j] + 1e-12)
    return t, pkf, pkm, hr

def resample_template(vals, npts=16):
    if len(vals) < 2: return [float(vals[0])]*npts if len(vals) else [0.0]*npts
    xp = np.linspace(0, 1, len(vals)); xq = np.linspace(0, 1, npts)
    return np.interp(xq, xp, vals)

def analyze(path, lo=1500, hi=9000):
    sr, x = load(path)
    env_db = envelope_db(sr, x, lo, hi)
    notes_spans = segment_notes(env_db, sr)
    t, pkf, pkm, hr = pitch_track(sr, x)
    hop = t[1]-t[0]
    notes = []
    for (t0, t1) in notes_spans:
        j0, j1 = int(t0/hop), max(int(t1/hop), int(t0/hop)+2)
        seg = pkf[j0:j1].copy()
        if len(seg) >= 5: seg = sig.medfilt(seg, 3)
        e0, e1 = int(t0*sr), int(t1*sr)
        env_seg = env_db[e0:e1]
        amp_norm = env_seg - env_seg.max()
        amp_lin = 10**(amp_norm/20.0)
        n = len(seg)
        notes.append(dict(
            t0=round(float(t0), 3), t1=round(float(t1), 3), dur=round(float(t1-t0), 3),
            f_start=float(np.median(seg[:max(1, n//5)])),
            f_end=float(np.median(seg[-max(1, n//5):])),
            f_peak=float(np.percentile(seg, 95)), f_min=float(np.percentile(seg, 5)),
            contour=[float(v) for v in resample_template(seg)],
            amp=[float(v) for v in resample_template(amp_lin)],
            harm2=float(np.median(hr[j0:j1])) if j1 > j0 else 0.0))
    return sr, notes

sr, notes = analyze(CARD + 'XC1093538.wav')
print('XC1093538: sr', sr, 'notes', len(notes))
for n_ in notes:
    print("  t=%6.2f dur=%.3f f%5.0f->%5.0f peak%5.0f min%5.0f harm2=%.2f" % (n_['t0'], n_['dur'], n_['f_start'], n_['f_end'], n_['f_peak'], n_['f_min'], n_['harm2']))
np.save('/tmp/notes.npy', notes, allow_pickle=True)
