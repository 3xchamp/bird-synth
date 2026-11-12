import numpy as np
from scipy.io import wavfile
from scipy import signal as sig

sr, x = wavfile.read('/home/hatch/workspace/bird-synth/samples/cardinal/XC1093538.wav')
print('sr', sr, 'dtype', x.dtype, 'shape', x.shape)
if x.ndim > 1: x = x[:,0]
x = x.astype(np.float64)
x /= (np.max(np.abs(x)) + 1e-12)
print('dur s', len(x)/sr)

f, t, Z = sig.stft(x, fs=sr, nperseg=1024, noverlap=1024-128, window='hann')
mag = np.abs(Z)
band = (f >= 1500) & (f <= 9000)
fb = f[band]; mb = mag[band]
energy = mb.sum(axis=0)
pk_idx = np.argmax(mb, axis=0)
pk_freq = fb[pk_idx]
pk_mag = mb[pk_idx, np.arange(mb.shape[1])]
# peak prominence: peak mag relative to band median mag
band_med = np.median(mb, axis=0) + 1e-12
prom_db = 20*np.log10(pk_mag/band_med)
e_db = 20*np.log10(energy/ (np.percentile(energy, 99.5)+1e-12))
print('energy dB percentiles: 50%%=%.1f 90%%=%.1f 99%%=%.1f' % (np.percentile(e_db,50), np.percentile(e_db,90), np.percentile(e_db,99)))
print('prominence dB at loud frames: median of top decile = %.1f' % np.median(prom_db[e_db > -15]))

voiced = (e_db > -26) & (prom_db > 8)
# clean: remove tiny runs, merge small gaps
hop_s = t[1]-t[0]
def runs(mask):
    idx = np.flatnonzero(np.diff(np.concatenate(([0], mask.view(np.int8), [0]))))
    return list(zip(idx[::2], idx[1::2]))
rr = runs(voiced)
print('raw runs:', len(rr))
min_len = int(0.025/hop_s); merge_gap = int(0.045/hop_s)
rr = [(a,b) for a,b in rr if b-a >= min_len]
merged = []
for a,b in rr:
    if merged and a - merged[-1][1] <= merge_gap:
        merged[-1] = (merged[-1][0], b)
    else:
        merged.append((a,b))
print('notes after clean:', len(merged))
notes = []
for a,b in merged:
    seg_f = pk_freq[a:b]
    seg_f = sig.medfilt(seg_f, 5) if b-a >= 5 else seg_f
    n = len(seg_f)
    notes.append(dict(t0=float(t[a]), t1=float(t[b-1]), dur=float(t[b-1]-t[a]),
                      f_start=float(np.median(seg_f[:max(1,n//5)])),
                      f_end=float(np.median(seg_f[-max(1,n//5):])),
                      f_peak=float(np.percentile(seg_f, 95)),
                      f_min=float(np.percentile(seg_f, 5))))
gaps = [notes[i+1]['t0']-notes[i]['t1'] for i in range(len(notes)-1)]
print('gaps: median %.3f  max %.2f' % (np.median(gaps), max(gaps)))
# bouts: split at gap > 1.0 s
bouts = [[0]]
for i,g in enumerate(gaps):
    if g > 1.0: bouts.append([i+1])
    else: bouts[-1].append(i+1)
print('bouts:', [(len(b), round(notes[b[0]]['t0'],2), round(notes[b[-1]]['t1'],2)) for b in bouts])
for bi, b in enumerate(bouts):
    ns = [notes[i] for i in b]
    print(f"--- bout {bi}: {len(ns)} notes, {ns[0]['t0']:.2f}-{ns[-1]['t1']:.2f}s")
    for n_ in ns[:14]:
        print("   t=%6.2f dur=%.3f f0=%5.0f fend=%5.0f fpeak=%5.0f fmin=%5.0f" % (n_['t0'], n_['dur'], n_['f_start'], n_['f_end'], n_['f_peak'], n_['f_min']))
