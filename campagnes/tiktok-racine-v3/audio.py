"""Habillage sonore synthétisé (sans voix) calé sur le montage de render.py."""
import sys, wave, numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

OUT = sys.argv[1]
SR, DUR = 48000, 32.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)
pad_bus = np.zeros((2, N))
fx_bus = np.zeros((2, N))


def env_ad(n, a, d):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / max(a, 1e-4))) * np.exp(-t / d)


def add(bus, sig, start, pan=0.0):
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[:N - i]
    bus[0, i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    bus[1, i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def bell(f, amp=0.18, d=1.4):
    n = int(d * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 3) \
        + 0.25 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6)
    return amp * s * env_ad(n, 0.002, d / 4)


def whoosh(d=0.5, amp=0.22, rise=True):
    n = int(d * SR)
    x = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    for k in range(8):  # balayage du filtre par morceaux
        lo = 300 + 2600 * (k / 8 if rise else 1 - k / 8)
        sos = butter(2, [lo, lo * 2.2], 'bandpass', fs=SR, output='sos')
        seg = sosfilt(sos, noise)
        w = np.clip(1 - np.abs(x * 8 - k - 0.5), 0, 1)
        out += seg * w
    e = np.sin(np.pi * x) ** 2 * (x if rise else 1)
    return amp * out * e / (np.abs(out).max() + 1e-9) * 2


def pop(amp=0.22):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 950 * np.exp(-t * 22) + 260
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.001, 0.025)


def boom(amp=0.6, d=2.5):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 34 + 40 * np.exp(-t * 8)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.004, 0.7)
    sub = sosfilt(butter(2, 180, 'low', fs=SR, output='sos'), rng.standard_normal(n)) * env_ad(n, 0.002, 0.12)
    return amp * (s + 0.6 * sub / (np.abs(sub).max() + 1e-9))


def pad(freqs, t0, t1, amp, att=1.5, rel=0.05, trem=0.15):
    i0, i1 = int(t0 * SR), int(t1 * SR)
    t = np.arange(i1 - i0) / SR
    n = len(t)
    e = np.minimum(1, t / att) * np.minimum(1, (n / SR - t) / max(rel, 1 / SR))
    for ch, det in ((0, -0.6), (1, 0.6)):
        s = np.zeros(n)
        for j, f in enumerate(freqs):
            ff = f * (1 + det * 0.002 * (j % 2 * 2 - 1))
            s += np.sin(2 * np.pi * ff * t + j) * (1 / (1 + j * 0.35))
            s += 0.25 * np.sin(2 * np.pi * ff * 2.003 * t) * (1 / (1 + j * 0.35))
        s *= (1 - trem) + trem * np.sin(2 * np.pi * 0.23 * t + ch)
        pad_bus[ch, i0:i1] += amp * e * s / len(freqs)


# --- 0–18 s : nappe chaude (la mineur → fa → do → sol), coupée net à 18 s
pad([110, 164.8, 220, 261.6, 329.6], 0.0, 4.5, 0.32, att=0.4, rel=0.4)
pad([87.3, 130.8, 174.6, 220, 261.6], 4.2, 8.6, 0.30, att=0.5, rel=0.4)
pad([130.8, 196, 261.6, 329.6, 392], 8.3, 12.4, 0.30, att=0.5, rel=0.4)
pad([98, 146.8, 196, 246.9, 293.7], 12.1, 18.0, 0.30, att=0.5, rel=0.0)
# pulsation discrète
for k in range(int(18 / 0.5)):
    t0 = k * 0.5
    if t0 < 17.9:
        add(fx_bus, bell(55 if k % 2 == 0 else 82.4, 0.10, 0.6), t0)

# accroche
add(fx_bus, bell(880, 0.10, 2.0), 0.5, -0.2)
add(fx_bus, bell(1318.5, 0.08, 2.0), 0.72, 0.2)
# transitions par mouvement
for b in (3.0, 8.0, 11.0, 15.0):
    add(fx_bus, whoosh(0.5, 0.20), b - 0.36)
# calcul : un tintement par chiffre (pentatonique montante)
penta = [523.3, 587.3, 659.3, 784, 880, 1046.5, 1174.7, 1318.5]
for i in range(8):
    add(fx_bus, bell(penta[i], 0.11, 1.0), 3.0 + 1.0 + 0.24 * i, -0.4 + 0.1 * i)
add(fx_bus, bell(440, 0.16, 1.8), 3.0 + 2.9)          # = 43
for f, dt in ((659.3, 0), (880, 0.05), (1318.5, 0.1)):  # le 7
    add(fx_bus, bell(f, 0.14, 2.0), 3.0 + 4.0 + dt)
# scène 3 : le 7, puis « ? »
add(fx_bus, bell(784, 0.14, 1.5), 8.3)
add(fx_bus, bell(1046.5, 0.12, 1.5), 9.1)
add(fx_bus, bell(1568, 0.07, 1.5), 9.15)
# scène 4 : neuf cases
for i in range(9):
    add(fx_bus, bell([392, 440, 523.3, 587.3, 659.3, 784, 880, 1046.5, 1174.7][i], 0.08, 0.8), 11.7 + 0.22 * i,
        -0.6 + 0.15 * i)
add(fx_bus, bell(880, 0.12, 1.6), 14.1)
# scène 5 : bulles
for i in range(3):
    add(fx_bus, pop(0.25), 15.75 + 0.3 * i, (-0.3, 0.3, -0.3)[i])
add(fx_bus, bell(659.3, 0.10, 1.2), 17.6)

# --- 18 s : silence, puis crescendo (changement d'atmosphère : ré mineur grave + montée)
pad([36.7, 73.4, 110, 146.8], 18.35, 22.0, 0.55, att=3.2, rel=0.02, trem=0.05)
pad([146.8, 220, 293.7, 349.2, 440], 19.2, 22.0, 0.30, att=2.6, rel=0.02, trem=0.25)
riser = whoosh(3.4, 0.30, rise=True)
add(fx_bus, riser, 18.6)
for k, f in enumerate([293.7, 349.2, 440, 523.3, 587.3]):
    add(fx_bus, bell(f, 0.06 + 0.012 * k, 1.5), 18.8 + 0.6 * k)

# --- 22–28 s : RACINE, atmosphère majeure et lumineuse
add(fx_bus, boom(0.45, 2.0), 22.0)
pad([146.8, 220, 293.7, 370, 440], 22.0, 28.0, 0.30, att=0.3, rel=0.3)
pad([587.3, 740, 880], 22.3, 28.0, 0.10, att=1.0, rel=0.3, trem=0.3)
for f, dt in ((587.3, 0), (880, 0.06), (1174.7, 0.12)):
    add(fx_bus, bell(f, 0.13, 2.2), 22.3 + dt)
add(fx_bus, whoosh(0.7, 0.16), 23.7)
for t0 in (25.25, 26.9):  # appuis sur un portrait
    add(fx_bus, pop(0.18), t0)
    add(fx_bus, bell(1318.5, 0.06, 0.8), t0 + 0.02)
for t0, f in ((24.9, 659.3), (26.0, 740), (27.0, 880)):
    add(fx_bus, bell(f, 0.07, 1.0), t0)

# --- 28–32 s : signature
add(fx_bus, boom(0.7, 3.0), 28.0)
pad([73.4, 110, 146.8, 185, 220, 293.7], 28.0, 32.0, 0.36, att=0.6, rel=1.2)
for f, dt in ((587.3, 0.9), (740, 1.1), (880, 1.6), (1174.7, 2.8)):
    add(fx_bus, bell(f, 0.09, 2.2), 28.0 + dt)

# réverbération simple (réponse impulsionnelle bruitée décroissante)
ir_n = int(1.8 * SR)
ir = rng.standard_normal((2, ir_n)) * np.exp(-np.arange(ir_n) / SR / 0.45)
ir /= np.sqrt((ir ** 2).sum(1, keepdims=True))
dry = pad_bus + fx_bus
wet = np.stack([fftconvolve(dry[c], ir[c])[:N] for c in range(2)])
mix = dry + 0.35 * wet
# silence franc à la coupure 18,0 → 18,35 s (la queue de réverbération est coupée aussi)
i0, i1 = int(18.0 * SR), int(18.35 * SR)
mix[:, i0:i1] = 0
fade_in = np.linspace(0, 1, int(0.01 * SR))
mix[:, i1:i1 + len(fade_in)] *= fade_in
mix[:, :int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
mix[:, -int(0.6 * SR):] *= np.linspace(1, 0, int(0.6 * SR)) ** 2
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 0.89 / np.abs(mix).max()

pcm = (mix.T * 32767).astype('<i2')
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('audio ok')
