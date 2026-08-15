#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORIGIN — Serveur webhook
Reçoit les données Formspree → génère le livret → envoie par email
"""

from flask import Flask, request, jsonify
import os, json, re, requests, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, date
import ephem as sw
import pytz, math
from pathlib import Path

# Timezones par pays (évite timezonefinder qui ne compile pas sur Render)
TIMEZONE_MAP = {
    'france': 'Europe/Paris', 'fr': 'Europe/Paris',
    'belgique': 'Europe/Brussels', 'suisse': 'Europe/Zurich',
    'canada': 'America/Montreal', 'maroc': 'Africa/Casablanca',
    'espagne': 'Europe/Madrid', 'italie': 'Europe/Rome',
    'default': 'Europe/Paris'
}

def get_timezone(ville):
    ville_lower = ville.lower()
    for k, v in TIMEZONE_MAP.items():
        if k in ville_lower:
            return v
    return 'Europe/Paris'  # défaut France

app = Flask(__name__)

# ── CONFIG (variables d'environnement Render)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GMAIL_USER        = os.environ.get("GMAIL_USER", "")
GMAIL_PASS        = os.environ.get("GMAIL_PASS", "")
EMAIL_DEST        = os.environ.get("EMAIL_DEST", "")
FORMSPREE_SECRET  = os.environ.get("FORMSPREE_SECRET", "")

# ════════════════════════════════════════════════════
# NUMÉROLOGIE
# ════════════════════════════════════════════════════

MAITRES = {11, 22, 33}
SIGNES = ['Bélier','Taureau','Gémeaux','Cancer','Lion','Vierge',
          'Balance','Scorpion','Sagittaire','Capricorne','Verseau','Poissons']

def reduire(n):
    while n > 9 and n not in MAITRES:
        n = sum(int(d) for d in str(n))
    return n

def chemin_de_vie(j, m, a):
    return reduire(sum(int(d) for d in f"{j:02d}{m:02d}{a}"))

def expression(prenom, nom=""):
    T = {'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,'I':9,
         'J':1,'K':2,'L':3,'M':4,'N':5,'O':6,'P':7,'Q':8,'R':9,
         'S':1,'T':2,'U':3,'V':4,'W':5,'X':6,'Y':7,'Z':8}
    return reduire(sum(T.get(c.upper(),0) for c in prenom+nom if c.isalpha()))

def intime(prenom, nom=""):
    T = {'A':1,'E':5,'I':9,'O':6,'U':3,'Y':7}
    return reduire(sum(T.get(c.upper(),0) for c in prenom+nom if c.isalpha()))

def realisation(prenom, nom=""):
    V = set('AEIOUY')
    T = {'B':2,'C':3,'D':4,'F':6,'G':7,'H':8,'J':1,'K':2,'L':3,'M':4,
         'N':5,'P':7,'Q':8,'R':9,'S':1,'T':2,'V':4,'W':5,'X':6,'Z':8}
    return reduire(sum(T.get(c.upper(),0) for c in prenom+nom if c.isalpha() and c.upper() not in V))

def annee_perso(j, m):
    return reduire(sum(int(d) for d in f"{j:02d}{m:02d}{date.today().year}"))

def label_nombre(n):
    noms = {11:"Maître Inspirateur", 22:"Maître Bâtisseur", 33:"Maître Enseignant"}
    return f"{n} ({noms[n]})" if n in noms else str(n)

# ════════════════════════════════════════════════════
# COORDONNÉES VILLES
# ════════════════════════════════════════════════════

VILLES_FR = {
    "paris":(48.8566,2.3522),"marseille":(43.2965,5.3698),"lyon":(45.7640,4.8357),
    "nice":(43.7102,7.2620),"toulouse":(43.6047,1.4442),"bordeaux":(44.8378,-0.5792),
    "nantes":(47.2184,-1.5536),"strasbourg":(48.5734,7.7521),"montpellier":(43.6108,3.8767),
    "toulon":(43.1242,5.9280),"cannes":(43.5528,7.0174),"aix-en-provence":(43.5297,5.4474),
    "saint-tropez":(43.2727,6.6408),"draguignan":(43.5377,6.4650),
    "brignoles":(43.4046,6.0606),"carcès":(43.4781,6.1770),"cotignac":(43.5511,6.1539),
    "var":(43.4667,6.2167),"antibes":(43.5804,7.1283),"grasse":(43.6585,6.9259),
    "avignon":(43.9493,4.8055),"arles":(43.6767,4.6278),"nimes":(43.8367,4.3601),
}

def get_coords(ville):
    key = ville.lower().strip().replace("saint ","saint-")
    if key in VILLES_FR:
        return VILLES_FR[key]
    for k, v in VILLES_FR.items():
        if k in key or key in k:
            return v
    return 43.2965, 5.3698  # fallback Marseille

# ════════════════════════════════════════════════════
# ASTROLOGIE
# ════════════════════════════════════════════════════

CORPS_EPHEM = {
    'Soleil': sw.Sun, 'Lune': sw.Moon, 'Mercure': sw.Mercury,
    'Vénus': sw.Venus, 'Mars': sw.Mars, 'Jupiter': sw.Jupiter,
    'Saturne': sw.Saturn, 'Uranus': sw.Uranus, 'Neptune': sw.Neptune,
}

def deg_signe(deg):
    deg = deg % 360
    return SIGNES[int(deg//30)], round(deg%30, 1)

def calc_theme(j, m, a, ville, heure=None, minute=0, asc_force=None):
    lat, lon = get_coords(ville)
    h = heure if heure is not None else 12
    try:
        dt = datetime(a, m, j, h, minute)
        tz_name = get_timezone(ville)
        offset = pytz.timezone(tz_name).localize(dt).utcoffset().total_seconds()/3600
    except Exception:
        offset = 1.0
    heure_utc = h + minute/60 - offset
    obs = sw.Observer()
    obs.lat = str(lat); obs.lon = str(lon)
    obs.date = f"{a}/{m}/{j} {heure_utc:.4f}"
    planetes = {}
    for nom, cls in CORPS_EPHEM.items():
        try:
            p = cls(obs)
            lon_deg = math.degrees(float(p.hlong))
            if nom == 'Soleil':
                lon_deg = (lon_deg + 180) % 360
            else:
                lon_deg = lon_deg % 360
            s, d = deg_signe(lon_deg)
            planetes[nom] = {'signe':s,'degre':d}
        except Exception:
            planetes[nom] = {'signe':'?','degre':0}
    asc_data = {'signe': asc_force, 'degre': None} if asc_force else None
    return {'planetes':planetes,'ascendant':asc_data}

def fmt_profil(p):
    j,m,a = p['jour'],p['mois'],p['annee']
    pr,nm = p['prenom'],p.get('nom','')
    num = {
        'cdv': chemin_de_vie(j,m,a),
        'expr': expression(pr,nm),
        'intime': intime(pr,nm),
        'real': realisation(pr,nm),
        'ap': annee_perso(j,m),
    }
    astro = calc_theme(j,m,a,p.get('ville','Marseille'),p.get('heure'),p.get('minute',0),p.get('asc_force'))
    heure_str = f"{p['heure']:02d}h{p.get('minute',0):02d}" if p.get('heure') is not None else "heure inconnue"
    lines = [
        f"PROFIL : {pr} {nm}",
        f"Né(e) le {j:02d}/{m:02d}/{a} à {p.get('ville','')} ({heure_str})",
        "",
        "NUMÉROLOGIE",
        f"  Chemin de vie : {label_nombre(num['cdv'])}",
        f"  Expression    : {label_nombre(num['expr'])}",
        f"  Intime        : {label_nombre(num['intime'])}",
        f"  Réalisation   : {label_nombre(num['real'])}",
        f"  Année perso   : {num['ap']}",
        "",
        "ASTROLOGIE",
    ]
    for np, d in astro['planetes'].items():
        lines.append(f"  {np:<10}: {d['signe']} {d['degre']}°")
    if astro['ascendant']:
        asc = astro['ascendant']
        deg_str = f" {asc['degre']}°" if asc['degre'] else ""
        lines.append(f"  Ascendant  : {asc['signe']}{deg_str}")
    return "\n".join(lines), num, astro

# ════════════════════════════════════════════════════
# APPEL CLAUDE
# ════════════════════════════════════════════════════

def appeler_claude(offre, profils_txt):
    structures = {
        'solo': """
1. LETTRE D'OUVERTURE (4-5 paragraphes, tutoiement, profond)
2. PORTRAIT NUMÉROLOGIQUE (8-10 paragraphes narratifs)
3. PORTRAIT ASTROLOGIQUE (8-10 paragraphes narratifs)
4. FORCES NATURELLES (5 items en prose narrative)
5. ZONES DE CROISSANCE (4 items en prose narrative)
6. OMBRES → LUMIÈRES (3 transformations : situation concrète + lumière + phrase à dire)
7. MANTRA PERSONNEL
8. MESSAGE FINAL (3-4 paragraphes)""",
        'couple': """
1. LETTRE D'OUVERTURE (4-5 paragraphes, aux deux prénoms, tutoiement)
2. SIGNATURES NUMÉRIQUES (2-3 paragraphes sur les nombres clés ensemble)
3. PORTRAIT INDIVIDUEL 1 (10-12 paragraphes, numérologie + astrologie entremêlées)
4. PORTRAIT INDIVIDUEL 2 (10-12 paragraphes)
5. CE QUE VOUS CRÉEZ ENSEMBLE (7-8 paragraphes, résonances croisées précises)
6. CE QUE VOUS VOUS APPORTEZ (4 paragraphes, dons mutuels)
7. OMBRES → LUMIÈRES (4 tensions avec situation + lumière + phrase à dire)
8. MANTRAS (3 : un par personne + un commun, avec note)
9. MESSAGE FINAL (4 paragraphes)""",
        'famille': """
1. LETTRE D'OUVERTURE (4-5 paragraphes)
2. PORTRAIT DE CHAQUE MEMBRE (6-8 paragraphes chacun)
3. DYNAMIQUE FAMILIALE (6-8 paragraphes)
4. HÉRITAGES TRANSMIS (4 paragraphes)
5. OMBRES → LUMIÈRES (4 tensions familiales)
6. MANTRAS (un par membre + un commun)
7. MESSAGE FINAL (4 paragraphes)""",
    }
    structure = structures.get(offre, structures['couple'])

    prompt = f"""Tu es le moteur narratif d'ORIGIN, service de lecture personnalisée (numérologie + astrologie + transgénérationnel).

STYLE OBLIGATOIRE :
- Tutoiement systématique, chaleureux, direct
- Tout en prose narrative — zéro liste à puces dans le contenu
- Profond, immersif, le client doit sentir qu'on a passé des heures sur son cas
- Utilise les prénoms régulièrement
- Chaque paragraphe apporte quelque chose de nouveau
- Nomme des situations concrètes et vécues
- Ton bienveillant mais direct sur les zones d'ombre

DONNÉES :
{profils_txt}

STRUCTURE :
{structure}

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{{
  "lettre": "<p>...</p>",
  "sections": [
    {{"titre": "...", "eyebrow": "...", "contenu": "<p>...</p><p>...</p>"}},
    ...
  ],
  "mantras": [
    {{"prenom": "...", "texte": "...", "note": "..."}},
    ...
  ],
  "message_final": "<p>...</p>"
}}"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 8000, "messages": [{"role":"user","content":prompt}]},
        timeout=180
    )
    r.raise_for_status()
    raw = r.json()['content'][0]['text']
    raw = re.sub(r'^```json\s*','',raw.strip())
    raw = re.sub(r'```$','',raw.strip())
    return json.loads(raw)

# ════════════════════════════════════════════════════
# GÉNÉRATION HTML
# ════════════════════════════════════════════════════

CSS = """
:root{--noir:#090907;--encre:#111109;--or:#C9A84C;--or-clair:#E8C97A;--cuivre:#B97333;--creme:#F2ECD8;--muted:#9E9478;--dim:#5A5340;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{background:var(--noir);color:var(--creme);font-family:'Cormorant Garamond',serif;font-weight:300;overflow-x:hidden;}
.cover{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;overflow:hidden;padding:4rem 2rem;text-align:center;}
.cover-bg{position:absolute;inset:0;background:radial-gradient(ellipse 70% 60% at 50% 40%,rgba(185,115,51,.12) 0%,transparent 65%);}
.particles{position:absolute;inset:0;pointer-events:none;}
.particle{position:absolute;width:2px;height:2px;background:var(--or);border-radius:50%;opacity:0;animation:pf var(--dur) var(--delay) ease-in-out infinite;}
@keyframes pf{0%{opacity:0;transform:translateY(0) scale(0)}20%{opacity:.8}80%{opacity:.4}100%{opacity:0;transform:translateY(-120px) scale(1.5)}}
.cover-content{position:relative;z-index:2;max-width:680px;margin:0 auto;}
.cover-eyebrow{font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.55em;text-transform:uppercase;color:var(--cuivre);margin-bottom:2.5rem;}
.seed-wrap{width:130px;height:130px;margin:0 auto 2.5rem;position:relative;}
.seed-svg{width:100%;height:100%;animation:sr 60s linear infinite;filter:drop-shadow(0 0 18px rgba(201,168,76,.45));}
@keyframes sr{to{transform:rotate(360deg)}}
.seed-pulse{position:absolute;inset:-18px;border-radius:50%;border:1px solid rgba(201,168,76,.15);animation:pr 3s ease-in-out infinite;}
.seed-pulse:nth-child(2){inset:-32px;animation-delay:1s;border-color:rgba(201,168,76,.08);}
@keyframes pr{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.05);opacity:.5}}
.cover-title{font-family:'Cinzel',serif;font-size:clamp(2.2rem,6vw,3.8rem);font-weight:400;letter-spacing:.12em;color:var(--or-clair);margin-bottom:1rem;animation:tg 6s ease-in-out infinite;}
@keyframes tg{0%,100%{text-shadow:0 0 40px rgba(232,201,122,.2)}50%{text-shadow:0 0 80px rgba(232,201,122,.5)}}
.cover-names{font-family:'Cormorant Garamond',serif;font-size:clamp(1.5rem,4vw,2.2rem);font-style:italic;color:var(--creme);margin-bottom:.6rem;}
.cover-amp{color:var(--or);font-style:normal;margin:0 .5rem;}
.cover-tagline{font-size:1rem;color:var(--muted);font-style:italic;margin-bottom:3rem;line-height:1.65;}
.cover-ligne{width:80px;height:1px;background:linear-gradient(to right,transparent,var(--or),transparent);margin:0 auto 1.8rem;}
.cover-meta{font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.3em;text-transform:uppercase;color:var(--dim);}
.nav-dots{position:fixed;right:1.8rem;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:.7rem;z-index:100;}
.nav-dot{width:6px;height:6px;border-radius:50%;background:rgba(201,168,76,.25);cursor:pointer;transition:all .3s;}
.nav-dot.active,.nav-dot:hover{background:var(--or);box-shadow:0 0 8px rgba(201,168,76,.6);transform:scale(1.4);}
.section{max-width:820px;margin:0 auto;padding:6rem 2.5rem;}
.section-sep{border-top:1px solid rgba(201,168,76,.08);}
.s-eyebrow{font-family:'Jost',sans-serif;font-size:.58rem;letter-spacing:.5em;text-transform:uppercase;color:var(--cuivre);margin-bottom:1rem;display:block;}
.s-title{font-family:'Cinzel',serif;font-size:clamp(1.5rem,3.5vw,2.2rem);font-weight:400;color:var(--or-clair);margin-bottom:2.5rem;letter-spacing:.06em;line-height:1.3;}
.s-title-center{text-align:center;}
.prose{font-size:clamp(1rem,1.8vw,1.12rem);line-height:1.95;color:var(--creme);font-weight:300;}
.prose p{margin-bottom:1.7rem;}
.prose em{color:var(--or-clair);font-style:italic;}
.lettre{background:rgba(201,168,76,.03);border:1px solid rgba(201,168,76,.12);border-left:3px solid var(--cuivre);padding:2.8rem 3rem;position:relative;}
.lettre-signature{margin-top:2rem;font-size:.85rem;letter-spacing:.2em;color:var(--cuivre);font-family:'Cinzel',serif;}
.ornament{display:flex;align-items:center;gap:1.2rem;margin:3rem 0;opacity:.4;}
.ornament-line{flex:1;height:1px;background:linear-gradient(to right,transparent,var(--or));}
.ornament-line:last-child{background:linear-gradient(to left,transparent,var(--or));}
.ornament-symbol{color:var(--or);font-size:1rem;}
.mantra-wrap{text-align:center;padding:3.5rem 2rem;position:relative;}
.mantra-bg{position:absolute;inset:0;background:radial-gradient(ellipse 60% 60% at 50% 50%,rgba(185,115,51,.07) 0%,transparent 70%);pointer-events:none;}
.mantra-prenom{font-family:'Cinzel',serif;font-size:.62rem;letter-spacing:.45em;color:var(--cuivre);margin-bottom:1.5rem;position:relative;z-index:1;}
.mantra-txt{font-family:'Cinzel',serif;font-size:clamp(1.1rem,2.5vw,1.5rem);font-weight:400;color:var(--or-clair);line-height:1.7;position:relative;z-index:1;}
.mantra-note{margin-top:1rem;font-size:.9rem;color:var(--dim);font-style:italic;position:relative;z-index:1;}
.final-wrap{min-height:50vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:6rem 2rem;position:relative;}
.final-glow{position:absolute;inset:0;background:radial-gradient(ellipse 50% 50% at 50% 50%,rgba(185,115,51,.1) 0%,transparent 70%);animation:fb 6s ease-in-out infinite;}
@keyframes fb{0%,100%{opacity:.6}50%{opacity:1}}
.final-prose{font-size:clamp(1rem,1.8vw,1.1rem);line-height:1.95;color:var(--creme);max-width:680px;position:relative;z-index:1;margin-bottom:2.5rem;}
.final-prose p{margin-bottom:1.5rem;}
.final-prose em{color:var(--or-clair);font-style:italic;}
.final-origin{font-family:'Cinzel',serif;font-size:.75rem;letter-spacing:.55em;color:var(--cuivre);position:relative;z-index:1;}
.reveal{opacity:0;transform:translateY(28px);transition:opacity .8s ease,transform .8s ease;}
.reveal.visible{opacity:1;transform:translateY(0);}
footer{border-top:1px solid rgba(201,168,76,.08);padding:2.5rem;text-align:center;font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.25em;color:var(--dim);}
@media(max-width:768px){.section{padding:4rem 1.4rem;}.lettre{padding:2rem 1.6rem;}}
"""

SEED_SVG = """<svg class="seed-svg" viewBox="0 0 200 200" fill="none">
<defs><radialGradient id="sg" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#E8C97A" stop-opacity=".9"/><stop offset="100%" stop-color="#B97333" stop-opacity=".5"/></radialGradient></defs>
<circle cx="100" cy="100" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none"/>
<circle cx="100" cy="72" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none" opacity=".85"/>
<circle cx="124" cy="86" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none" opacity=".85"/>
<circle cx="124" cy="114" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none" opacity=".85"/>
<circle cx="100" cy="128" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none" opacity=".85"/>
<circle cx="76" cy="114" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none" opacity=".85"/>
<circle cx="76" cy="86" r="28" stroke="url(#sg)" stroke-width="1.2" fill="none" opacity=".85"/>
<circle cx="100" cy="100" r="56" stroke="#C9A84C" stroke-width=".6" fill="none" opacity=".3"/>
<circle cx="100" cy="100" r="70" stroke="#C9A84C" stroke-width=".4" fill="none" opacity=".15"/>
</svg>"""

def generer_html(offre, clients, narratif):
    annee = date.today().year
    if offre == 'solo':
        noms = f"{clients[0]['prenom']} {clients[0].get('nom','')}"
        tagline = "Ce que ta date de naissance révèle de qui tu es vraiment."
    elif offre == 'couple':
        noms = f"{clients[0]['prenom']} <span class='cover-amp'>&</span> {clients[1]['prenom']}"
        tagline = "Ce que vos deux lignées ont traversé pour que vous vous retrouviez."
    else:
        noms = " · ".join(c['prenom'] for c in clients)
        tagline = "Ce que votre lignée vous a transmis, et ce que vous pouvez en faire."

    nb = 2 + len(narratif.get('sections',[])) + 1 + 1
    nav = "\n".join(
        f'<div class="nav-dot{"  active" if i==0 else ""}" data-section="{i}"></div>'
        for i in range(nb)
    )

    sections_html = ""
    for i, sec in enumerate(narratif.get('sections',[])):
        sections_html += f"""
<section class="section section-sep" id="s{i+2}">
  <div class="reveal">
    <span class="s-eyebrow">{sec.get('eyebrow','')}</span>
    <h2 class="s-title">{sec['titre']}</h2>
    <div class="prose">{sec['contenu']}</div>
  </div>
</section>"""

    mantras_html = ""
    for i, m in enumerate(narratif.get('mantras',[])):
        sep = '<div class="ornament"><div class="ornament-line"></div><span class="ornament-symbol">✦</span><div class="ornament-line"></div></div>' if i > 0 else ''
        mantras_html += f"""{sep}
<div class="mantra-wrap">
  <div class="mantra-bg"></div>
  <p class="mantra-prenom">{m['prenom'].upper()}</p>
  <p class="mantra-txt">{m['texte']}</p>
  <p class="mantra-note">{m.get('note','')}</p>
</div>"""

    sm = 2 + len(narratif.get('sections',[]))
    sf = sm + 1
    sid_list = json.dumps([f's{i}' for i in range(nb)])

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ORIGIN — {noms}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Jost:wght@300;400&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<nav class="nav-dots" id="navDots">{nav}</nav>
<section class="cover" id="s0">
  <div class="cover-bg"></div>
  <div class="particles" id="particles"></div>
  <div class="cover-content">
    <p class="cover-eyebrow">Analyse personnalisée · {offre.capitalize()} · {annee}</p>
    <div class="seed-wrap"><div class="seed-pulse"></div><div class="seed-pulse"></div>{SEED_SVG}</div>
    <h1 class="cover-title">ORIGIN</h1>
    <p class="cover-names">{noms}</p>
    <p class="cover-tagline">{tagline}</p>
    <div class="cover-ligne"></div>
    <p class="cover-meta">Numérologie · Astrologie · Transgénérationnel</p>
  </div>
</section>
<section class="section section-sep" id="s1">
  <div class="reveal">
    <span class="s-eyebrow">Avant tout</span>
    <h2 class="s-title">Une lettre pour toi</h2>
    <div class="lettre">
      <div class="prose">{narratif.get('lettre','')}</div>
      <p class="lettre-signature">ORIGIN · Lecture personnalisée {annee}</p>
    </div>
  </div>
</section>
{sections_html}
<section class="section section-sep" id="s{sm}">
  <div class="reveal">
    <span class="s-eyebrow">Mots pour avancer</span>
    <h2 class="s-title s-title-center">Tes mantras personnalisés</h2>
    {mantras_html}
  </div>
</section>
<section class="section section-sep" id="s{sf}">
  <div class="reveal">
    <div class="final-wrap">
      <div class="final-glow"></div>
      <div class="final-prose">{narratif.get('message_final','')}</div>
      <div class="cover-ligne" style="margin-bottom:2rem;"></div>
      <p class="final-origin">ORIGIN · origin-famille.fr</p>
    </div>
  </div>
</section>
<footer>ORIGIN · Analyse personnalisée · {annee} · Confidentiel</footer>
<script>
const c=document.getElementById('particles');
for(let i=0;i<45;i++){{const p=document.createElement('div');p.className='particle';p.style.cssText=`left:${{Math.random()*100}}%;top:${{50+Math.random()*50}}%;--dur:${{4+Math.random()*7}}s;--delay:${{Math.random()*10}}s;`;c.appendChild(p);}}
const dots=document.querySelectorAll('.nav-dot');
const sIds={sid_list};
const sections=sIds.map(id=>document.getElementById(id));
dots.forEach((d,i)=>d.addEventListener('click',()=>{{if(sections[i])sections[i].scrollIntoView({{behavior:'smooth'}})}}));
const obs=new IntersectionObserver(e=>{{e.forEach(en=>{{if(en.isIntersecting){{en.target.querySelectorAll('.reveal').forEach(el=>el.classList.add('visible'));const idx=sections.indexOf(en.target);if(idx>=0){{dots.forEach(d=>d.classList.remove('active'));if(dots[idx])dots[idx].classList.add('active');}}}}}});}},{{threshold:0.12}});
sections.forEach(s=>{{if(s)obs.observe(s);}});
</script>
</body></html>"""

# ════════════════════════════════════════════════════
# ENVOI EMAIL
# ════════════════════════════════════════════════════

def envoyer_email(html_content, clients, offre, email_client):
    prenoms = " & ".join(c['prenom'] for c in clients)
    filename = f"ORIGIN_{offre}_{prenoms.replace(' ','_')}_{date.today().strftime('%Y%m%d')}.html"

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = EMAIL_DEST
    msg['Subject'] = f"✦ ORIGIN — Nouveau livret {offre} — {prenoms}"

    body = f"""Nouveau livret ORIGIN généré automatiquement.

Client(s) : {prenoms}
Offre : {offre.upper()}
Email client : {email_client}
Date : {date.today().strftime('%d/%m/%Y')}

Le livret est en pièce jointe. Ouvre-le dans un navigateur, valide, puis transfère au client.
"""
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(html_content.encode('utf-8'))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

    print(f"Email envoyé à {EMAIL_DEST}")

# ════════════════════════════════════════════════════
# ROUTES FLASK
# ════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'ORIGIN Generator'})

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json or request.form.to_dict()
        print(f"Webhook reçu : {json.dumps(data, ensure_ascii=False)[:300]}")

        offre = data.get('offre', 'solo').lower()
        email_client = data.get('email', '')

        # Parser les clients selon l'offre
        clients = []
        if offre == 'solo':
            clients = [{
                'prenom': data.get('prenom1', ''),
                'nom':    data.get('nom1', ''),
                'jour':   int(data.get('jour1', 1)),
                'mois':   int(data.get('mois1', 1)),
                'annee':  int(data.get('annee1', 1990)),
                'ville':  data.get('ville1', 'Paris'),
                'heure':  int(data['heure1']) if data.get('heure1') else None,
                'minute': int(data.get('minute1', 0)),
                'asc_force': data.get('asc1') or None,
            }]
        elif offre in ('couple', 'famille', 'prestige'):
            # Personne 1
            clients.append({
                'prenom': data.get('prenom1',''),
                'nom':    data.get('nom1',''),
                'jour':   int(data.get('jour1',1)),
                'mois':   int(data.get('mois1',1)),
                'annee':  int(data.get('annee1',1990)),
                'ville':  data.get('ville1','Paris'),
                'heure':  int(data['heure1']) if data.get('heure1') else None,
                'minute': int(data.get('minute1',0)),
                'asc_force': data.get('asc1') or None,
            })
            # Personne 2
            clients.append({
                'prenom': data.get('prenom2',''),
                'nom':    data.get('nom2',''),
                'jour':   int(data.get('jour2',1)),
                'mois':   int(data.get('mois2',1)),
                'annee':  int(data.get('annee2',1990)),
                'ville':  data.get('ville2','Paris'),
                'heure':  int(data['heure2']) if data.get('heure2') else None,
                'minute': int(data.get('minute2',0)),
                'asc_force': data.get('asc2') or None,
            })
            # Enfants si famille/prestige
            for i in range(3, 7):
                if data.get(f'prenom{i}'):
                    clients.append({
                        'prenom': data.get(f'prenom{i}',''),
                        'nom':    data.get(f'nom{i}',''),
                        'jour':   int(data.get(f'jour{i}',1)),
                        'mois':   int(data.get(f'mois{i}',1)),
                        'annee':  int(data.get(f'annee{i}',2010)),
                        'ville':  data.get(f'ville{i}',''),
                        'heure':  int(data[f'heure{i}']) if data.get(f'heure{i}') else None,
                        'minute': int(data.get(f'minute{i}',0)),
                        'asc_force': data.get(f'asc{i}') or None,
                    })

        # Calcul + prompt
        profils_txt_parts = []
        for c in clients:
            txt, _, _ = fmt_profil(c)
            profils_txt_parts.append(txt)
        profils_txt = "\n\n".join(profils_txt_parts)

        # Appel Claude
        narratif = appeler_claude(offre, profils_txt)

        # Génération HTML
        html = generer_html(offre, clients, narratif)

        # Envoi email
        envoyer_email(html, clients, offre, email_client)

        return jsonify({'status': 'success', 'message': 'Livret généré et envoyé'}), 200

    except Exception as e:
        print(f"ERREUR : {e}")
        import traceback; traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
