"""ORIGIN — TikTok V2 « rythmée » : texte cinétique mot par mot, coupes calées à 120 BPM, sans musique.

Usage : python3 -I render_v2.py PACK FONTS OUT [--preview t1,t2,...]
"""
import sys, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

PACK, FONTS, OUT = sys.argv[1:4]
PREVIEW = None
if '--preview' in sys.argv:
    PREVIEW = [float(x) for x in sys.argv[sys.argv.index('--preview') + 1].split(',')]

W, H, FPS, DUR = 1080, 1920, 30, 32.0
NF = int(DUR * FPS)
GOLD = (240, 190, 100)
CREAM = (250, 240, 222)
WHITE = (255, 255, 255)

NAMES = ['01_le_hook_nombre', '02_calcul_simple', '03_commente_ton_nombre', '04_symbolique_des_nombres',
         '05_partage_avec_un_proche', '06_le_reveal_des_racines', '07_racine_arbre_interactif', '08_signature_origin']


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255


FOND = [load(f'{PACK}/fonds_sans_texte/{n}_fond.png') for n in NAMES]
CAPTURE = load(f'{PACK}/capture_arbre_origin_demo.png')
LOGO = load(f'{PACK}/logo_origin_reference_fourni_par_utilisateur.jpg')

F_CG = f'{FONTS}/CG-SemiBold.ttf'
F_CGM = f'{FONTS}/CG-Medium.ttf'
F_CGI = f'{FONTS}/CG-MediumItalic.ttf'
F_XB = f'{FONTS}/OS-ExtraBold.ttf'
F_OSB = f'{FONTS}/OS-Bold.ttf'
F_OSS = f'{FONTS}/OS-SemiBold.ttf'
F_SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


# ---------------------------------------------------------------- courbes
def clamp01(x):
    return float(min(max(x, 0.0), 1.0))


def eout(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def backout(x, k=2.2):
    x = clamp01(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


# ---------------------------------------------------------------- effets globaux (temps absolus)
CUTS = [3.0, 8.0, 11.0, 15.0, 18.5, 22.0, 23.5, 28.0]
FLASH = [(1.5, .35), (6.0, .55), (7.0, .7), (17.5, .45), (21.25, .55), (22.0, .9), (23.5, .5), (28.0, .8),
         (3.0, .3), (8.0, .3), (11.0, .3), (15.0, .3), (31.0, .25)]
SHAKE = [(2.5, 9), (6.0, 14), (7.0, 20), (17.5, 12), (21.25, 14), (22.0, 20), (28.0, 16), (9.0, 8)]
_rng = np.random.default_rng(3)
_SH = _rng.standard_normal((NF + 10, 2))


def flash_amount(t):
    return sum(s * np.exp(-max(t - t0, 0) / 0.09) for t0, s in FLASH if t >= t0)


def shake_offset(t):
    a = sum(s * np.exp(-max(t - t0, 0) / 0.12) for t0, s in SHAKE if t >= t0)
    n = int(t * FPS)
    return _SH[n] * a


def punch(t, events):
    """Zoom sec : petit à-coup sur chaque évènement (mot qui tombe, coupe)."""
    return sum(a * np.exp(-max(t - t0, 0) / 0.11) for t0, a in events if t >= t0)


# ---------------------------------------------------------------- fonds
def frame_bg(img, cx, cy, zoom, dark=0.55):
    dark = min(1.0, dark * 1.45)
    s = zoom
    M = np.float32([[s, 0, W / 2 - cx * s], [0, s, H / 2 - cy * s]])
    fr = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return fr * dark


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.4 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2, 0, 1))[..., None]
del yy, xx


def framing(t, shots):
    """shots = [(t0, cx, cy, zoom_debut, zoom_fin)] ; coupe franche entre deux plans, lente poussée dans le plan."""
    cur = shots[0]
    nxt_t = None
    for i, sh in enumerate(shots):
        if t >= sh[0]:
            cur = sh
            nxt_t = shots[i + 1][0] if i + 1 < len(shots) else None
    t0, cx, cy, z0, z1 = cur
    span = (nxt_t - t0) if nxt_t else 1.5
    return cx, cy, z0 + (z1 - z0) * ease((t - t0) / span)


# ---------------------------------------------------------------- particules dorées
NP = 140
P_X = _rng.uniform(0, W, NP)
P_Y = _rng.uniform(0, H, NP)
P_V = _rng.uniform(25, 90, NP)
P_R = _rng.uniform(1.5, 4.5, NP)
P_PH = _rng.uniform(0, 6.28, NP)


def particles(fr, t, k=1.0):
    ov = np.zeros((H // 2, W // 2), np.float32)
    ys = (P_Y - P_V * t) % H
    xs = (P_X + 18 * np.sin(t * 0.7 + P_PH)) % W
    tw = 0.5 + 0.5 * np.sin(t * 3 + P_PH * 3)
    for x, y, r, a in zip(xs, ys, P_R, tw):
        cv2.circle(ov, (int(x / 2), int(y / 2)), max(1, int(r / 2)), float(a), -1, cv2.LINE_AA)
    ov = cv2.GaussianBlur(ov, (0, 0), 1.6) * 0.9 * k
    ov = cv2.resize(ov, (W, H), interpolation=cv2.INTER_LINEAR)
    g = np.array(GOLD, np.float32) / 255
    fr[:] = 1 - (1 - fr) * (1 - np.clip(ov[..., None] * g, 0, 1))


# ---------------------------------------------------------------- calques
def put_layer(fr, rgb, al, cx, cy, a, scale=1.0, sx=1.0, glow=0.0):
    if a <= 0.003:
        return
    if abs(scale - 1) > 1e-3 or abs(sx - 1) > 1e-3:
        h0, w0 = al.shape
        nw, nh = max(1, int(w0 * scale * sx)), max(1, int(h0 * scale))
        rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
        al = cv2.resize(al, (nw, nh), interpolation=cv2.INTER_LINEAR)
    if glow > 0.003:
        p = 40
        rgb = np.pad(rgb, ((p, p), (p, p), (0, 0)))
        al = np.pad(al, p)
    h, w = al.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if fx0 >= fx1 or fy0 >= fy1:
        return
    sl = (slice(fy0 - y0, fy1 - y0), slice(fx0 - x0, fx1 - x0))
    reg = fr[fy0:fy1, fx0:fx1]
    if glow > 0.003:
        g = cv2.GaussianBlur(rgb * al[..., None], (0, 0), 16)[sl] * glow * a
        reg[:] = 1 - (1 - reg) * (1 - np.clip(g, 0, 1))
    A = (al[sl] * a)[..., None]
    reg[:] = reg * (1 - A) + rgb[sl] * A


_tl = {}


def text_layer(text, font, size, color, maxw=900, shadow=True):
    k = (text, font, size, color, maxw, shadow)
    if k in _tl:
        return _tl[k]
    while ImageFont.truetype(font, size).getlength(text) > maxw and size > 20:
        size -= 2
    f = ImageFont.truetype(font, size)
    asc, desc = f.getmetrics()
    pad = 40
    w = int(f.getlength(text)) + 2 * pad
    h = asc + desc + 2 * pad
    img = Image.new('L', (w, h), 0)
    ImageDraw.Draw(img).text((pad, pad), text, font=f, fill=255)
    al = np.asarray(img).astype(np.float32) / 255
    rgb = np.ones((h, w, 3), np.float32) * (np.array(color, np.float32) / 255)
    if shadow:  # ombre douce pour la lisibilité : intégrée au calque (noir sous le texte)
        sh = cv2.GaussianBlur(np.roll(al, 6, 0), (0, 0), 11) * 0.75
        a_tot = al + sh * (1 - al)
        rgb = rgb * (al / np.maximum(a_tot, 1e-4))[..., None]
        al = a_tot
    _tl[k] = (rgb, al)
    return _tl[k]


def word(fr, t, text, font, size, color, cy, t0, t1=None, cx=540, glow=0.0, big=1.55, maxw=900, d=0.16):
    """Mot qui tombe : arrive gros puis se pose (léger rebond), disparaît d'un coup sec à t1."""
    if t < t0 or (t1 is not None and t >= t1):
        return
    p = (t - t0) / d
    s = big - (big - 1) * backout(p)
    a = clamp01(p * 2.5)
    if t1 is not None and t > t1 - 0.06:
        a *= clamp01((t1 - t) / 0.06)
    rgb, al = text_layer(text, font, size, color, maxw)
    g = glow * (0.5 + 0.5 * np.exp(-max(t - t0, 0) / 0.3))
    put_layer(fr, rgb, al, cx, cy, a, scale=s, glow=g)


def rounded_mask(h, w, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r - 1, h - 1), 255, -1)
    cv2.rectangle(m, (0, r), (w - 1, h - r - 1), 255, -1)
    for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


def gold_border(fr, x0, y0, x1, y1, r, a, th=3):
    ov = fr.copy()
    col = tuple(c / 255 for c in GOLD)
    for p0, p1 in (((x0 + r, y0), (x1 - r, y0)), ((x0 + r, y1), (x1 - r, y1)),
                   ((x0, y0 + r), (x0, y1 - r)), ((x1, y0 + r), (x1, y1 - r))):
        cv2.line(ov, p0, p1, col, th, cv2.LINE_AA)
    for (cx, cy), ang in (((x0 + r, y0 + r), 180), ((x1 - r, y0 + r), 270), ((x1 - r, y1 - r), 0), ((x0 + r, y1 - r), 90)):
        cv2.ellipse(ov, (cx, cy), (r, r), ang, 0, 90, col, th, cv2.LINE_AA)
    fr[:] = fr * (1 - a) + ov * a


_bub = {}


def bubble_layer(text, mine):
    k = (text, mine)
    if k in _bub:
        return _bub[k]
    f = ImageFont.truetype(F_OSB, 58)
    tw = int(f.getlength(text))
    w, h = tw + 110, 112
    img = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    fill = (58, 40, 22, 235) if mine else (22, 30, 40, 235)
    dr.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=56, fill=fill, outline=GOLD + (255,), width=3)
    dr.text((20 + w / 2, 20 + h / 2), text, font=f, fill=CREAM + (255,), anchor='mm')
    arr = np.asarray(img).astype(np.float32) / 255
    _bub[k] = (arr[..., :3].copy(), arr[..., 3].copy())
    return _bub[k]


def bubble(fr, t, text, mine, cy, t0, t1=None):
    if t < t0 or (t1 is not None and t >= t1):
        return
    p = (t - t0) / 0.2
    rgb, al = bubble_layer(text, mine)
    w = al.shape[1]
    cx = 110 + w / 2 if mine else 970 - w / 2
    put_layer(fr, rgb, al, cx, cy + (1 - eout(p)) * 40, clamp01(p * 3), scale=0.6 + 0.4 * backout(p))


# ---------------------------------------------------------------- scènes (temps absolus)
DISCLAIMER = 'Numérologie : interprétation symbolique, non scientifique'


def scene_hook(t):
    cx, cy, z = framing(t, [(0.0, 330, 560, 1.55, 1.45), (1.0, 420, 700, 1.3, 1.22), (2.0, 540, 900, 1.08, 1.02)])
    z += punch(t, [(0.0, .05), (0.5, .03), (1.0, .05), (1.5, .06), (2.0, .05), (2.5, .06)])
    fr = frame_bg(FOND[0], cx, cy, z, 0.62) * VIGNETTE
    word(fr, t, 'TA DATE', F_XB, 150, WHITE, 800, 0.0, 1.0)
    word(fr, t, 'DE NAISSANCE', F_XB, 112, WHITE, 950, 0.5, 1.0)
    word(fr, t, 'CACHE', F_XB, 160, WHITE, 800, 1.0, 2.0)
    word(fr, t, 'UN NOMBRE.', F_XB, 150, GOLD, 960, 1.5, 2.0, glow=.6)
    word(fr, t, 'TU CONNAIS', F_XB, 130, WHITE, 800, 2.0, 3.0)
    word(fr, t, 'LE TIEN ?', F_XB, 170, GOLD, 970, 2.5, 3.0, glow=.7)
    return fr


def scene_calc(t):
    cx, cy, z = framing(t, [(3.0, 540, 1000, 1.25, 1.15), (4.0, 560, 900, 1.12, 1.08),
                            (6.0, 540, 960, 1.35, 1.3), (7.0, 540, 900, 1.05, 1.0)])
    ev = [(3.0, .06), (6.0, .08), (6.5, .04), (7.0, .1)] + [(4.0 + .25 * k, .025) for k in range(8)]
    fr = frame_bg(FOND[1], cx, cy, z + punch(t, ev), 0.5) * VIGNETTE
    word(fr, t, 'EXEMPLE', F_XB, 56, GOLD, 560, 3.0, 6.0, big=1.3)
    word(fr, t, '17 / 09 / 1988', F_XB, 120, CREAM, 720, 3.0, 6.0, big=1.4)
    # les chiffres tombent un par un, sur deux lignes
    f = ImageFont.truetype(F_XB, 110)
    for line, y, k0 in ((['1', ' + 7', ' + 0', ' + 9'], 900, 0), (['+ 1', ' + 9', ' + 8', ' + 8'], 1040, 4)):
        full = ''.join(line)
        x_left = 540 - f.getlength(full) / 2
        for j, chunk in enumerate(line):
            pre = f.getlength(''.join(line[:j]))
            wch = f.getlength(chunk)
            word(fr, t, chunk.strip(), F_XB, 110, GOLD, y, 4.0 + .25 * (k0 + j), 6.0,
                 cx=x_left + pre + wch - f.getlength(chunk.strip()) / 2, glow=.5, big=1.8)
    word(fr, t, '= 43', F_XB, 230, GOLD, 820, 6.0, 7.0, glow=.8, big=1.9)
    word(fr, t, '4 + 3', F_XB, 130, CREAM, 1060, 6.5, 7.0)
    word(fr, t, 'TON CHEMIN DE VIE', F_XB, 60, CREAM, 560, 7.25, 8.0, big=1.3)
    word(fr, t, '7', F_CG, 560, GOLD, 930, 7.0, 8.0, glow=1.0, big=2.2)
    return fr


def scene_toi(t):
    cx, cy, z = framing(t, [(8.0, 540, 800, 1.2, 1.12), (9.5, 540, 1000, 1.1, 1.02)])
    fr = frame_bg(FOND[2], cx, cy, z + punch(t, [(8.0, .05), (9.0, .06), (9.5, .05), (10.0, .04)]), 0.55) * VIGNETTE
    # le 7 pivote et devient « ? »
    if t < 9.5:
        rgb7, al7 = text_layer('7', F_CG, 560, GOLD)
        rgbq, alq = text_layer('?', F_CG, 560, GOLD)
        if t < 8.5:
            put_layer(fr, rgb7, al7, 540, 930, 1, glow=.9)
        elif t < 8.6:
            put_layer(fr, rgb7, al7, 540, 930, 1, sx=max(0.02, 1 - (t - 8.5) / 0.1), glow=.9)
        else:
            p = (t - 8.6) / 0.12
            put_layer(fr, rgbq, alq, 540, 930, 1, sx=min(1, max(0.02, p)), scale=1 + 0.15 * (1 - backout((t - 8.6) / 0.3)),
                      glow=1.0)
    word(fr, t, 'ET TOI ?', F_XB, 150, WHITE, 1330, 9.0, 9.5, glow=.3)
    word(fr, t, 'ÉCRIS TON NOMBRE', F_XB, 104, WHITE, 800, 9.5, 11.0)
    word(fr, t, 'EN COMMENTAIRE', F_XB, 104, GOLD, 940, 10.0, 11.0, glow=.5)
    if t >= 10.3:
        rgb, al = text_layer('↓', F_SYM, 150, GOLD)
        put_layer(fr, rgb, al, 540, 1110 + 22 * abs(np.sin((t - 10.3) * 2 * np.pi)), clamp01((t - 10.3) / 0.1), glow=.6)
    return fr


NUMS = ['INITIATIVE', 'LIEN', 'EXPRESSION', 'STRUCTURE', 'LIBERTÉ', 'HARMONIE', 'INTROSPECTION', 'AMBITION',
        'TRANSMISSION']


def scene_symb(t):
    n_t = [11.75 + .3 * k for k in range(9)]
    z = 1.0 + 0.1 * ease((t - 11) / 4) + punch(t, [(11.0, .05)] + [(x, .04) for x in n_t] + [(14.5, .05)])
    fr = frame_bg(FOND[3], 540, 930, z, 0.75) * VIGNETTE
    word(fr, t, 'CHAQUE NOMBRE,', F_XB, 84, WHITE, 520, 11.0, 14.5, big=1.3)
    word(fr, t, 'UNE SYMBOLIQUE', F_XB, 92, GOLD, 625, 11.25, 14.5, big=1.3, glow=.4)
    for k in range(9):
        t1 = n_t[k + 1] if k < 8 else 14.5
        word(fr, t, str(k + 1), F_CG, 400, GOLD, 960, n_t[k], t1, glow=.8, big=1.6, d=.12)
        word(fr, t, NUMS[k], F_XB, 76, CREAM, 1210, n_t[k], t1, big=1.3, d=.12)
    word(fr, t, 'LEQUEL', F_XB, 130, WHITE, 900, 14.5, 15.0)
    word(fr, t, 'TE RESSEMBLE ?', F_XB, 110, GOLD, 1040, 14.65, 15.0, glow=.5)
    if t >= 11.0:
        rgb, al = text_layer(DISCLAIMER, F_CGI, 36, CREAM, shadow=True)
        put_layer(fr, rgb, al, 540, 1395, 0.9 * clamp01((t - 11.0) / 0.3))
    return fr


def scene_share(t):
    cx, cy, z = framing(t, [(15.0, 540, 900, 1.25, 1.15), (16.5, 540, 950, 1.08, 1.02)])
    ev = [(15.0, .05), (15.25, .04), (15.75, .05), (16.1, .05), (16.5, .05), (16.85, .03), (17.2, .03), (17.5, .08)]
    fr = frame_bg(FOND[4], cx, cy, z + punch(t, ev), 0.5) * VIGNETTE
    word(fr, t, 'ENVOIE-LA À', F_XB, 100, WHITE, 660, 15.0, 16.5)
    word(fr, t, 'TON PARTENAIRE', F_XB, 120, GOLD, 820, 15.25, 15.75, glow=.5)
    word(fr, t, 'UN AMI', F_XB, 150, GOLD, 820, 15.75, 16.1, glow=.5)
    word(fr, t, 'TA FAMILLE', F_XB, 140, GOLD, 820, 16.1, 16.5, glow=.5)
    bubble(fr, t, 'Moi : 7', True, 700, 16.5)
    bubble(fr, t, 'Toi : 3', False, 860, 16.85)
    bubble(fr, t, 'Et nous deux ?', True, 1020, 17.2)
    word(fr, t, 'COMPAREZ !', F_XB, 150, GOLD, 1240, 17.5, glow=.7)
    return fr


L6 = FOND[5].mean(2)
L6 = (L6 - L6.min()) / (L6.max() - L6.min())


def scene_roots(t):
    if t < 18.5:  # coupure : noir
        fr = np.zeros((H, W, 3), np.float32)
        if t >= 18.1:
            rgb, al = text_layer('Mais…', F_CGI, 110, CREAM, shadow=False)
            put_layer(fr, rgb, al, 540, 930, clamp01((t - 18.1) / 0.25))
        return fr
    u = ease((t - 18.5) / 1.6)
    thr = 1.05 - 1.25 * u  # la lumière gagne les branches, puis les portraits
    al = np.clip((L6 - thr) / 0.18, 0, 1)[..., None]
    img = FOND[5] * np.maximum(al, 0.05)
    cx, cy, z = framing(t, [(18.5, 540, 760, 1.0, 1.1), (20.5, 700, 620, 1.4, 1.5)])
    z += punch(t, [(18.75, .03), (19.25, .03), (19.75, .04), (20.5, .06), (20.75, .03), (21.25, .08)])
    fr = frame_bg(img, cx, cy, z, 0.7 if t < 20.5 else 0.6) * VIGNETTE
    word(fr, t, 'UN NOMBRE', F_XB, 116, WHITE, 720, 18.75, 20.5)
    word(fr, t, 'NE RACONTE PAS', F_XB, 100, WHITE, 850, 19.25, 20.5)
    word(fr, t, 'TOUTE TON HISTOIRE.', F_XB, 92, GOLD, 980, 19.75, 20.5, glow=.5)
    word(fr, t, 'ET TES', F_XB, 130, WHITE, 1000, 20.75, 22.0)
    word(fr, t, 'RACINES ?', F_CG, 200, GOLD, 1170, 21.25, 22.0, glow=.9, big=1.8)
    return fr


BG7 = np.clip(cv2.GaussianBlur(FOND[6], (0, 0), 20) * 0.35, 0, 1)
PANEL = (40, 330, 1040, 1330)
CH, CW = CAPTURE.shape[:2]
SHOTS = [(23.5, 440, 450, 880, 440, 450), (24.25, 420, 700, 600, 560, 700),
         (25.5, 1170, 620, 430, 1170, 640), (27.0, 925, 450, 880, 900, 450)]
TAPS = [((196, 540), 24.6), ((1170, 512), 25.8)]


def cam(t):
    """Caméra dans la capture : zoom rapide (0,22 s) d'un plan à l'autre, dérive lente dans le plan."""
    idx = max(i for i, s in enumerate(SHOTS) if t >= s[0])
    t0, ax, ay, w, bx, by = SHOTS[idx]
    end = SHOTS[idx + 1][0] if idx + 1 < len(SHOTS) else 28.0
    u = ease((t - t0) / (end - t0))
    x, y = ax + (bx - ax) * u, ay + (by - ay) * u
    if idx > 0 and t - t0 < 0.22:
        pt0, pax, pay, pw, pbx, pby = SHOTS[idx - 1]
        k = eout((t - t0) / 0.22)
        x, y, w = pbx + (x - pbx) * k, pby + (y - pby) * k, pw + (w - pw) * k
    return x, y, w


def scene_racine(t):
    if t < 23.5:
        cx, cy, z = framing(t, [(22.0, 540, 900, 1.25, 1.05)])
        z += punch(t, [(22.0, .1), (22.5, .03), (23.0, .04)])
        fr = frame_bg(FOND[6], cx, cy, z, 0.5) * VIGNETTE
        word(fr, t, 'NOUVEAU CHEZ ORIGIN', F_XB, 56, GOLD, 600, 22.0, big=1.3)
        word(fr, t, 'RACINE', F_CG, 240, GOLD, 790, 22.0, glow=1.0, big=2.0, d=.2)
        word(fr, t, 'L’ARBRE GÉNÉALOGIQUE', F_XB, 78, WHITE, 980, 22.5)
        word(fr, t, 'INTERACTIF', F_XB, 120, GOLD, 1100, 23.0, glow=.5)
        return fr
    fr = BG7.copy()
    word(fr, t, 'RACINE', F_CG, 120, GOLD, 215, 23.5, glow=.5, big=1.3)
    x0, y0, x1, y1 = PANEL
    pw, ph = x1 - x0, y1 - y0
    p_in = (t - 23.5) / 0.25
    s_in = 1.25 - 0.25 * backout(p_in)
    x, y, w = cam(t)
    h = w * ph / pw
    x = min(max(x, w / 2), CW - w / 2)
    y = min(max(y, h / 2), CH - h / 2)
    M = np.float32([[pw / w, 0, -(x - w / 2) * pw / w], [0, ph / h, -(y - h / 2) * ph / h]])
    img = cv2.warpAffine(CAPTURE, M, (pw, ph), flags=cv2.INTER_AREA if w > pw else cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REPLICATE)
    # taps sur un portrait
    for (px, py), tt in TAPS:
        k = (t - tt) / 0.6
        if 0 <= k <= 1:
            sx, sy = (px - (x - w / 2)) * pw / w, (py - (y - h / 2)) * ph / h
            ov = img.copy()
            cv2.circle(ov, (int(sx), int(sy)), int(26 + 90 * eout(k)), (1, .93, .8), 5, cv2.LINE_AA)
            cv2.circle(ov, (int(sx), int(sy)), 22, (1, .93, .8), -1, cv2.LINE_AA)
            img = img * (1 - .85 * (1 - k)) + ov * .85 * (1 - k)
    m = rounded_mask(ph, pw, 26)
    rgba_rgb = img
    put_layer(fr, rgba_rgb, m, (x0 + x1) / 2, (y0 + y1) / 2, clamp01(p_in * 3), scale=s_in)
    if p_in >= 1:
        gold_border(fr, x0, y0, x1 - 1, y1 - 1, 26, 1.0, 4)
        rgb, al = text_layer('Démonstration · personnes fictives', F_OSS, 24, CREAM)
        put_layer(fr, rgb, al, x1 - 230, y1 - 34, 0.9)
    word(fr, t, 'EXPLORE LES GÉNÉRATIONS', F_XB, 70, WHITE, 1420, 24.25, 25.5, big=1.3)
    word(fr, t, 'OUVRE LEURS FICHES', F_XB, 80, WHITE, 1420, 25.5, 27.0, big=1.3)
    word(fr, t, 'RELIE TES RACINES', F_XB, 80, GOLD, 1420, 27.0, big=1.3, glow=.4)
    return fr


LOGO_C = (345.0, 752.0)  # centre de l'emblème dans le fichier logo fourni


def logo_frame(scale, cy):
    M = np.float32([[scale, 0, 540 - LOGO_C[0] * scale], [0, scale, cy - LOGO_C[1] * scale]])
    fr = cv2.warpAffine(LOGO, M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    lw = LOGO.shape[1] * scale
    x0 = 540 - LOGO_C[0] * scale
    xs = np.arange(W, dtype=np.float32)
    edge = np.clip(np.minimum(xs - x0, x0 + lw - xs) / 30, 0, 1)
    return fr * edge[None, :, None]


def scene_logo(t):
    p = (t - 28.0) / 0.35
    s = 1.95 - 0.5 * backout(p) - 0.04 * ease((t - 28.4) / 3.6)
    fr = logo_frame(s, 880)
    word(fr, t, 'CE N’ÉTAIT', F_CG, 84, CREAM, 190, 28.5, big=1.4)
    word(fr, t, 'QUE LE DÉBUT.', F_CG, 108, GOLD, 295, 28.75, glow=.5, big=1.4)
    word(fr, t, 'Chez ORIGIN, bien d’autres calculs', F_CGM, 54, CREAM, 1290, 29.5, big=1.2)
    word(fr, t, 'sont réalisés pour toi.', F_CGM, 54, CREAM, 1355, 29.75, big=1.2)
    word(fr, t, 'Avec RACINE, découvre ton histoire familiale.', F_CGI, 46, GOLD, 1430, 30.5, big=1.2)
    if t >= 31.0:
        p = (t - 31.0) / 0.2
        ov = np.zeros((130, 700, 3), np.float32)
        ov[:] = (0.05, 0.04, 0.03)
        m = rounded_mask(90, 660, 45)
        al = np.zeros((130, 700), np.float32)
        al[20:110, 20:680] = m * 0.85
        tmp = fr.copy()
        put_layer(tmp, ov, al, 540, 1525, 1, scale=0.6 + 0.4 * backout(p))
        if p >= 1:
            gold_border(tmp, 210, 1480, 869, 1569, 44, 1.0, 3)
        fr[:] = fr * (1 - clamp01(p * 3)) + tmp * clamp01(p * 3)
        word(fr, t, 'DÉCOUVRE ORIGIN', F_XB, 44, GOLD, 1525, 31.0, big=1.3)
        rgb, al = text_layer(DISCLAIMER, F_CGI, 30, CREAM)
        put_layer(fr, rgb, al, 540, 1610, 0.75 * clamp01((t - 31.0) / 0.3))
    return fr


SCENES = [(0.0, scene_hook), (3.0, scene_calc), (8.0, scene_toi), (11.0, scene_symb), (15.0, scene_share),
          (18.0, scene_roots), (22.0, scene_racine), (28.0, scene_logo)]


def compose(t):
    fn = [f for s, f in SCENES if t >= s][-1]
    fr = fn(t)
    dark = 18.0 <= t < 18.5
    if not dark:
        particles(fr, t, 0.55 if t >= 28.0 else 1.0)
    dx, dy = shake_offset(t)
    if abs(dx) + abs(dy) > 0.5:
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    fl = flash_amount(t)
    if fl > 0.003 and not dark:
        fr = fr * (1 - fl) + np.array([1.0, 0.92, 0.78], np.float32) * fl
    return fr


def to_u8(fr):
    return (np.clip(fr, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    if PREVIEW:
        tiles = []
        for t in PREVIEW:
            im = Image.fromarray(to_u8(compose(t))).resize((360, 640))
            ImageDraw.Draw(im).text((8, 8), f'{t:.2f}s', fill=(0, 255, 255))
            tiles.append(im)
        cols = min(len(tiles), 6)
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 360, rows * 640))
        for i, im in enumerate(tiles):
            sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
        sheet.save(f'{OUT}/preview_v2.jpg', quality=90)
        sys.exit(0)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
           '-profile:v', 'high', '-movflags', '+faststart', f'{OUT}/ORIGIN_TikTok_32s_v2_rythme.mp4']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(NF):
        p.stdin.write(to_u8(compose(n / FPS)).tobytes())
        if n % 90 == 0:
            print(f'{n / FPS:5.1f}s', flush=True)
    p.stdin.close()
    p.wait()
    print('ok')
