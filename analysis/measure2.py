import numpy as np, json, subprocess, os
from scipy.io import wavfile
from scipy import signal as sig

CARD = '/home/hatch/workspace/bird-synth/samples/cardinal/'

def load(path):
    sr, x = wavfile.read(path)
    if x.ndim > 1: x = x[:, 0]
    x = x.astype(np.float64); x /= (np.max(np.abs(x)) + 1e-12)
    return sr, x

def envelope_db(sr, x, lo, hi, smooth_ms=3.0):
    sos = sig.butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    xb = sig.sosfilt(sos, x)
    env = np.abs(sig.hilbert(xb))
    k = max(1, int(smooth_ms/1000*sr))
    env = np.convolve(env, np.ones(k)/k, mode='same')
    return 20*np.log10(env + 1e-6)

def segment_notes(env_db, sr, on_db, off_db, min_off_ms=15, min_dur_ms=28):
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

def analyze(path, lo, hi, on_db, off_db):
    sr, x = load(path)
    env_db = envelope_db(sr, x, lo, hi)
    spans = segment_notes(env_db, sr, on_db, off_db)
    f, t, Z = sig.stft(x, fs=sr, nperseg=1024, noverlap=1024-128, window='hann')
    mag = np.abs(Z); band = (f >= 1300) & (f <= 9500); fb = f[band]; mb = mag[band]
    pk = np.argmax(mb, axis=0); pkf = fb[pk]; pkm = mb[pk, np.arange(mb.shape[1])]
    med = np.median(mb, axis=0) + 1e-12
    prom = 20*np.log10(pkm/med)
    hop = t[1]-t[0]
    notes = []
    for (t0, t1) in spans:
        j0, j1 = int(t0/hop), max(int(t1/hop), int(t0/hop)+2)
        seg = pkf[j0:j1].copy()
        if len(seg) >= 5: seg = sig.medfilt(seg, 3)
        e0, e1 = int(t0*sr), int(t1*sr)
        env_seg = env_db[e0:e1]
        amp_lin = 10**((env_seg - env_seg.max())/20.0)
        def rs(vals, npts=16):
            if len(vals) < 2: return [float(vals[0])]*npts
            return [float(v) for v in np.interp(np.linspace(0,1,npts), np.linspace(0,1,len(vals)), vals)]
        n = len(seg)
        notes.append(dict(t0=round(float(t0),3), t1=round(float(t1),3), dur=round(float(t1-t0),3),
            f_start=float(np.median(seg[:max(1,n//5)])), f_end=float(np.median(seg[-max(1,n//5):])),
            f_peak=float(np.percentile(seg,95)), f_min=float(np.percentile(seg,5)),
            prom_db=float(np.median(prom[j0:j1])),
            contour=rs(seg), amp=rs(amp_lin)))
    return sr, notes

sr, notes = analyze(CARD+'XC1093538.wav', 1500, 9000, -30.0, -36.0)
notes = [n for n in notes if n['prom_db'] > 5]
print('XC1093538 sensitive run: %d notes' % len(notes))
for n_ in notes[:12]:
    print("  t=%6.2f dur=%.3f f%5.0f->%5.0f peak%5.0f prom=%.0f" % (n_['t0'], n_['dur'], n_['f_start'], n_['f_end'], n_['f_peak'], n_['prom_db']))
print('  ... last 6:')
for n_ in notes[-6:]:
    print("  t=%6.2f dur=%.3f f%5.0f->%5.0f peak%5.0f prom=%.0f" % (n_['t0'], n_['dur'], n_['f_start'], n_['f_end'], n_['f_peak'], n_['prom_db']))
import pickle
pickle.dump(notes, open('/tmp/notes109.pkl','wb'))

# XC10170 via ffmpeg decode
subprocess.run(['ffmpeg','-y','-v','error','-i',CARD+'XC10170.mp3','/tmp/xc10170.wav'], check=True)
sr2, notes2 = analyze('/tmp/xc10170.wav', 1300, 9000, -22.0, -30.0)
notes2 = [n for n in notes2 if n['prom_db'] > 5]
print('XC10170: sr', sr2, '%d notes' % len(notes2))
for n_ in notes2:
    print("  t=%6.2f dur=%.3f f%5.0f->%5.0f peak%5.0f min%5.0f prom=%.0f" % (n_['t0'], n_['dur'], n_['f_start'], n_['f_end'], n_['f_peak'], n_['f_min'], n_['prom_db']))
pickle.dump(notes2, open('/tmp/notes10170.pkl','wb'))
