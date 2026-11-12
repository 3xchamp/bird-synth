import numpy as np
from scipy.io import wavfile
from scipy import signal as sig

sr, x = wavfile.read('/home/hatch/workspace/bird-synth/samples/cardinal/XC1093538.wav')
if x.ndim > 1: x = x[:,0]
x = x.astype(np.float64); x /= (np.max(np.abs(x))+1e-12)

# bandpass 1.5-9k, hilbert envelope, smooth 4 ms
sos = sig.butter(4, [1500, 9000], btype='band', fs=sr, output='sos')
xb = sig.sosfilt(sos, x)
env = np.abs(sig.hilbert(xb))
k = int(0.004*sr); env = np.convolve(env, np.ones(k)/k, mode='same')
env_db = 20*np.log10(env + 1e-6)

def show(t0, t1, label):
    print(f'--- envelope {label} {t0}-{t1}s (each char = 20 ms, value = dB, "." = below -60)')
    i0, i1 = int(t0*sr), int(t1*sr)
    step = int(0.020*sr)
    vals = [env_db[i:i+step].max() for i in range(i0, i1, step)]
    line = ''
    for v in vals:
        if v < -60: line += '.'
        elif v < -50: line += '1'
        elif v < -45: line += '2'
        elif v < -40: line += '3'
        elif v < -35: line += '4'
        elif v < -30: line += '5'
        elif v < -25: line += '6'
        elif v < -20: line += '7'
        elif v < -15: line += '8'
        else: line += '9'
    for j in range(0, len(line), 100):
        print(f'{t0 + j*0.02:6.2f} {line[j:j+100]}')
    # min/max stats
    seg = env_db[i0:i1]
    print('   seg dB: max %.1f  p90 %.1f  p50 %.1f  p10 %.1f' % (seg.max(), np.percentile(seg,90), np.percentile(seg,50), np.percentile(seg,10)))

show(1.2, 5.2, 'bout 0 (incl. long seg 2.01-4.83)')
show(28.2, 31.8, 'bout 3 (discrete notes)')
