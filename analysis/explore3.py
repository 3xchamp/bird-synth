import numpy as np
from scipy.io import wavfile
from scipy import signal as sig

sr, x = wavfile.read('/home/hatch/workspace/bird-synth/samples/cardinal/XC1093538.wav')
if x.ndim > 1: x = x[:,0]
x = x.astype(np.float64); x /= (np.max(np.abs(x))+1e-12)
sos = sig.butter(4, [1500, 9000], btype='band', fs=sr, output='sos')
xb = sig.sosfilt(sos, x)
env = np.abs(sig.hilbert(xb))
k = int(0.003*sr); env = np.convolve(env, np.ones(k)/k, mode='same')
env_db = 20*np.log10(env + 1e-6)

def show(t0, t1):
    i0, i1 = int(t0*sr), int(t1*sr)
    step = int(0.005*sr)
    vals = [( (i)/sr, env_db[i:i+step].max()) for i in range(i0, i1, step)]
    for j in range(0, len(vals), 20):
        row = vals[j:j+20]
        print(' '.join(f'{v:5.1f}' for _, v in row), '   <- t=%.2f' % row[0][0])
show(2.0, 3.0)
print()
show(29.2, 30.2)
