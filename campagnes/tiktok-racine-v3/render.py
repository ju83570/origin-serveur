"""ORIGIN — TikTok « Ton nombre n'est qu'un début » : rendu 1080x1920 / 30 fps / 32 s.

Usage : python3 -I render.py PACK FONTS OUT [--preview t1,t2,...]
"""
import sys, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

PACK, FONTS, OUT = sys.argv[1:4]
PREVIEW = None
if '--preview' in sys.argv:
    PREVIEW = [float(x) for x in sys.argv[sys.argv.index('--preview') + 1].split(',')]

W, H, FPS, DUR = 1080, 1920, 30, 32.0
NF = int(DUR * FPS)
GOLD = (236, 186, 98)
CREAM = (246, 234, 212)

NAMES = ['01_le_hook_nombre', '02_calcul_simple', '03_commente_ton_nombre', '04_symbolique_des_nombres',
         '05_partage_avec_un_proche', '06_le_reveal_des_racines', '07_racine_arbre_interactif', '08_signature_origin']


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255


VIS = [load(f'{PACK}/visuels_1080x1920/{n}.png') for n in NAMES]
FOND = [load(f'{PACK}/fonds_sans_texte/{n}_fond.png') for n in NAMES]
CAPTURE = load(f'{PACK}/capture_arbre_origin_demo.png')
LOGO = load(f'{PACK}/logo_origin_reference_fourni_par_utilisateur.jpg')

F_CG = f'{FONTS}/CG-SemiBold.ttf'
F_CGM = f'{FONTS}/CG-Medium.ttf'
F_CGI = f'{FONTS}/CG-MediumItalic.ttf'
F_OSB = f'{FONTS}/OS-Bold.ttf'
F_OSS = f'{FONTS}/OS-SemiBold.ttf'
F_SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


# ---------------------------------------------------------------- helpers
def clamp01(x):
    return float(min(max(x, 0.0), 1.0))


def eout(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ramp(t, t0, d=0.35):
    return eout((t - t0) / d)


BADGE = (30, 150, 30, 150)  # pastille de numéro de scène, à ne jamais afficher


def corrected_base(vis, fond, excl, sigma=45):
    """Fond sans texte recalé en basse fréquence sur le visuel, pour éviter les coutures."""
    d = vis - fond
    wm = np.ones((H, W), np.float32)
    for y0, y1, x0, x1 in list(excl) + [BADGE]:
        wm[y0:y1, x0:x1] = 0
    num = cv2.GaussianBlur(d * wm[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(wm, (0, 0), sigma)[..., None]
    return np.clip(fond + num / np.maximum(den, 1e-3), 0, 1)


def inpaint(img, bands):
    """Vide une carte : chaque bande est remplie par interpolation verticale entre ses lignes propres."""
    out = img.copy()
    for y0, y1, x0, x1 in bands:
        top = img[y0 - 4:y0, x0:x1].mean(0)
        bot = img[y1:y1 + 4, x0:x1].mean(0)
        k = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
        out[y0:y1, x0:x1] = top[None] * (1 - k) + bot[None] * k
    return out


def matte_of(vis, under):
    m = np.clip((np.abs(vis - under).max(2) - 0.03) / 0.12, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 1.0)


_rm = {}


def rectmask(h, w, f):
    k = (h, w, f)
    if k not in _rm:
        m = np.zeros((h, w), np.float32)
        m[f:h - f, f:w - f] = 1
        _rm[k] = cv2.GaussianBlur(m, (0, 0), max(f / 2, 0.5)) if f else m
    return _rm[k]


def put_layer(fr, rgb, al, cx, cy, a, scale=1.0, glow=0.0):
    if a <= 0.003 and glow <= 0.003:
        return
    if abs(scale - 1) > 1e-3:
        rgb = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        al = cv2.resize(al, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    if glow > 0.003:
        p = 36
        rgb = np.pad(rgb, ((p, p), (p, p), (0, 0)))
        al = np.pad(al, p)
    h, w = al.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if fx0 >= fx1 or fy0 >= fy1:
        return
    sl = (slice(fy0 - y0, fy1 - y0), slice(fx0 - x0, fx1 - x0))
    reg = fr[fy0:fy1, fx0:fx1]
    A = (al[sl] * a)[..., None]
    reg[:] = reg * (1 - A) + rgb[sl] * A
    if glow > 0.003:
        g = cv2.GaussianBlur(rgb * al[..., None], (0, 0), 13)[sl] * glow
        reg[:] = 1 - (1 - reg) * (1 - np.clip(g, 0, 1))


def put(fr, src, rect, a, dy=0.0, scale=1.0, glow=0.0, feather=8, matte=None):
    y0, y1, x0, x1 = rect
    rgb = src[y0:y1, x0:x1]
    al = matte[y0:y1, x0:x1] if matte is not None else rectmask(y1 - y0, x1 - x0, feather)
    put_layer(fr, rgb, al, (x0 + x1) / 2, (y0 + y1) / 2 + dy, a, scale, glow)


def appear(fr, src, rect, lt, t0, d=0.4, rise=24, **kw):
    a = ramp(lt, t0, d)
    put(fr, src, rect, a, dy=(1 - a) * rise, **kw)


def kenburns(fr, s, cx, cy, dx=0.0, dy=0.0):
    if abs(s - 1) < 1e-4 and dx == 0 and dy == 0:
        return fr
    M = np.float32([[s, 0, (1 - s) * cx + dx], [0, s, (1 - s) * cy + dy]])
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


_tl = {}


def text_layer(text, font, size, color, sym=None):
    """Calque RGBA (rgb float, alpha float) ; `sym` = glyphe ✦ en préfixe (police symbole)."""
    k = (text, font, size, color, sym)
    if k in _tl:
        return _tl[k]
    f = ImageFont.truetype(font, size)
    parts = []
    if sym:
        parts.append((sym + '  ', ImageFont.truetype(F_SYM, int(size * 0.6)), GOLD))
    parts.append((text, f, color))
    asc, desc = f.getmetrics()
    widths = [p[1].getlength(p[0]) for p in parts]
    pad = 8
    img = Image.new('RGBA', (int(sum(widths)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    x = pad
    for (s, ff, col), wd in zip(parts, widths):
        a2, _ = ff.getmetrics()
        dr.text((x, pad + asc - a2 - (0 if ff is f else -int(size * 0.08))), s, font=ff, fill=col + (255,))
        x += wd
    arr = np.asarray(img).astype(np.float32) / 255
    _tl[k] = (arr[..., :3].copy(), arr[..., 3].copy())
    return _tl[k]


def put_text(fr, text, font, size, color, cx, cy, a, rise=0.0, glow=0.0, scale=1.0, sym=None):
    rgb, al = text_layer(text, font, size, color, sym)
    put_layer(fr, rgb, al, cx, cy + rise, a, scale, glow)


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


# ---------------------------------------------------------------- scène 01 : le hook
S1 = dict(kicker=(205, 295, 140, 940), ton=(280, 392, 250, 830), nombre=(392, 535, 140, 940),
          rule=(612, 652, 80, 1000), sub=(672, 768, 150, 930), cta=(1392, 1548, 70, 1010))
B1 = corrected_base(VIS[0], FOND[0], list(S1.values()) + [(1590, 1835, 370, 710)])
M1 = matte_of(VIS[0], B1)


def scene1(lt):
    fr = B1.copy()
    appear(fr, VIS[0], S1['kicker'], lt, 0.12)
    for key, t0 in (('ton', 0.5), ('nombre', 0.72)):
        a = ramp(lt, t0, 0.45)
        put(fr, VIS[0], S1[key], a, scale=1.18 - 0.18 * a, matte=M1, glow=0.9 * max(0, 1 - (lt - t0) / 0.8) * a)
    appear(fr, VIS[0], S1['rule'], lt, 1.3, rise=0)
    appear(fr, VIS[0], S1['sub'], lt, 1.45)
    appear(fr, VIS[0], S1['cta'], lt, 2.0, rise=30)
    return kenburns(fr, 1.0 + 0.085 * ease(lt / 3.2), 330, 600)


# ---------------------------------------------------------------- scène 02 : le calcul
S2 = dict(title=(220, 300, 140, 940), sub=(350, 442, 160, 920), card=(498, 1258, 52, 1032),
          date=(595, 705, 90, 990), sum=(885, 1012, 300, 780), reduce=(1072, 1150, 230, 850),
          four=(1308, 1402, 380, 700), seven=(1418, 1568, 440, 640), cta=(1618, 1782, 70, 1010))
E2 = inpaint(VIS[1], [(585, 715, 80, 1000), (765, 1020, 80, 1000), (1065, 1155, 80, 1000)])
B2 = corrected_base(VIS[1], FOND[1], list(S2.values()))
U2 = B2.copy()
U2[498:1258, 52:1032] = E2[498:1258, 52:1032]
M2 = matte_of(VIS[1], U2)
# segments de la ligne « 1+7+0+9+1+9+8+8 », détectés colonne par colonne
_band = np.abs(VIS[1][775:872, 120:960] - E2[775:872, 120:960]).max(2) > 0.18
_cols = _band.any(0)
SEGS = []
x = 0
while x < len(_cols):
    if _cols[x]:
        s = x
        while x < len(_cols) and (_cols[x] or (x + 3 < len(_cols) and _cols[x:x + 4].any())):
            x += 1
        SEGS.append((120 + s, 120 + x))
    x += 1
DIGIT_T = [1.0 + 0.12 * i for i in range(len(SEGS))]


def scene2(lt):
    fr = B2.copy()
    appear(fr, VIS[1], S2['title'], lt, 0.0)
    appear(fr, VIS[1], S2['sub'], lt, 0.22)
    appear(fr, U2, S2['card'], lt, 0.42, rise=36, feather=6)
    appear(fr, VIS[1], S2['date'], lt, 0.7)
    for i, (sx0, sx1) in enumerate(SEGS):
        t0 = DIGIT_T[i]
        a = ramp(lt, t0, 0.18)
        is_digit = i % 2 == 0
        g = (1.6 * np.exp(-max(lt - t0, 0) / 0.35) * a) if is_digit else 0.0
        put(fr, VIS[1], (772, 875, sx0 - 5, sx1 + 5), a, dy=(1 - a) * 10, glow=g, matte=M2)
    a = ramp(lt, 2.9, 0.4)
    put(fr, VIS[1], S2['sum'], a, scale=1.25 - 0.25 * a, matte=M2, glow=1.0 * max(0, 1 - (lt - 2.9) / 0.7) * a)
    appear(fr, VIS[1], S2['reduce'], lt, 3.3)
    appear(fr, VIS[1], S2['four'], lt, 3.6)
    a = ramp(lt, 4.0, 0.45)
    put(fr, VIS[1], S2['seven'], a, scale=1.5 - 0.5 * a, matte=M2, glow=1.5 * max(0.25, 1 - (lt - 4.0) / 0.8) * a)
    appear(fr, VIS[1], S2['cta'], lt, 4.45, rise=30)
    return kenburns(fr, 1.0 + 0.03 * ease(lt / 5), 540, 900)


# ---------------------------------------------------------------- scène 03 : « et toi ? »
S3 = dict(title=(220, 318, 120, 960), circle=(410, 1205, 100, 980), ettoi=(1250, 1392, 300, 780),
          cta=(1455, 1615, 70, 1010), small=(1620, 1700, 200, 880))
SEVEN3 = (650, 990, 420, 670)
E3 = inpaint(VIS[2], [SEVEN3])
B3 = corrected_base(VIS[2], FOND[2], list(S3.values()) + [(1700, 1920, 0, 1080)])
U3 = B3.copy()
U3[410:1205, 100:980] = E3[410:1205, 100:980]
M3 = matte_of(VIS[2], U3)
_ys, _xs = np.nonzero(M3[SEVEN3[0]:SEVEN3[1], SEVEN3[2]:SEVEN3[3]] > 0.5)
C7 = (SEVEN3[2] + _xs.mean(), SEVEN3[0] + _ys.mean(), _ys.max() - _ys.min())


def question_layer():
    f = ImageFont.truetype(F_CG, 10)
    size = 10
    while True:
        f = ImageFont.truetype(F_CG, size)
        b = f.getbbox('?')
        if b[3] - b[1] >= C7[2] * 1.02:
            break
        size += 4
    img = Image.new('RGBA', (b[2] - b[0] + 20, b[3] - b[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 - b[0], 10 - b[1]), '?', font=f, fill=GOLD + (255,))
    arr = np.asarray(img).astype(np.float32) / 255
    return arr[..., :3].copy(), arr[..., 3].copy()


Q3 = question_layer()


def scene3(lt):
    fr = B3.copy()
    appear(fr, VIS[2], S3['title'], lt, 0.05)
    a = ramp(lt, 0.1, 0.4)
    put(fr, U3, S3['circle'], a, scale=0.92 + 0.08 * a, feather=8)
    # le 7 surgit…
    a7 = ramp(lt, 0.3, 0.35) * (1 - ramp(lt, 0.95, 0.3))
    s7 = (1.45 - 0.45 * ramp(lt, 0.3, 0.35)) + 0.25 * ramp(lt, 0.95, 0.3)
    put(fr, VIS[2], SEVEN3, a7, scale=s7, matte=M3, glow=1.2 * a7 * max(0.3, 1 - (lt - 0.3) / 0.6))
    # … puis devient « ? »
    aq = ramp(lt, 1.1, 0.4)
    put_layer(fr, Q3[0], Q3[1], C7[0], C7[1], aq, scale=0.7 + 0.3 * aq,
              glow=1.4 * aq * max(0.35, 1 - (lt - 1.1) / 0.8))
    a = ramp(lt, 1.25, 0.4)
    put(fr, VIS[2], S3['ettoi'], a, scale=1.2 - 0.2 * a, matte=M3)
    appear(fr, VIS[2], S3['cta'], lt, 1.7, rise=30)
    appear(fr, VIS[2], S3['small'], lt, 2.05)
    return kenburns(fr, 1.0 + 0.03 * ease(lt / 3), 540, 800)


# ---------------------------------------------------------------- scène 04 : la symbolique
S4 = dict(title=(148, 348, 160, 920), sub=(382, 462, 250, 830), masters=(1448, 1532, 250, 830),
          cta=(1582, 1722, 70, 1010))
TILES = [(y0 - 6, y1 + 6, x0 - 6, min(x1 + 6, 1080)) for (y0, y1) in ((550, 795), (810, 1055), (1070, 1315))
         for (x0, x1) in ((108, 415), (438, 745), (768, 1075))]
B4 = corrected_base(VIS[3], FOND[3], list(S4.values()) + TILES)


def scene4(lt):
    fr = B4.copy()
    appear(fr, VIS[3], S4['title'], lt, 0.05)
    appear(fr, VIS[3], S4['sub'], lt, 0.3)
    put_text(fr, 'Numérologie : interprétation symbolique, non scientifique', F_CGI, 34, CREAM,
             540, 505, 0.85 * ramp(lt, 0.45, 0.4))
    for i, r in enumerate(TILES):
        t0 = 0.7 + 0.22 * i
        a = ramp(lt, t0, 0.3)
        g = 0.9 * np.exp(-max(lt - t0, 0) / 0.35) * a
        if i == 6:  # le 7 de l'exemple se rallume
            g += 0.9 * np.exp(-((lt - 3.1) / 0.3) ** 2)
        put(fr, VIS[3], r, a, scale=0.9 + 0.1 * a, glow=g, feather=5)
    appear(fr, VIS[3], S4['masters'], lt, 2.8)
    appear(fr, VIS[3], S4['cta'], lt, 3.1, rise=30)
    return kenburns(fr, 1.0 + 0.03 * ease(lt / 4), 540, 930)


# ---------------------------------------------------------------- scène 05 : partage
S5 = dict(title=(145, 352, 130, 950), sub=(440, 545, 200, 880), card=(590, 1340, 140, 950),
          share=(1395, 1482, 200, 880), avec=(1478, 1558, 200, 880), cta=(1605, 1765, 70, 1010))
BUBBLES = [(780, 882, 212, 667), (905, 1007, 418, 868), (1028, 1132, 212, 667)]
E5 = inpaint(VIS[4], [(772, 1142, 190, 890)])
B5 = corrected_base(VIS[4], FOND[4], list(S5.values()))
U5 = B5.copy()
U5[590:1340, 140:950] = E5[590:1340, 140:950]


def scene5(lt):
    fr = B5.copy()
    appear(fr, VIS[4], S5['title'], lt, 0.03)
    appear(fr, VIS[4], S5['sub'], lt, 0.25)
    appear(fr, U5, S5['card'], lt, 0.4, rise=36, feather=6)
    for i, r in enumerate(BUBBLES):
        t0 = 0.75 + 0.3 * i
        a = ramp(lt, t0, 0.28)
        put(fr, VIS[4], r, a, dy=(1 - a) * 26, scale=0.86 + 0.14 * a, feather=4)
    appear(fr, VIS[4], S5['share'], lt, 1.7)
    appear(fr, VIS[4], S5['avec'], lt, 1.85)
    a = ramp(lt, 2.1, 0.35)
    put(fr, VIS[4], S5['cta'], a, dy=(1 - a) * 30, glow=0.5 * np.exp(-((lt - 2.6) / 0.25) ** 2))
    return kenburns(fr, 1.0 + 0.03 * ease(lt / 3), 540, 900)


# ---------------------------------------------------------------- scène 06 : la rupture, les racines
S6 = dict(t1=(175, 272, 180, 900), t2=(262, 352, 140, 940), rule=(438, 482, 90, 1000), box=(1385, 1650, 70, 1010))
B6 = corrected_base(VIS[5], FOND[5], list(S6.values()))
M6 = matte_of(VIS[5], B6)
L6 = B6.mean(2)
L6 = (L6 - L6.min()) / (L6.max() - L6.min())


def scene6(lt):
    if lt < 0.3:  # le bruit est coupé : noir
        return np.zeros((H, W, 3), np.float32)
    u = ease((lt - 0.3) / 1.9)
    thr = 1.05 - 1.25 * u  # la lumière gagne d'abord les branches, puis les portraits
    al = np.clip((L6 - thr) / 0.18, 0, 1)
    al = np.maximum(al, 0.08 * ease((lt - 0.3) / 0.5))
    fr = B6 * al[..., None]
    appear(fr, VIS[5], S6['t1'], lt, 0.7, matte=M6)
    appear(fr, VIS[5], S6['t2'], lt, 1.1, matte=M6)
    appear(fr, VIS[5], S6['rule'], lt, 1.5, rise=0, matte=M6)
    appear(fr, VIS[5], S6['box'], lt, 2.3, rise=36, feather=6)
    return kenburns(fr, 1.0 + 0.08 * ease(lt / 4), 540, 760, dy=-20 * ease(lt / 4))


# ---------------------------------------------------------------- scène 07 : RACINE (moment produit)
S7 = dict(kicker=(128, 200, 220, 860), racine=(195, 350, 200, 880), arbre=(435, 522, 180, 900),
          inter=(500, 600, 260, 820), frame=(640, 1314, 85, 995))
B7 = corrected_base(VIS[6], FOND[6], list(S7.values()) + [(1300, 1700, 100, 980)])
M7 = matte_of(VIS[6], B7)
BG7B = np.clip(cv2.GaussianBlur(B7, (0, 0), 18) * 0.42, 0, 1)
R0 = (112, 664, 968, 1290)       # vignette de l'interface dans le visuel 07 (x0, y0, x1, y1)
R1 = (40, 400, 1040, 1320)       # panneau plein cadre
CH, CW = CAPTURE.shape[:2]
CROP0 = (CW - CH * (R0[2] - R0[0]) / (R0[3] - R0[1])) / 2, CH * (R0[2] - R0[0]) / (R0[3] - R0[1])
CROP1W = CH * (R1[2] - R1[0]) / (R1[3] - R1[1])
PAN_MAX = CW - CROP1W
BULLETS = [('Explore les générations', 2.9, 4.0), ('Ouvre les fiches de tes proches', 4.0, 5.0),
           ('Relie les portraits et les souvenirs', 5.0, 6.2)]
TAPS = [((196, 540), 3.25), ((1170, 512), 4.9)]


def pan_x(lt):
    return PAN_MAX * ease((lt - 2.9) / 2.4)


def draw_panel(fr, rect, crop, a):
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    cx, cw = crop
    cx = min(max(cx, 0), CW - cw)
    src = CAPTURE[:, int(round(cx)):int(round(cx + cw))]
    w, h = x1 - x0, y1 - y0
    img = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
    m = rounded_mask(h, w, 20) * a
    # ombre portée
    sh = np.zeros((H, W), np.float32)
    sh[y0 + 14:y1 + 14, x0:x1] = m
    sh = cv2.GaussianBlur(sh, (0, 0), 22) * 0.75
    fr[:] = fr * (1 - sh[..., None])
    reg = fr[y0:y1, x0:x1]
    reg[:] = reg * (1 - m[..., None]) + img * m[..., None]
    gold_border(fr, x0, y0, x1 - 1, y1 - 1, 20, a, 3)
    return cx


def scene7(lt):
    # 7a : annonce RACINE sur le décor, léger travelling vertical
    fa = B7.copy()
    appear(fa, VIS[6], S7['kicker'], lt, 0.08)
    a = ramp(lt, 0.3, 0.45)
    put(fa, VIS[6], S7['racine'], a, scale=1.22 - 0.22 * a, matte=M7, glow=1.1 * a * max(0.2, 1 - (lt - 0.3) / 0.9))
    appear(fa, VIS[6], S7['arbre'], lt, 0.7)
    appear(fa, VIS[6], S7['inter'], lt, 0.85)
    appear(fa, VIS[6], S7['frame'], lt, 1.1, rise=40, feather=6)
    fa = kenburns(fa, 1.03, 540, 900, dy=24 - 40 * ease(lt / 2.2))
    if lt < 1.95:
        return fa
    # 7b : transition vers la vraie interface, puis travelling dans l'arbre
    u = ease((lt - 2.0) / 0.7)
    fr = fa * (1 - u) + BG7B * u
    rect = [R0[i] + (R1[i] - R0[i]) * u for i in range(4)]
    crop = (CROP0[0] * (1 - u) + pan_x(lt) * u, CROP0[1] * (1 - u) + CROP1W * u)
    draw_panel(fr, rect, crop, ramp(lt, 1.95, 0.15))
    a = ramp(lt, 2.45, 0.45)
    put_text(fr, 'RACINE', F_CG, 132, GOLD, 540, 215, a, rise=(1 - a) * 20, glow=0.6 * a)
    put_text(fr, 'l’arbre généalogique interactif d’ORIGIN', F_CGI, 48, CREAM, 540, 330, ramp(lt, 2.65, 0.45))
    if lt >= 2.7:
        a = ramp(lt, 2.7, 0.4)
        ov = fr.copy()
        cv2.rectangle(ov, (R1[2] - 420, R1[3] - 48), (R1[2] - 8, R1[3] - 6), (0.03, 0.025, 0.02), -1)
        fr[:] = fr * (1 - 0.8 * a) + ov * 0.8 * a
        put_text(fr, 'Démonstration · personnes fictives', F_OSS, 22, CREAM, R1[2] - 214, R1[3] - 27, 0.85 * a)
        s = (R1[3] - R1[1]) / CH
        for (px, py), t0 in TAPS:
            k = (lt - t0) / 0.7
            if 0 <= k <= 1:
                sx, sy = R1[0] + (px - pan_x(lt)) * s, R1[1] + py * s
                ov = fr.copy()
                cv2.circle(ov, (int(sx), int(sy)), int(18 + 70 * eout(k)), (1, 0.93, 0.8), 4, cv2.LINE_AA)
                cv2.circle(ov, (int(sx), int(sy)), 16, (1, 0.93, 0.8), -1, cv2.LINE_AA)
                aa = 0.85 * (1 - k)
                fr[:] = fr * (1 - aa) + ov * aa
        for text, t0, t1 in BULLETS:
            a = ramp(lt, t0, 0.3) * (1 - ramp(lt, t1 - 0.2, 0.2) if t1 < 6 else 1)
            put_text(fr, text, F_CGM, 54, CREAM, 540, 1385, a, rise=(1 - ramp(lt, t0, 0.3)) * 18, sym='✦')
    fade = 1 - ease((lt - 5.75) / 0.25)
    return fr * fade


# ---------------------------------------------------------------- scène 08 : signature, logo officiel
LOGO_C = (345.0, 752.0)  # centre de l'emblème dans le fichier logo fourni


def logo_frame(scale, cy):
    M = np.float32([[scale, 0, 540 - LOGO_C[0] * scale], [0, scale, cy - LOGO_C[1] * scale]])
    fr = cv2.warpAffine(LOGO, M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # fondu des bords latéraux de l'image fournie vers le noir
    lw = LOGO.shape[1] * scale
    x0 = 540 - LOGO_C[0] * scale
    xs = np.arange(W, dtype=np.float32)
    edge = np.clip(np.minimum(xs - x0, x0 + lw - xs) / 30, 0, 1)
    return fr * edge[None, :, None]


def scene8(lt):
    u = ease(lt / 1.3)
    fr = logo_frame(1.62 - 0.22 * u, 960 - 80 * u) * ease(lt / 0.45)
    a = ramp(lt, 0.9, 0.45)
    put_text(fr, 'CE N’ÉTAIT', F_CG, 80, CREAM, 540, 190, a, rise=(1 - a) * 20)
    a = ramp(lt, 1.1, 0.45)
    put_text(fr, 'QUE LE DÉBUT.', F_CG, 104, GOLD, 540, 290, a, rise=(1 - a) * 20, glow=0.5 * a)
    a = ramp(lt, 1.6, 0.4)
    put_text(fr, 'Chez ORIGIN, bien d’autres calculs', F_CGM, 52, CREAM, 540, 1290, a, rise=(1 - a) * 16)
    put_text(fr, 'sont réalisés pour toi.', F_CGM, 52, CREAM, 540, 1352, a, rise=(1 - a) * 16)
    a = ramp(lt, 2.3, 0.4)
    put_text(fr, 'Avec RACINE, découvre ton histoire familiale.', F_CGI, 44, GOLD, 540, 1425, a, rise=(1 - a) * 16)
    a = ramp(lt, 2.8, 0.4)
    if a > 0:
        ov = fr.copy()
        m = rounded_mask(84, 640, 42)
        reg = ov[1478:1562, 220:860]
        reg[:] = reg * (1 - m[..., None] * 0.7) + np.array([0.04, 0.035, 0.03]) * m[..., None] * 0.7
        gold_border(ov, 220, 1478, 859, 1561, 41, 1.0, 2)
        fr[:] = fr * (1 - a) + ov * a
        put_text(fr, 'DÉCOUVRE ORIGIN', F_OSB, 38, GOLD, 540, 1519, a, glow=0.35 * np.exp(-((lt - 3.4) / 0.3) ** 2))
        put_text(fr, 'Numérologie : interprétation symbolique, non scientifique', F_CGI, 28, CREAM, 540, 1605, 0.7 * a)
    return fr


# ---------------------------------------------------------------- montage
SCENES = [(0.0, 3.0, scene1), (3.0, 8.0, scene2), (8.0, 11.0, scene3), (11.0, 15.0, scene4),
          (15.0, 18.0, scene5), (18.0, 22.0, scene6), (22.0, 28.0, scene7), (28.0, 32.0, scene8)]
PUSH = 0.42  # transitions « par mouvement » 01→05


def motion_blur_v(fr, k):
    k = int(k)
    return fr if k < 3 else cv2.blur(fr, (1, k))


def compose(t):
    for i, (s, e, fn) in enumerate(SCENES):
        if s <= t < e or (i == len(SCENES) - 1 and t >= s):
            idx = i
            break
    s, e, fn = SCENES[idx]
    # poussée verticale avec flou de bougé aux frontières 3, 8, 11, 15 s
    for b in (3.0, 8.0, 11.0, 15.0):
        if b - PUSH / 2 <= t < b + PUSH / 2:
            k = (t - (b - PUSH / 2)) / PUSH
            u = ease(k)
            ia = [j for j, sc in enumerate(SCENES) if sc[1] == b][0]
            fa = SCENES[ia][2](t - SCENES[ia][0])
            fb = SCENES[ia + 1][2](max(t - b, 0))
            off = int(round(u * H))
            out = np.empty_like(fa)
            out[:H - off] = fa[off:]
            out[H - off:] = fb[:off]
            speed = np.sin(np.pi * k)
            return motion_blur_v(out, 90 * speed)
    if 22.0 - 0.3 <= t < 22.0:  # 06 → 07 : fondu zoomé
        k = ease((t - 21.7) / 0.3)
        fa = kenburns(scene6(t - 18.0), 1 + 0.08 * k, 540, 800)
        fb = scene7(0.0)
        return fa * (1 - k) + fb * k
    return fn(t - s)


# ---------------------------------------------------------------- sous-titres (voix off)
SUBS = [  # (début, fin, texte, incrusté ?, y centre)
    (0.0, 1.7, 'Ta date de naissance cache un nombre.', True, 1180),
    (1.7, 3.0, 'Tu connais le tien ?', True, 1180),
    (3.0, 4.3, 'Additionne tous les chiffres.', True, 1280),
    (4.3, 5.9, 'Exemple : 17 septembre 1988…', True, 1280),
    (5.9, 8.0, '43, puis 4 + 3 : 7.', True, 1280),
    (8.0, 9.2, 'Et toi ?', True, 1226),
    (9.2, 11.0, 'Mets ton nombre en commentaire.', True, 1226),
    (11.0, 13.0, 'Chaque nombre possède une interprétation', True, 1380),
    (13.0, 15.0, 'symbolique en numérologie.', True, 1380),
    (15.0, 16.1, 'Envoie la vidéo à ton partenaire,', True, 1368),
    (16.1, 17.2, 'à un ami, à quelqu’un de ta famille.', True, 1368),
    (17.2, 18.0, 'Comparez !', True, 1368),
    (18.4, 19.8, 'Mais un nombre ne raconte pas', True, 1300),
    (19.8, 20.9, 'toute une histoire…', True, 1300),
    (20.9, 22.0, 'Et tes racines ?', True, 1300),
    (22.0, 23.0, 'Découvre RACINE :', True, 1362),
    (23.0, 24.6, 'l’arbre généalogique interactif d’ORIGIN.', True, 1362),
    (24.6, 26.2, 'Explore les générations,', False, 0),
    (26.2, 28.0, 'leurs fiches et leurs liens.', False, 0),
    (28.0, 30.0, 'Chez ORIGIN, bien d’autres calculs sont réalisés pour toi.', False, 0),
    (30.0, 32.0, 'Et avec RACINE, découvre ton histoire familiale.', False, 0),
]
_pill = {}


def pill_layer(text):
    if text in _pill:
        return _pill[text]
    size = 38
    while ImageFont.truetype(F_OSS, size).getlength(text) > 780:
        size -= 1
    f = ImageFont.truetype(F_OSS, size)
    tw = int(f.getlength(text))
    ph, pw = 56, tw + 48
    img = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=28, fill=(8, 6, 4, 165))
    dr.text((pw / 2, ph / 2), text, font=f, fill=CREAM + (255,), anchor='mm')
    arr = np.asarray(img).astype(np.float32) / 255
    _pill[text] = (arr[..., :3].copy(), arr[..., 3].copy())
    return _pill[text]


def add_subs(fr, t):
    for s, e, text, burn, y in SUBS:
        if burn and s <= t < e:
            a = min(clamp01((t - s) / 0.12), clamp01((e - t) / 0.12)) if e - s > 0.3 else 1
            if s in (3.0, 8.0, 11.0, 15.0, 22.0) or e in (3.0, 8.0, 11.0, 15.0, 18.0):
                a = 1.0 if s <= t < e else 0  # pas de fondu en bord de transition : coupe franche
                if abs(t - s) < PUSH / 2 and s in (3.0, 8.0, 11.0, 15.0):
                    a = clamp01((t - s) / (PUSH / 2))
                if abs(e - t) < PUSH / 2 and e in (3.0, 8.0, 11.0, 15.0):
                    a = clamp01((e - t) / (PUSH / 2))
            rgb, al = pill_layer(text)
            put_layer(fr, rgb, al, 540, y, a)
    return fr


def srt_time(x):
    ms = int(round(x * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def write_srt(path):
    with open(path, 'w', encoding='utf-8') as f:
        for i, (s, e, text, _, _) in enumerate(SUBS, 1):
            f.write(f'{i}\n{srt_time(s)} --> {srt_time(e)}\n{text}\n\n')


def to_u8(fr):
    return (np.clip(fr, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    print('segments ligne de calcul :', len(SEGS), 'centre du 7 :', [round(v) for v in C7])
    if PREVIEW:
        tiles = []
        for t in PREVIEW:
            fr = add_subs(compose(t), t)
            im = Image.fromarray(to_u8(fr)).resize((360, 640))
            ImageDraw.Draw(im).text((8, 8), f'{t:.2f}s', fill=(0, 255, 255))
            tiles.append(im)
        cols = min(len(tiles), 6)
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 360, rows * 640))
        for i, im in enumerate(tiles):
            sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
        sheet.save(f'{OUT}/preview.jpg', quality=90)
        sys.exit(0)

    write_srt(f'{OUT}/ORIGIN_TikTok_voix_off.srt')
    enc = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
           '-r', str(FPS), '-movflags', '+faststart']
    raw = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-']
    p_clean = subprocess.Popen(raw + enc + [f'{OUT}/_video_clean.mp4'], stdin=subprocess.PIPE)
    p_subs = subprocess.Popen(raw + enc + [f'{OUT}/_video_subs.mp4'], stdin=subprocess.PIPE)
    for n in range(NF):
        t = n / FPS
        fr = compose(t)
        p_clean.stdin.write(to_u8(fr).tobytes())
        p_subs.stdin.write(to_u8(add_subs(fr.copy(), t)).tobytes())
        if n % 60 == 0:
            print(f'{t:5.1f}s', flush=True)
    for p in (p_clean, p_subs):
        p.stdin.close()
        p.wait()
    print('ok')
