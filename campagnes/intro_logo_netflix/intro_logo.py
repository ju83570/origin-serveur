#!/usr/bin/env python3
"""Intro logo ORIGIN facon « ta-dum » Netflix — 1080x1920, 3,8 s, avec son.

0,0-0,45 s  point de lumiere -> flare anamorphique horizontal
0,45 s      « TA » : l'eclipse s'allume (revelation circulaire a bord lumineux)
0,90 s      « DUM » : flash, onde de choc, logo plein feu avec punch + aberration chromatique
0,9-2,6 s   tenue : poussee lente, rayons de lumiere, halo qui respire, poussiere doree
2,6-3,8 s   plongee dans la main : zoom accelere + trainees radiales dorees -> noir

Usage : python3 intro_logo.py [--carre]   (--carre : version 1080x1080 en plus)
"""
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 3.8
T_TA, T_DUM, T_DIVE = 0.45, 0.90, 2.6
GOLD = np.array([1.0, 0.76, 0.36], np.float32)


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * x * (x * (6 * x - 15) + 10)


def ease_in(x):
    return np.clip(x, 0, 1) ** 3


def ease_out(x):
    return 1 - (1 - np.clip(x, 0, 1)) ** 3


def build(W, H):
    src = Image.open(os.path.join(HERE, "logo_origin.jpg")).convert("RGB")
    sw, sh = src.size
    # centre du logo (cercle) dans le visuel source
    lcx, lcy, lr = 610 / 1220 * sw, 1340 / 2712 * sh, 300 / 1220 * sw
    scale = 0.82 * W / sw  # marge pour le mot ORIGIN pendant les zooms
    big = src.resize((int(sw * scale * 2), int(sh * scale * 2)), Image.LANCZOS)
    k = scale * 2
    cx, cy, R = lcx * k, lcy * k, lr * k

    def cam(z, img=big):
        """Cadre W x H centre sur le logo, zoom z."""
        bw, bh = W * 2 / z, H * 2 / z
        x0, y0 = cx - bw / 2, cy - bh / 2
        return np.asarray(img.transform((W, H), Image.AFFINE, (bw / W, 0, x0, 0, bh / H, y0),
                                        Image.BICUBIC), np.float32) / 255.0

    # rayons de lumiere precalcules (flou radial des parties claires)
    lum = np.asarray(big.convert("L"), np.float32) / 255.0
    bright = Image.fromarray((np.clip((lum - 0.55) / 0.45, 0, 1) * 255).astype(np.uint8))
    acc = np.zeros(lum.shape, np.float32)
    for s in np.linspace(1.0, 1.45, 18):
        bw, bh = big.size[0] / s, big.size[1] / s
        x0, y0 = cx - bw / 2 * 1, cy - bh / 2 * 1
        x0, y0 = cx - cx / s, cy - cy / s
        acc += np.asarray(bright.transform(big.size, Image.AFFINE, (1 / s, 0, x0, 0, 1 / s, y0), Image.BILINEAR), np.float32)
    rays = Image.fromarray(np.clip(acc / 18 * 1.6, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    rays = Image.merge("RGB", [rays] * 3)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ocx, ocy = W / 2, H / 2
    dist = np.sqrt((xx - ocx) ** 2 + (yy - ocy) ** 2)
    R1 = R / 2  # rayon du cercle en sortie a z=1
    rng = np.random.default_rng(5)
    N = 90
    pts = dict(a=rng.uniform(0, 6.283, N), r=rng.uniform(R1 * 0.9, max(W, H) * 0.6, N),
               v=rng.uniform(0.02, 0.12, N), s=rng.uniform(1.0, 3.5, N) * W / 1080,
               b=rng.uniform(0.3, 1.0, N), ph=rng.uniform(0, 6.283, N))
    vign = (1 - 0.5 * np.clip((dist / (0.75 * max(W, H) / 2)) - 0.6, 0, 1))[..., None]

    def zoom_blur(img_fn, z, amount, n=12):
        acc = 0
        for s in np.linspace(0, amount, n):
            acc = acc + img_fn(z * (1 + s))
        return acc / n

    def chroma(a, amt):
        if amt < 0.3:
            return a
        out = a.copy()
        sh_ = int(round(amt))
        out[..., 0] = np.roll(a[..., 0], sh_, axis=1)
        out[..., 2] = np.roll(a[..., 2], -sh_, axis=1)
        return out

    def frame(t):
        # zoom camera
        if t < T_DUM:
            z = 1.12
        elif t < T_DIVE:
            p = (t - T_DUM) / (T_DIVE - T_DUM)
            z = 1.0 + 0.10 * (1 - ease_out(min(1, p * 6))) + 0.05 * p  # punch puis poussee lente
        else:
            p = (t - T_DIVE) / (DUR - T_DIVE)
            z = 1.05 * (1 + 7 * ease_in(p))
        out = np.zeros((H, W, 3), np.float32)

        # 1) point lumineux + flare anamorphique
        if t < T_DUM + 0.3:
            p = t / T_TA
            grow = ease_out(p)
            fade = 1 - ease((t - T_DUM) / 0.3)
            core = np.exp(-(dist / (6 + 40 * grow) / (W / 1080)) ** 2)
            flare = np.exp(-((yy - ocy) / (3 * W / 1080)) ** 2) * np.exp(-np.abs(xx - ocx) / (W * (0.05 + 0.6 * grow)))
            out += (core[..., None] * (GOLD * 0.6 + 0.4) + flare[..., None] * GOLD * 0.9) * min(1, t / 0.12) * fade

        # 2) TA : revelation circulaire (l'eclipse s'allume)
        if T_TA <= t < T_DUM:
            p = ease_out((t - T_TA) / (T_DUM - T_TA))
            img = cam(z)
            rr = R1 * z * 1.25 * p
            m = np.clip((rr - dist) / (25 * W / 1080), 0, 1)
            edge = np.exp(-((dist - rr) / (10 * W / 1080)) ** 2)
            out += img * m[..., None] * 0.55 + edge[..., None] * GOLD * 1.2

        # 3) DUM et suite
        if t >= T_DUM:
            u = t - T_DUM
            if t < T_DIVE:
                img = cam(z)
            else:
                amount = 0.6 * ease_in((t - T_DIVE) / (DUR - T_DIVE)) + 0.02
                img = zoom_blur(cam, z, amount)
            breathe = 0.5 + 0.5 * np.sin(u * 4.0)
            rimg = cam(z, rays)
            img = img + rimg * GOLD * (0.55 + 0.25 * breathe) * (1 - ease(u / 0.1) * 0.2)
            img = chroma(img, 14 * (W / 1080) * np.exp(-u * 7))
            # flash + onde de choc
            flash = np.exp(-u * 11) * 0.7
            ring_r = R1 * (1 + u * 3.5)
            shock = np.exp(-((dist - ring_r) / (18 * W / 1080)) ** 2) * np.exp(-u * 4)
            img = img + flash * (GOLD * 0.5 + 0.5) + shock[..., None] * GOLD * 0.9
            out = out + img
            # poussiere doree en orbite lente
            for i in range(N):
                a = pts["a"][i] + pts["v"][i] * u
                r = pts["r"][i] * z * (1 + 0.04 * u)
                x, y = ocx + r * np.cos(a), ocy + r * np.sin(a) * 1.1
                s = pts["s"][i] * (1 + 2 * max(0, z - 1.3))
                x0, x1 = int(max(0, x - 4 * s)), int(min(W, x + 4 * s + 1))
                y0, y1 = int(max(0, y - 4 * s)), int(min(H, y + 4 * s + 1))
                if x1 <= x0 or y1 <= y0:
                    continue
                g = np.exp(-(((xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2) / (2 * s * s)))
                br = pts["b"][i] * (0.5 + 0.5 * np.sin(u * 3 + pts["ph"][i])) * min(1, u / 0.3)
                out[y0:y1, x0:x1] += g[..., None] * GOLD * br * 0.8

        # fin : flash blanc-dore puis noir
        if t > DUR - 0.5:
            p = (t - (DUR - 0.5)) / 0.5
            out = out + np.exp(-((p - 0.25) / 0.15) ** 2) * (GOLD * 0.6 + 0.4) * 0.8
            out = out * (1 - ease(p))
        out = out * vign
        out += np.random.default_rng(int(t * 1000)).standard_normal((H, W, 1)).astype(np.float32) * 0.012
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)

    return frame


def sound(path):
    SR = 48000
    n = int(DUR * SR)
    L = np.zeros(n)
    Rr = np.zeros(n)
    rng = np.random.default_rng(1)

    def put(sig, t0, pan=0.0):
        i = int(t0 * SR)
        j = min(n, i + len(sig))
        L[i:j] += sig[: j - i] * np.sqrt((1 - pan) / 2)
        Rr[i:j] += sig[: j - i] * np.sqrt((1 + pan) / 2)

    def bp_noise(m, lo, hi):
        spec = np.fft.rfft(rng.standard_normal(m))
        f = np.fft.rfftfreq(m, 1 / SR)
        spec *= (f > lo) & (f < hi)
        x = np.fft.irfft(spec, m)
        return x / np.abs(x).max()

    # montee de lumiere (shimmer)
    m = int(T_TA * SR)
    tt = np.linspace(0, 1, m)
    put(bp_noise(m, 3000, 12000) * tt ** 2 * 0.12, 0)
    # TA : impact sourd
    m = int(0.6 * SR)
    t = np.arange(m) / SR
    ta = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 25)) * t) * np.exp(-t * 9) * 0.9
    ta += bp_noise(m, 100, 2000) * np.exp(-t * 40) * 0.25
    put(ta, T_TA)
    # DUM : boom + accord grave cuivre (La : 55, 110, 165, 220, 277)
    m = int((DUR - T_DUM) * SR)
    t = np.arange(m) / SR
    boom = np.sin(2 * np.pi * (38 + 45 * np.exp(-t * 7)) * t) * np.exp(-t * 1.6) * 1.0
    boom += bp_noise(m, 40, 400) * np.exp(-t * 14) * 0.5
    put(boom, T_DUM)
    env = (1 - np.exp(-t * 30)) * np.exp(-t * 0.6)
    for f, g in ((55, 0.35), (110, 0.30), (164.8, 0.22), (220, 0.15), (277.2, 0.10), (329.6, 0.07)):
        for pan, det in ((-0.5, 0.997), (0.5, 1.003)):
            saw = sum(np.sin(2 * np.pi * f * det * h * t) / h ** 1.3 for h in range(1, 9))
            put(saw * env * g * 0.5, T_DUM, pan)
    # whoosh de plongee
    m = int((DUR - T_DIVE) * SR)
    tt = np.linspace(0, 1, m)
    put(bp_noise(m, 300, 9000) * tt ** 2.5 * np.where(tt > 0.85, (1 - tt) / 0.15, 1) * 0.5, T_DIVE)
    put(np.sin(2 * np.pi * np.cumsum(300 + 1500 * tt ** 2) / SR) * tt ** 3 * 0.06, T_DIVE)

    # reverb
    out = np.stack([L, Rr], 1)
    m = int(2.2 * SR)
    t = np.arange(m) / SR
    size = 1 << int(np.ceil(np.log2(n + m)))
    for c in range(2):
        ir = rng.standard_normal(m) * np.exp(-t / 0.5)
        ir /= np.sqrt((ir ** 2).sum())
        wet = np.fft.irfft(np.fft.rfft(out[:, c], size) * np.fft.rfft(ir, size), size)[:n]
        out[:, c] = out[:, c] + wet * 0.9
    out = np.tanh(out * 1.3)
    out /= np.abs(out).max() / 0.9
    fade = int(0.25 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype("<i2").tobytes())


def render(W, H, name, wav):
    frame = build(W, H)
    out = os.path.join(HERE, name)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", str(DUR), "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(int(DUR * FPS)):
        p.stdin.write(frame(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print("OK ->", out)


if __name__ == "__main__":
    wav = os.path.join(HERE, "ta_dum_origin.wav")
    sound(wav)
    render(1080, 1920, "INTRO_ORIGIN_1080x1920.mp4", wav)
    if "--carre" in sys.argv:
        render(1080, 1080, "INTRO_ORIGIN_1080x1080.mp4", wav)
