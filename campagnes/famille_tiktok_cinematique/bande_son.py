#!/usr/bin/env python3
"""Bande-son originale synthetisee (libre de droits) calee sur le montage.

Pad emotionnel + arpeges de piano, whooshes sur chaque transition,
battement de coeur en montee, riser + impact sur le CTA final.
"""
import wave

import numpy as np

SR = 44100
RNG = np.random.default_rng(7)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na) ** 2
    e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def tone(f, dur, harm=6, decay=None, detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for h in range(1, harm + 1):
        amp = 1 / h ** 1.6
        if decay is not None:
            amp = amp * np.exp(-t * decay * (1 + 0.6 * (h - 1)))
        out += amp * np.sin(2 * np.pi * f * h * (1 + detune) * t + RNG.uniform(0, 6.28))
    return out


def bandnoise(n, lo, hi):
    spec = np.fft.rfft(RNG.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    spec *= ((fr > lo) & (fr < hi)).astype(float)
    x = np.fft.irfft(spec, n)
    return x / (np.abs(x).max() + 1e-9)


def add(buf, sig, t0, pan=0.0):
    i = int(t0 * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if j <= i:
        return
    sig = sig[: j - i]
    buf[i:j, 0] += sig * np.sqrt((1 - pan) / 2)
    buf[i:j, 1] += sig * np.sqrt((1 + pan) / 2)


def reverb(x, secs=2.6, wet=0.3):
    n = int(secs * SR)
    t = np.arange(n) / SR
    out = np.empty_like(x)
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    for c in range(2):
        ir = RNG.standard_normal(n) * np.exp(-t / 0.55)
        ir /= np.sqrt((ir ** 2).sum())
        y = np.fft.irfft(np.fft.rfft(x[:, c], size) * np.fft.rfft(ir, size), size)[: len(x)]
        out[:, c] = x[:, c] * (1 - wet) + y * wet * 3
    return out


CHORDS = {  # notes MIDI
    "Am": [45, 57, 60, 64], "F": [41, 53, 57, 60],
    "C": [48, 55, 60, 64], "G": [43, 55, 59, 62],
}
PROG = ["Am", "F", "C", "G", "Am", "F", "C", "G", "F", "C"]


def render(starts, total, path):
    n = int(total * SR)
    music = np.zeros((n, 2))
    fx = np.zeros((n, 2))
    bounds = starts[1:]

    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else total
        name = PROG[k]
        dur = e - s + 1.2
        # pad (deux couches legerement desaccordees, stereo)
        for i, m in enumerate(CHORDS[name]):
            g = 0.10 if i == 0 else 0.06
            for pan, det in ((-0.6, -0.0018), (0.6, 0.0018)):
                sig = tone(midi(m), dur, harm=5, detune=det) * env_adsr(int(dur * SR), 0.7, 1.2)
                add(music, sig * g, s - 0.2, pan)
        # arpege de piano (a partir de la scene 2, densifie ensuite)
        if k >= 1:
            notes = [m + 12 for m in CHORDS[name][1:]] + [CHORDS[name][1] + 24]
            pattern = [0, 1, 2, 3, 2, 1, 3, 2]
            step = 0.5 if k < 6 else 0.25
            t, j = s, 0
            while t < e - 0.05:
                m = notes[pattern[j % len(pattern)]]
                vel = 0.16 if j % 2 == 0 else 0.11
                if k >= 6 and j % 2:
                    vel *= 0.7
                add(music, tone(midi(m), 1.6, harm=7, decay=2.6) * vel, t, pan=RNG.uniform(-0.4, 0.4))
                t += step
                j += 1
        # basse grave a partir de la scene 5
        if k >= 4:
            add(music, tone(midi(CHORDS[name][0] - 12), e - s + 0.5, harm=3) * env_adsr(int((e - s + 0.5) * SR), 0.3, 0.6) * 0.10, s)

    # accord d'accroche a t=0
    for m in CHORDS["Am"][1:]:
        add(music, tone(midi(m + 12), 3.0, harm=7, decay=1.2) * 0.18, 0.05)

    # battement de coeur (scenes 7 a 9)
    t = starts[6]
    while t < starts[9] - 0.6:
        for off, amp in ((0, 0.55), (0.22, 0.35)):
            L = int(0.35 * SR)
            tt = np.arange(L) / SR
            kick = np.sin(2 * np.pi * (48 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 11)
            add(fx, kick * amp, t + off)
        t += 1.0

    # whoosh sur chaque transition
    for i, b in enumerate(bounds):
        L = int(1.0 * SR)
        tt = np.linspace(0, 1, L)
        env = np.where(tt < 0.55, (tt / 0.55) ** 3, np.exp(-(tt - 0.55) * 9))
        w = bandnoise(L, 400, 5000) * env * 0.28
        add(fx, w, b - 0.55, pan=-0.7 if i % 2 else 0.7)
        if i in (2, 4, 7):  # petits impacts sous les transitions fortes
            L2 = int(1.4 * SR)
            t2 = np.arange(L2) / SR
            add(fx, np.sin(2 * np.pi * (34 + 30 * np.exp(-t2 * 6)) * t2) * np.exp(-t2 * 3) * 0.45, b)

    # riser + impact sur le CTA
    b = starts[9]
    L = int(2.6 * SR)
    tt = np.linspace(0, 1, L)
    riser = bandnoise(L, 800, 9000) * tt ** 3 * 0.35
    riser += np.sin(2 * np.pi * np.cumsum(200 + 700 * tt ** 2) / SR) * tt ** 3 * 0.08
    add(fx, riser, b - 2.6)
    L = int(3.0 * SR)
    t2 = np.arange(L) / SR
    boom = np.sin(2 * np.pi * (30 + 40 * np.exp(-t2 * 5)) * t2) * np.exp(-t2 * 1.6)
    boom += bandnoise(L, 30, 300) * np.exp(-t2 * 8) * 0.6
    add(fx, boom * 0.9, b)
    # scintillement final
    for m in (72, 76, 79, 84):
        sig = tone(midi(m), total - b, harm=2) * (0.5 + 0.5 * np.sin(2 * np.pi * 5 * np.arange(int((total - b) * SR)) / SR))
        add(music, sig * env_adsr(len(sig), 1.0, 2.0) * 0.025, b, pan=RNG.uniform(-0.8, 0.8))

    # arc dramatique : montee progressive, creux avant le CTA, explosion finale
    pts_t = [0, starts[3], starts[6], starts[9] - 2.6, starts[9] - 0.3, starts[9], total]
    pts_g = [0.5, 0.65, 0.85, 1.0, 0.35, 1.15, 1.0]
    arc = np.interp(np.arange(n) / SR, pts_t, pts_g)[:, None]
    mix = reverb(music, wet=0.35) * arc + reverb(fx, secs=1.8, wet=0.2)
    mix = np.tanh(mix * 1.1)
    mix /= np.abs(mix).max() / 0.89
    fade = int(1.8 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    mix[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
