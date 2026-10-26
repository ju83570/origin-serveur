#!/usr/bin/env python3
"""Montage cinematographique ORIGIN Famille — 10 visuels, 1080x1920, ~43 s.

Effets : mise au point d'ouverture, mouvements de camera avec easing,
transitions variees (flash dore, zoom traversant, whip pan, light leak),
poussiere doree flottante, bokeh, grain argentique, vignettage,
reflet lumineux sur les titres, impact + pulsation du CTA final,
bande-son originale synchronisee (bande_son.py).

Usage : python3 montage_cinematique.py   (ou --preview pour un rendu rapide 540x960)
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bande_son  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = "--preview" in sys.argv
W, H = (540, 960) if PREVIEW else (1080, 1920)
FPS = 30
TR = 0.7  # duree des transitions
OUT = os.path.join(HERE, "ORIGIN_FAMILLE_CINEMATIQUE_1080x1920.mp4" if not PREVIEW else "preview.mp4")

# (duree, mouvement camera, transition vers la scene suivante)
SCENES = [
    (3.6, "in", "flash"),
    (4.2, "out", "zoom"),
    (4.2, "in", "whip"),
    (4.6, "out", "leak"),
    (4.4, "in", "zoom"),
    (4.2, "out", "whipv"),
    (4.6, "in", "leak"),
    (4.2, "out", "whip"),
    (4.2, "in", "flash"),
    (6.4, "cta", None),
]
ZMAX = 1.07
GOLD = np.array([1.0, 0.78, 0.42], np.float32)

starts = np.concatenate([[0], np.cumsum([d for d, _, _ in SCENES])[:-1]])
TOTAL = float(sum(d for d, _, _ in SCENES))


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * x * (x * (6 * x - 15) + 10)


def bell(p):
    return np.sin(np.pi * np.clip(p, 0, 1)) ** 2


# ---------- sources ----------
SRC = []
for i in range(10):
    im = Image.open(os.path.join(HERE, "VISUELS", f"{i + 1:02d}.png")).convert("RGB")
    im = im.resize((W * 2, H * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    SRC.append(im)


def camera(i, u, extra_zoom=1.0, dx=0.0, dy=0.0):
    """Cadre de la scene i au temps local u (s), avec zoom/decalage additionnels."""
    d, mv, _ = SCENES[i]
    p = ease(u / d)
    if mv == "in":
        z = 1 + (ZMAX - 1) * p
    elif mv == "out":
        z = ZMAX - (ZMAX - 1) * p
    else:  # CTA : leger recul puis cadre fixe pour la lisibilite
        z = 1 + 0.06 * (1 - ease(u / 2.2))
    z *= extra_zoom
    sw, sh = SRC[i].size
    bw, bh = sw / z, sh / z
    cx = sw / 2 + dx * bw
    cy = sh / 2 + dy * bh + (0.006 * sh * np.sin(u * 0.9 + i) if mv != "cta" else 0)
    x0, y0 = cx - bw / 2, cy - bh / 2
    fr = SRC[i].transform((W, H), Image.AFFINE, (bw / W, 0, x0, 0, bh / H, y0), Image.BICUBIC)
    return fr, (x0, y0, z * W / sw)


def to_np(im):
    return np.asarray(im, np.float32) / 255.0


def blur(arr, amount):
    if amount < 0.05:
        return arr
    f = max(1.0, 1 + amount * 0.5)
    im = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
    small = im.resize((max(8, int(W / f)), max(8, int(H / f))), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(float(amount) * 0.8 * W / 1080))
    return to_np(small.resize((W, H), Image.BILINEAR))


def motion_blur(arr, k, axis):
    k = int(k)
    if k < 2:
        return arr
    c = np.cumsum(arr, axis=axis, dtype=np.float32)
    pad = [(0, 0)] * 3
    pad[axis] = (k, 0)
    c = np.pad(c, pad, mode="edge")
    sl_hi = [slice(None)] * 3
    sl_lo = [slice(None)] * 3
    sl_hi[axis] = slice(k, None)
    sl_lo[axis] = slice(0, -k)
    return (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / k


# ---------- calques d'ambiance precalcules ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = (1 - 0.38 * np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6)[..., None]
rng = np.random.default_rng(3)
GRAIN = []
for _ in range(8):
    g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    GRAIN.append(np.asarray(Image.fromarray(g).resize((W, H), Image.BILINEAR))[..., None])

S = W / 1080


def sprite(rad):
    n = int(rad * 4) + 1
    a = np.arange(n) - n // 2
    return np.exp(-(a[:, None] ** 2 + a[None, :] ** 2) / (2 * (rad / 1.6) ** 2)).astype(np.float32)


N_DUST = 70
dust = {
    "x": rng.uniform(0, W, N_DUST), "y": rng.uniform(0, H, N_DUST),
    "vx": rng.uniform(-8, 8, N_DUST) * S, "vy": rng.uniform(-38, -10, N_DUST) * S,
    "r": rng.choice([2, 3, 4, 6, 9, 14], N_DUST, p=[.3, .25, .2, .12, .08, .05]) * S,
    "a": rng.uniform(0.25, 0.9, N_DUST), "ph": rng.uniform(0, 6.28, N_DUST),
}
SPRITES = {}


def draw_dust(acc, t):
    for k in range(N_DUST):
        rad = max(1.0, dust["r"][k])
        key = round(rad, 1)
        if key not in SPRITES:
            SPRITES[key] = sprite(rad)
        sp = SPRITES[key]
        x = (dust["x"][k] + dust["vx"][k] * t + 12 * S * np.sin(t * 0.7 + dust["ph"][k])) % W
        y = (dust["y"][k] + dust["vy"][k] * t) % H
        a = dust["a"][k] * (0.55 + 0.45 * np.sin(t * 2.1 + dust["ph"][k]))
        if rad > 8 * S:
            a *= 0.35  # gros bokeh doux
        n = sp.shape[0]
        x0, y0 = int(x) - n // 2, int(y) - n // 2
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(W, x0 + n), min(H, y0 + n)
        if xb <= xa or yb <= ya:
            continue
        acc[ya:yb, xa:xb] += sp[ya - y0:yb - y0, xa - x0:xb - x0, None] * a * 0.55


LW, LH = 108, 192
ly, lx = np.mgrid[0:LH, 0:LW].astype(np.float32)


def light_leak(t, strength):
    if strength < 0.01:
        return 0
    m = np.zeros((LH, LW), np.float32)
    for j, (sx, sy, sp, rad) in enumerate(((0.2, 0.3, 0.9, 55), (0.85, 0.6, -0.7, 70), (0.5, 0.1, 0.5, 45))):
        cx = LW * (sx + 0.35 * np.sin(t * sp + j))
        cy = LH * (sy + 0.2 * np.cos(t * sp * 0.8 + j))
        m += np.exp(-((lx - cx) ** 2 + (ly - cy) ** 2) / (2 * rad ** 2))
    m = np.asarray(Image.fromarray(m).resize((W, H), Image.BILINEAR))[..., None]
    col = np.array([1.0, 0.55, 0.18], np.float32)
    return m * col * strength


def title_shine(frame, u):
    """Reflet lumineux diagonal sur les titres (pixels clairs du haut de l'image)."""
    p = (u - 0.55) / 1.1
    if not 0 <= p <= 1:
        return frame
    pos = -0.3 + 1.6 * ease(p)
    band = np.exp(-(((xx / W) + (yy / H) * 0.35 - pos) / 0.06) ** 2)
    top = np.clip(1 - (yy / H - 0.28) / 0.1, 0, 1)
    lum = frame.mean(axis=2)
    mask = np.clip((lum - 0.55) / 0.3, 0, 1)
    return frame + (band * top * mask)[..., None] * GOLD * 0.55


def cta_fx(frame, u, geo):
    """Halo pulsant + reflet sur le bouton « Decouvrir ORIGIN » et le logo."""
    x0, y0, sc = geo
    def mp(px, py):  # coordonnees visuel 941x1672 -> sortie
        sw = SRC[9].size[0]
        return (px * sw / 941 - x0) * sc, (py * sw / 941 - y0) * sc
    bx0, by0 = mp(183, 1068)
    bx1, by1 = mp(757, 1172)
    ccx, ccy = (bx0 + bx1) / 2, (by0 + by1) / 2
    hw, hh = (bx1 - bx0) / 2, (by1 - by0) / 2
    dxr = np.maximum(np.abs(xx - ccx) - hw + hh, 0)
    dyr = np.maximum(np.abs(yy - ccy), 0)
    dist = np.sqrt(dxr ** 2 + dyr ** 2) - hh
    pulse = 0.5 + 0.5 * np.sin((u - 0.6) * 2 * np.pi / 1.3)
    on = ease((u - 0.5) / 0.5)
    halo = np.exp(-np.clip(dist, 0, None) / (28 * S)) * (dist > -2) * (0.25 + 0.35 * pulse) * on
    frame = frame + halo[..., None] * GOLD * 0.8
    # reflet qui traverse le bouton toutes les 1,6 s
    ph = ((u - 0.9) % 1.6) / 0.7
    if u > 0.9 and ph <= 1:
        pos = bx0 - 80 * S + (bx1 - bx0 + 160 * S) * ease(ph)
        band = np.exp(-((xx - pos - (yy - ccy) * 0.5) / (22 * S)) ** 2) * (dist < 0)
        frame = frame + band[..., None] * 0.6
    # logo main
    lx_, ly_ = mp(470, 1420)
    d2 = np.sqrt((xx - lx_) ** 2 + (yy - ly_) ** 2)
    ring = np.exp(-((d2 - 50 * SRC[9].size[0] / 941 * sc) / (14 * S)) ** 2)
    frame = frame + ring[..., None] * GOLD * 0.35 * (0.5 + 0.5 * np.sin(u * 3.2)) * on
    return frame


def scene_frame(i, u, **kw):
    fr, geo = camera(i, u, **kw)
    a = to_np(fr)
    a = title_shine(a, u)
    if SCENES[i][1] == "cta":
        a = cta_fx(a, u, geo)
    return a


def compose(t):
    # scene courante / transition
    k = int(np.searchsorted(starts, t, side="right") - 1)
    k = max(0, min(9, k))
    u = t - starts[k]
    leak = 0.0
    flash = 0.0
    nxt = k + 1 if k < 9 and t > starts[k + 1] - TR / 2 else None
    prv = k - 1 if k > 0 and u < TR / 2 else None
    if nxt is None and prv is not None:
        a_i, b_i, p = prv, k, (u + TR / 2) / TR
    elif nxt is not None:
        a_i, b_i, p = k, nxt, (t - (starts[nxt] - TR / 2)) / TR
    else:
        a_i = b_i = None
    if a_i is None:
        frame = scene_frame(k, u)
    else:
        kind = SCENES[a_i][2]
        ua, ub = t - starts[a_i], t - starts[b_i]
        ub_c = max(ub, 0)
        e = ease(p)
        if kind == "zoom":
            A = scene_frame(a_i, ua, extra_zoom=1 + 0.22 * ease(p * 1.4))
            B = scene_frame(b_i, ub_c, extra_zoom=1 + 0.2 * (1 - ease(p * 1.4 - 0.4)))
            m = ease((p - 0.35) / 0.3)
            frame = blur(A, 10 * bell(p)) * (1 - m) + blur(B, 10 * bell(p)) * m
            flash = 0.12 * bell(p)
        elif kind in ("whip", "whipv"):
            horiz = kind == "whip"
            # push : A sort, B entre colle a A
            if horiz:
                A = scene_frame(a_i, ua, dx=e)
                B = scene_frame(b_i, ub_c, dx=e - 1)
                cut = int(round(W * (1 - e)))
                frame = np.concatenate([A[:, :cut], B[:, cut:]], axis=1)
            else:
                A = scene_frame(a_i, ua, dy=e)
                B = scene_frame(b_i, ub_c, dy=e - 1)
                cut = int(round(H * (1 - e)))
                frame = np.concatenate([A[:cut], B[cut:]], axis=0)
            frame = motion_blur(frame, 90 * S * bell(p), axis=1 if horiz else 0)
        elif kind == "leak":
            A = scene_frame(a_i, ua)
            B = scene_frame(b_i, ub_c)
            frame = A * (1 - e) + B * e
            leak = 0.45 * bell(p)
        else:  # flash dore
            A = scene_frame(a_i, ua, extra_zoom=1 + 0.08 * e)
            B = scene_frame(b_i, ub_c, extra_zoom=1 + 0.08 * (1 - e))
            m = ease((p - 0.42) / 0.16)
            frame = A * (1 - m) + B * m
            flash = 0.6 * np.exp(-((p - 0.5) / 0.12) ** 2)
    # ouverture : mise au point + fondu depuis le noir
    if t < 1.0:
        frame = blur(frame, 12 * (1 - ease(t / 0.7)))
        frame = frame * ease(t / 0.45)
    # impact sur le CTA : petite secousse + flash
    if 0 <= t - starts[9] < 0.4:
        q = (t - starts[9]) / 0.4
        sh = int(14 * S * (1 - q) * np.sin(q * 40))
        frame = np.roll(frame, sh, axis=0)
    # ambiance permanente
    frame = frame + light_leak(t, 0.07 + leak)
    if flash > 0:
        frame = frame + flash * (GOLD * 0.6 + 0.4)
    acc = np.zeros((H, W, 1), np.float32)
    draw_dust(acc, t)
    frame = frame + acc * GOLD
    frame = frame * VIGNETTE
    frame = frame + GRAIN[int(t * FPS) % len(GRAIN)] * 0.022
    # fondu de fin
    if t > TOTAL - 0.6:
        frame = frame * ease((TOTAL - t) / 0.6 + 0.0) ** 0.5
    return (np.clip(frame, 0, 1) * 255).astype(np.uint8)


def main():
    wav = os.path.join(HERE, "bande_son_origin.wav")
    bande_son.render(list(starts), TOTAL, wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "medium" if PREVIEW else "slow", "-crf", "19",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(round(TOTAL * FPS))
    for f in range(nf):
        proc.stdin.write(compose(f / FPS).tobytes())
        if f % 150 == 0:
            print(f"{f}/{nf}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("OK ->", OUT)


if __name__ == "__main__":
    main()
