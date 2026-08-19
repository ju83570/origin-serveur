#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORIGIN — Serveur webhook
Reçoit les données Formspree → génère le livret → envoie par email
"""

from flask import Flask, request, jsonify
import threading
import os, json, re, requests
from datetime import datetime, date
import ephem as sw
import pytz, math
import base64
from weasyprint import HTML as WeasyprintHTML

TIMEZONE_MAP = {
    'france': 'Europe/Paris', 'fr': 'Europe/Paris',
    'belgique': 'Europe/Brussels', 'suisse': 'Europe/Zurich',
    'canada': 'America/Montreal', 'maroc': 'Africa/Casablanca',
    'espagne': 'Europe/Madrid', 'italie': 'Europe/Rome',
}

def get_timezone(ville):
    ville_lower = ville.lower()
    for k, v in TIMEZONE_MAP.items():
        if k in ville_lower:
            return v
    return 'Europe/Paris'

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BREVO_SMTP_LOGIN  = os.environ.get("BREVO_SMTP_LOGIN", "")
BREVO_SMTP_KEY    = os.environ.get("BREVO_SMTP_KEY", "")
EMAIL_DEST        = os.environ.get("EMAIL_DEST", "")

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

# ── Significations des chiffres ──────────────────────────────────────────────
SIGNIF_CHIFFRES = {
    1: "leadership, indépendance, initiative, volonté",
    2: "harmonie, sensibilité, coopération, diplomatie",
    3: "créativité, expression, joie de vivre, communication",
    4: "structure, travail, stabilité, sens pratique",
    5: "liberté, changement, aventure, adaptabilité",
    6: "responsabilité, amour, famille, service",
    7: "introspection, spiritualité, analyse, quête de sens",
    8: "puissance, ambition, réussite matérielle, autorité",
    9: "sagesse, universalité, compassion, accomplissement",
    11: "inspiration, intuition élevée, mission spirituelle",
    22: "vision grandiose, réalisation concrète, bâtisseur",
    33: "amour universel, guérison, enseignement sacré",
}

THEMES_ANNEE = {
    1: ("Nouveau départ", "Énergie pionnière, semences plantées", "Oser commencer, affirmer sa direction"),
    2: ("Patience & Alliance", "Sensibilité accrue, partenariats", "Écouter, tisser des liens, laisser mûrir"),
    3: ("Expression & Créativité", "Légèreté, expansion sociale", "Créer, communiquer, célébrer la vie"),
    4: ("Construction & Travail", "Effort, ancrage, mise en ordre", "Poser des fondations solides, s'organiser"),
    5: ("Changement & Liberté", "Mouvement, imprévus, renouveau", "Accueillir le changement, ne pas résister"),
    6: ("Amour & Responsabilité", "Foyer, famille, service aux autres", "Prendre soin, équilibrer donner/recevoir"),
    7: ("Introspection & Quête", "Retraite intérieure, analyse, foi", "Se retrouver, chercher le sens profond"),
    8: ("Pouvoir & Abondance", "Ambition, récolte, autorité", "Prendre sa place, gérer ressources et pouvoir"),
    9: ("Clôture & Lâcher-prise", "Fin de cycle, bilan, libération", "Terminer, pardonner, se préparer au renouveau"),
    11: ("Éveil Spirituel", "Haute vibration, révélations, mission", "Faire confiance à l'intuition, rayonner"),
    22: ("Réalisation Majeure", "Projets d'envergure, impact collectif", "Concrétiser la vision avec méthode"),
    33: ("Service Sacré", "Amour inconditionnel, guérison, enseignement", "Se mettre au service avec le cœur ouvert"),
}

def analyse_chiffres(j, m, a):
    chiffres_date = [int(d) for d in f"{j:02d}{m:02d}{a}" if d != '0']
    comptage = {i: chiffres_date.count(i) for i in range(1, 10)}
    dominants = [k for k, v in comptage.items() if v >= 3]
    manquants  = [k for k, v in comptage.items() if v == 0]
    return {
        'dominants': [(d, SIGNIF_CHIFFRES.get(d,'')) for d in dominants],
        'manquants':  [(mn, SIGNIF_CHIFFRES.get(mn,'')) for mn in manquants],
    }

def pinnacles(j, m, a):
    cdv = chemin_de_vie(j, m, a)
    p1 = reduire(j + m)
    p2 = reduire(m + sum(int(d) for d in str(a)))
    p3 = reduire(p1 + p2)
    p4 = reduire(j + sum(int(d) for d in str(a)))
    age = date.today().year - a
    fin_p1 = 36 - cdv
    if age < fin_p1:
        return 1, p1, fin_p1 - age
    elif age < fin_p1 + 9:
        return 2, p2, (fin_p1 + 9) - age
    elif age < fin_p1 + 18:
        return 3, p3, (fin_p1 + 18) - age
    else:
        return 4, p4, None

def annee_perso_detaillee(j, m):
    ap = reduire(sum(int(d) for d in f"{j:02d}{m:02d}{date.today().year}"))
    theme, energie, focus = THEMES_ANNEE.get(ap, ("Transition", "Énergie de passage", "Rester à l'écoute"))
    return ap, theme, energie, focus


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
    return 43.2965, 5.3698

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
    filiation = p.get('filiation', '')
    filiation_str = f"\n  Filiation     : {filiation}" if filiation else ""

    # Enrichissements
    chiffres = analyse_chiffres(j, m, a)
    num_pin, val_pin, reste_pin = pinnacles(j, m, a)
    ap, theme_ap, energie_ap, focus_ap = annee_perso_detaillee(j, m)

    # Chiffres dominants / manquants
    dom_str = ", ".join(f"{d} ({sig})" for d, sig in chiffres['dominants']) or "aucun"
    man_str = ", ".join(f"{mn} ({sig})" for mn, sig in chiffres['manquants']) or "aucun"

    # Pinnacle
    pin_str = f"Pinnacle {num_pin} — valeur {val_pin}"
    if reste_pin:
        pin_str += f" (encore {reste_pin} ans dans ce cycle)"
    else:
        pin_str += " (dernier cycle, permanent)"

    lines = [
        f"PROFIL : {pr} {nm}",
        f"Né(e) le {j:02d}/{m:02d}/{a} à {p.get('ville','')} ({heure_str}){filiation_str}",
        "",
        "NUMÉROLOGIE",
        f"  Chemin de vie : {label_nombre(num['cdv'])}",
        f"  Expression    : {label_nombre(num['expr'])}",
        f"  Intime        : {label_nombre(num['intime'])}",
        f"  Réalisation   : {label_nombre(num['real'])}",
        f"  Année perso   : {ap} — {theme_ap}",
        f"  Énergie       : {energie_ap}",
        f"  Focus         : {focus_ap}",
        f"  Cycle de vie  : {pin_str}",
        f"  Dominants     : {dom_str}",
        f"  Manquants     : {man_str}",
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

def appeler_claude(offre, profils_txt):
    annee_courante = date.today().year
    structures = {
        'solo': """
1. LETTRE D'OUVERTURE (4 paragraphes longs — accroche sur ce qui rend cette personne absolument unique, reference precise aux nombres et planetes, chaleur et profondeur)
2. PORTRAIT NUMEROLOGIQUE (5 paragraphes denses — 1 par nombre : chemin de vie, expression, intime, realisation, annee perso/pinnacle — croise les nombres entre eux dans chaque paragraphe)
3. PORTRAIT ASTROLOGIQUE (5 paragraphes denses — Soleil avec aspects, Lune avec aspects, Ascendant si connu, planetes personnelles Mercure+Venus+Mars, synthese du theme natal global)
4. TON ANNEE EN COURS (3 paragraphes denses — theme de l'annee perso, energie et focus concrets, resonance avec le pinnacle et les transits actuels en 2026)
5. FORCES ET CROISSANCE (3 paragraphes denses — dominants comme forces celebrees avec exemples de vie, manquants comme zones d'invitation avec exemples concrets de ce que ca genere)
6. OMBRES VERS LUMIERES (3 transformations completes, 1 paragraphe dense chacune : situation concrete vecue + bascule + lumiere + phrase a dire a voix haute)
7. MANTRA PERSONNEL (1 mantra fort — texte du mantra + note explicative de 3-4 lignes ancree dans les donnees)
8. MESSAGE FINAL (3 paragraphes longs — elan vers l'avenir, ce que cette personne est venue accomplir, chaleureux et concret)""",
        'couple': """
1. LETTRE D'OUVERTURE (4 paragraphes longs — ce qui rend cette rencontre unique, resonances entre leurs deux themes, chaleur et profondeur)
2. PORTRAIT INDIVIDUEL PERSONNE 1 (5 paragraphes denses — numerologie complete, astrologie, annee perso, pinnacle, ce qui la/le caracterise profondement)
3. PORTRAIT INDIVIDUEL PERSONNE 2 (5 paragraphes denses — idem, avec ses specificites propres, sans copier la structure de P1)
4. CE QUE VOUS CREEZ ENSEMBLE (4 paragraphes denses — resonances des chiffres croises, dynamique de couple, zones de friction et de complementarite, ce que leur union cree comme energie tierce)
5. VOS ANNEES EN RESONANCE (3 paragraphes denses — croiser les annees personnelles, les pinnacles, les transits communs en 2026)
6. OMBRES VERS LUMIERES (3 tensions de couple, 1 paragraphe dense chacune : situation concrete + bascule + lumiere + phrase commune)
7. MANTRAS (un par personne ancre dans son profil + un mantra commun ancre dans leur dynamique)
8. MESSAGE FINAL (3 paragraphes longs)""",
        'famille': """
1. LETTRE D'OUVERTURE (4 paragraphes longs — ce qui rend ce foyer unique, les resonances entre membres, ce que cette famille porte comme mission collective)
2. PORTRAIT DE CHAQUE MEMBRE (4 paragraphes denses par personne — numerologie + astrologie + annee perso + pinnacle — chaque membre traite avec la meme profondeur)
3. DYNAMIQUE FAMILIALE (4 paragraphes denses — ce que chacun apporte au collectif, les tensions creatives, les complementarites, les roles non dits)
4. HERITAGES ET TRANSMISSION (4 paragraphes denses — patterns qui se repetent, loyautes invisibles, ce qui a ete transmis sans le vouloir, ce qui cherche a se liberer)
5. OMBRES VERS LUMIERES (3 tensions familiales, 1 paragraphe dense chacune : situation concrete + bascule + lumiere + phrase)
6. MANTRAS (un par membre du foyer ancre dans son profil + un mantra de foyer commun)
7. MESSAGE FINAL (3 paragraphes longs — vision de ce que ce foyer peut devenir, chaleureux et porteur d'espoir)""",
        'prestige': """
1. LETTRE D'OUVERTURE (4 paragraphes longs — a la lignee entiere sur 3 generations, ce que cette famille porte comme heritage et comme mission)
2. PORTRAIT DE CHAQUE MEMBRE DU FOYER (4 paragraphes denses par personne — numerologie + astrologie + annee perso — chaque membre traite avec la meme profondeur)
3. LES RACINES — LECTURE DES PARENTS DES DEUX ADULTES (5 paragraphes denses — profil de chaque parent, ce que chaque lignee a transmis, les schemas dominants de chaque branche familiale)
4. L'HERITAGE INVISIBLE (4 paragraphes denses — repetitions sur 3 generations, silences familiaux, loyautes inconscientes, blessures transmises, ce qui cherche a se liberer a travers le foyer actuel)
5. CE QUI PEUT SE DENOUER (3 paragraphes denses — pistes concretes de liberation pour chaque membre et pour le foyer, ce que cette generation peut transformer pour les suivantes)
6. OMBRES VERS LUMIERES (3 tensions transgenationnelles, 1 paragraphe dense chacune : pattern concret observe sur plusieurs generations + bascule + lumiere + phrase de liberation)
7. MANTRAS (un par membre du foyer ancre dans son profil + un mantra de lignee commun qui honore les racines et ouvre vers l'avenir)
8. MESSAGE FINAL (3 paragraphes longs — ancre dans l'espoir, la transmission consciente et la beaute de ce que cette lignee peut creer)""",
    }
    structure = structures.get(offre, structures['famille'])

    prompt = f"""Tu es le moteur narratif d'ORIGIN, service de lecture personnalisée (numérologie + astrologie + transgénérationnel).

ANNÉE EN COURS : {annee_courante}
Toutes les références à "cette année", "en {annee_courante}", l'année personnelle, les transits actuels, doivent se baser sur {annee_courante}.

LONGUEUR IMPERATIVE — REGLE ABSOLUE PRIORITAIRE :
- Chaque paragraphe = MINIMUM 6-8 lignes de prose dense. Un paragraphe court est un paragraphe raté.
- Respecte EXACTEMENT le nombre de paragraphes indiqué. Si la structure dit 5 paragraphes, ecris 5 paragraphes complets, jamais 3.
- Le livret complet doit atteindre entre 9 000 et 12 000 mots. Ne condense pas, ne resume pas.
- Si tu as l'impression d'avoir dit l'essentiel, c'est le signal pour creuser encore : ajoute un exemple concret, une image, une connexion entre donnees, une nuance supplementaire.
- Chaque section doit etre aussi longue et dense que les autres. Aucune section light.

STYLE OBLIGATOIRE :
- Tutoiement systematique, chaleureux, direct
- Tout en prose narrative — zero liste a puces dans le contenu
- Profond, immersif, le client doit sentir qu'on a passe des heures sur son cas
- Utilise les prenoms regulierement (minimum 2 fois par paragraphe)
- Chaque paragraphe apporte quelque chose de nouveau — jamais de redite
- Nomme des situations concretes et vecues, des emotions precises, des images sensorielles
- Ton bienveillant mais direct sur les zones d'ombre

UTILISATION DES DONNEES ENRICHIES :
- L'annee personnelle, son theme et son focus sont deja calcules — developpe-les narrativement sur 3 paragraphes denses
- Les chiffres dominants = forces naturelles a nommer, celebrer et illustrer par des situations de vie concretes
- Les chiffres manquants = zones de croissance a explorer avec bienveillance — donne des exemples precis de ce que ca genere dans la vie quotidienne
- Le pinnacle actuel = le grand cycle de vie traverse — relie-le a ce que la personne vit concretement aujourd'hui
- Croise TOUJOURS numerologie + astrologie — ne traite jamais une donnee de facon isolee
- Pour l'astrologie : developpe Soleil, Lune, Ascendant (si connu), puis Mercure, Venus, Mars avec leurs aspects significatifs

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
        json={"model": "claude-opus-4-6", "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}]},
        timeout=600
    )
    r.raise_for_status()
    resp_json = r.json()
    stop_reason = resp_json.get('stop_reason', '?')
    usage = resp_json.get('usage', {})
    print(f"[Claude] stop_reason={stop_reason} | input_tokens={usage.get('input_tokens','?')} | output_tokens={usage.get('output_tokens','?')}")
    if stop_reason == 'max_tokens':
        print("⚠️ ATTENTION : réponse tronquée (max_tokens atteint) — le JSON sera probablement invalide")
    raw = resp_json['content'][0]['text']
    # Nettoyage robuste markdown
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()
    # Extraire le JSON si du texte précède
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        raw = match.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"JSON tronqué, tentative de réparation...")
        for end in [raw.rfind('"}'), raw.rfind('"}')+1]:
            if end > 0:
                candidate = raw[:end+1]
                opens_curl = candidate.count('{') - candidate.count('}')
                opens_bracket = candidate.count('[') - candidate.count(']')
                candidate += ']' * opens_bracket + '}' * opens_curl
                try:
                    return json.loads(candidate)
                except:
                    pass
        return {
            "lettre": "<p>Une erreur technique est survenue. Nous vous recontactons sous 24h.</p>",
            "sections": [],
            "mantras": [{"prenom": "Vous", "texte": "Votre lecture est en cours de préparation.", "note": ""}],
            "message_final": "<p>Nous avons bien reçu vos informations et préparons votre livret. Il vous sera envoyé sous 24h.</p>"
        }

CSS = """
:root{--noir:#090907;--encre:#111109;--or:#C9A84C;--or-clair:#E8C97A;--cuivre:#B97333;--creme:#F2ECD8;--muted:#9E9478;--dim:#5A5340;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{background:var(--noir);color:var(--creme);font-family:'Cormorant Garamond',serif;font-weight:300;overflow-x:hidden;}

/* COVER */
.cover{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;overflow:hidden;padding:4rem 2rem;text-align:center;}
.cover-bg{position:absolute;inset:0;background:radial-gradient(ellipse 70% 60% at 50% 40%,rgba(185,115,51,.15) 0%,transparent 65%);}
.cover-bg-pulse{position:absolute;inset:0;background:radial-gradient(ellipse 40% 40% at 50% 50%,rgba(201,168,76,.08) 0%,transparent 60%);animation:bgp 8s ease-in-out infinite;}
@keyframes bgp{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.15);opacity:1}}

/* PARTICULES */
.particles{position:absolute;inset:0;pointer-events:none;overflow:hidden;}
.particle{position:absolute;border-radius:50%;opacity:0;animation:pf var(--dur) var(--delay) ease-in-out infinite;}
@keyframes pf{0%{opacity:0;transform:translateY(0) scale(0)}15%{opacity:.9}70%{opacity:.3}100%{opacity:0;transform:translateY(-150px) scale(2)}}
.star{position:absolute;width:1px;height:1px;background:var(--or-clair);border-radius:50%;animation:twinkle var(--dur) var(--delay) ease-in-out infinite;}
@keyframes twinkle{0%,100%{opacity:0;transform:scale(1)}50%{opacity:.8;transform:scale(1.5)}}

/* LOGO MAIN */

/* GRAINE DE VIE */
.cover-content{position:relative;z-index:2;max-width:720px;margin:0 auto;}
.cover-eyebrow{font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.55em;text-transform:uppercase;color:var(--cuivre);margin-bottom:1.5rem;animation:fadein 1.5s ease-out forwards;}
.seed-wrap{width:110px;height:110px;margin:0 auto 2rem;position:relative;}
.seed-svg{width:100%;height:100%;animation:sr 60s linear infinite;filter:drop-shadow(0 0 18px rgba(201,168,76,.45));}
@keyframes sr{to{transform:rotate(360deg)}}
.seed-pulse{position:absolute;inset:-18px;border-radius:50%;border:1px solid rgba(201,168,76,.15);animation:pr 3s ease-in-out infinite;}
.seed-pulse:nth-child(2){inset:-32px;animation-delay:1s;border-color:rgba(201,168,76,.08);}
@keyframes pr{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.05);opacity:.5}}

.cover-title{font-family:'Cinzel',serif;font-size:clamp(1.8rem,5vw,3rem);font-weight:400;letter-spacing:.12em;color:var(--or-clair);margin-bottom:.8rem;animation:tg 6s ease-in-out infinite,fadein 2s ease-out forwards;}
@keyframes tg{0%,100%{text-shadow:0 0 40px rgba(232,201,122,.2)}50%{text-shadow:0 0 80px rgba(232,201,122,.6),0 0 120px rgba(201,168,76,.3)}}
@keyframes fadein{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.cover-names{font-family:'Cormorant Garamond',serif;font-size:clamp(1.6rem,4vw,2.4rem);font-style:italic;color:var(--creme);margin-bottom:.6rem;}
.cover-amp{color:var(--or);font-style:normal;margin:0 .5rem;}
.cover-tagline{font-size:1.05rem;color:var(--muted);font-style:italic;margin-bottom:2.5rem;line-height:1.7;}
.cover-ligne{width:80px;height:1px;background:linear-gradient(to right,transparent,var(--or),transparent);margin:0 auto 1.8rem;}
.cover-title{font-family:'Cinzel',serif;font-size:clamp(2.8rem,8vw,5rem);font-weight:400;letter-spacing:.28em;text-indent:.28em;color:var(--or-clair);margin-bottom:1.5rem;text-align:center;width:100%;text-shadow:0 0 60px rgba(201,168,76,.5);animation:tg 6s ease-in-out infinite,fadein 2s ease-out forwards;}
.cover-meta{font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.3em;text-transform:uppercase;color:var(--dim);}

/* SCROLL INDICATOR */
.scroll-hint{position:absolute;bottom:2rem;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:.5rem;opacity:.4;animation:bounce 2s ease-in-out infinite;}
@keyframes bounce{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(8px)}}
.scroll-hint span{font-family:'Jost',sans-serif;font-size:.55rem;letter-spacing:.3em;color:var(--or);}
.scroll-arrow{width:20px;height:20px;border-right:1px solid var(--or);border-bottom:1px solid var(--or);transform:rotate(45deg);}

/* NAV DOTS */
.nav-dots{position:fixed;right:1.8rem;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:.7rem;z-index:100;}
.nav-dot{width:6px;height:6px;border-radius:50%;background:rgba(201,168,76,.25);cursor:pointer;transition:all .4s;position:relative;}
.nav-dot::after{content:'';position:absolute;inset:-4px;border-radius:50%;border:1px solid rgba(201,168,76,.0);transition:all .4s;}
.nav-dot.active,.nav-dot:hover{background:var(--or);box-shadow:0 0 12px rgba(201,168,76,.7);transform:scale(1.5);}
.nav-dot.active::after{border-color:rgba(201,168,76,.3);}

/* SECTIONS */
.section{max-width:820px;margin:0 auto;padding:7rem 2.5rem;}
.section-sep{border-top:1px solid rgba(201,168,76,.08);}
.s-eyebrow{font-family:'Jost',sans-serif;font-size:.58rem;letter-spacing:.5em;text-transform:uppercase;color:var(--cuivre);margin-bottom:1rem;display:block;}
.s-title{font-family:'Cinzel',serif;font-size:clamp(1.5rem,3.5vw,2.2rem);font-weight:400;color:var(--or-clair);margin-bottom:2.5rem;letter-spacing:.06em;line-height:1.3;}
.s-title-center{text-align:center;}
.prose{font-size:clamp(1rem,1.8vw,1.12rem);line-height:2;color:var(--creme);font-weight:300;}
.prose p{margin-bottom:1.8rem;}
.prose em{color:var(--or-clair);font-style:italic;}

/* LETTRE */
.lettre{background:rgba(201,168,76,.03);border:1px solid rgba(201,168,76,.12);border-left:3px solid var(--cuivre);padding:2.8rem 3rem;position:relative;overflow:hidden;}
.lettre::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(to right,var(--cuivre),transparent);}
.lettre-signature{margin-top:2rem;font-size:.85rem;letter-spacing:.2em;color:var(--cuivre);font-family:'Cinzel',serif;}

/* ORNEMENTS */
.ornament{display:flex;align-items:center;gap:1.2rem;margin:3rem 0;opacity:.4;}
.ornament-line{flex:1;height:1px;background:linear-gradient(to right,transparent,var(--or));}
.ornament-line:last-child{background:linear-gradient(to left,transparent,var(--or));}
.ornament-symbol{color:var(--or);font-size:1rem;}

/* MANTRAS */
.mantra-wrap{text-align:center;padding:4rem 2rem;position:relative;overflow:hidden;}
.mantra-bg{position:absolute;inset:0;background:radial-gradient(ellipse 60% 60% at 50% 50%,rgba(185,115,51,.08) 0%,transparent 70%);pointer-events:none;animation:mb 5s ease-in-out infinite;}
@keyframes mb{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
.mantra-prenom{font-family:'Cinzel',serif;font-size:.62rem;letter-spacing:.45em;color:var(--cuivre);margin-bottom:1.5rem;position:relative;z-index:1;}
.mantra-txt{font-family:'Cinzel',serif;font-size:clamp(1.1rem,2.5vw,1.6rem);font-weight:400;color:var(--or-clair);line-height:1.7;position:relative;z-index:1;}
.mantra-note{margin-top:1rem;font-size:.95rem;color:var(--dim);font-style:italic;position:relative;z-index:1;}

/* FINAL */
.final-wrap{min-height:60vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:6rem 2rem;position:relative;}
.final-glow{position:absolute;inset:0;background:radial-gradient(ellipse 50% 50% at 50% 50%,rgba(185,115,51,.12) 0%,transparent 70%);animation:fb 6s ease-in-out infinite;}
@keyframes fb{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;transform:scale(1.05)}}
.final-prose{font-size:clamp(1rem,1.8vw,1.1rem);line-height:2;color:var(--creme);max-width:680px;position:relative;z-index:1;margin-bottom:2.5rem;}
.final-prose p{margin-bottom:1.5rem;}
.final-prose em{color:var(--or-clair);font-style:italic;}
.final-origin{font-family:'Cinzel',serif;font-size:.75rem;letter-spacing:.55em;color:var(--cuivre);position:relative;z-index:1;}
.final-seed{width:80px;height:80px;margin:0 auto 2rem;opacity:.6;animation:sr 30s linear infinite;}

/* RÉVÉLATION AU SCROLL — Safari + Android compatible */
.reveal{opacity:1;transform:translateY(0);transition:opacity 1s ease,transform 1s ease;}
.js-loaded .reveal{opacity:0;transform:translateY(40px);}
.reveal.visible{opacity:1 !important;transform:translateY(0) !important;}
.reveal-left{opacity:1;transform:translateX(0);transition:opacity 1s ease,transform 1s ease;}
.js-loaded .reveal-left{opacity:0;transform:translateX(-40px);}
.reveal-left.visible{opacity:1 !important;transform:translateX(0) !important;}
.reveal-scale{opacity:1;transform:scale(1);transition:opacity 1s ease,transform 1s ease;}
.js-loaded .reveal-scale{opacity:0;transform:scale(0.92);}
.reveal-scale.visible{opacity:1 !important;transform:scale(1) !important;}

/* LIGNE LUMINEUSE */
.light-line{width:0;height:1px;background:linear-gradient(to right,transparent,var(--or),transparent);margin:2rem auto;transition:width 1.5s ease;}
.light-line.visible{width:120px;}

footer{border-top:1px solid rgba(201,168,76,.08);padding:2.5rem;text-align:center;font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.25em;color:var(--dim);}
@media(max-width:768px){.section{padding:4rem 1.4rem;}.lettre{padding:2rem 1.6rem;}}
"""

SEED_SVG = """<svg class="seed-svg" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
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
        delay = i * 0.1
        sections_html += f"""
<section class="section section-sep" id="s{i+2}">
  <div class="reveal" style="transition-delay:{delay}s">
    <span class="s-eyebrow">{sec.get('eyebrow','')}</span>
    <h2 class="s-title">{sec.get('titre','')}</h2>
    <div class="light-line"></div>
    <div class="prose">{sec.get('contenu','')}</div>
  </div>
</section>"""

    mantras_html = ""
    for i, m in enumerate(narratif.get('mantras',[])):
        sep = '<div class="ornament"><div class="ornament-line"></div><span class="ornament-symbol">✦</span><div class="ornament-line"></div></div>' if i > 0 else ''
        mantras_html += f"""{sep}
<div class="mantra-wrap reveal-scale">
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
  <div class="cover-bg-pulse"></div>
  <div class="particles" id="particles"></div>
  <div class="cover-content">
    <p class="cover-eyebrow">Analyse personnalisée · {offre.capitalize()} · {annee}</p>
    <h1 class="cover-title">ORIGIN</h1>
    <div class="seed-wrap">
      <div class="seed-pulse"></div>
      <div class="seed-pulse"></div>
      {SEED_SVG}
    </div>
    <p class="cover-names">{noms}</p>
    <p class="cover-tagline">{tagline}</p>
    <div class="cover-ligne"></div>
    <p class="cover-meta">Numérologie · Astrologie · Transgénérationnel</p>
  </div>
  <div class="scroll-hint">
    <span>Découvrir</span>
    <div class="scroll-arrow"></div>
  </div>
</section>

<section class="section section-sep" id="s1">
  <div class="reveal">
    <span class="s-eyebrow">Avant tout</span>
    <h2 class="s-title">Une lettre pour toi</h2>
    <div class="light-line"></div>
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
    <div class="light-line" style="margin:0 auto 3rem;"></div>
    {mantras_html}
  </div>
</section>

<section class="section section-sep" id="s{sf}">
  <div class="reveal">
    <div class="final-wrap">
      <div class="final-glow"></div>
      <svg class="final-seed" viewBox="0 0 200 200" fill="none">{SEED_SVG}</svg>
      <div class="final-prose">{narratif.get('message_final','')}</div>
      <div class="cover-ligne" style="margin-bottom:2rem;"></div>
      <p class="final-origin">ORIGIN · origin-famille.fr</p>
    </div>
  </div>
</section>

<footer>ORIGIN · Analyse personnalisée · {annee} · Confidentiel</footer>

<script>
// Activation progressive — Safari safe
document.body.classList.add('js-loaded');

// Particules dorées
const pc = document.getElementById('particles');
for(let i=0;i<60;i++){{
  const p = document.createElement('div');
  const isSmall = Math.random() > 0.5;
  if(isSmall){{
    p.className='star';
    p.style.cssText=`left:${{Math.random()*100}}%;top:${{Math.random()*100}}%;--dur:${{3+Math.random()*5}}s;--delay:${{Math.random()*8}}s;`;
  }}else{{
    p.className='particle';
    const size = Math.random()*3+1;
    p.style.cssText=`left:${{Math.random()*100}}%;top:${{60+Math.random()*40}}%;width:${{size}}px;height:${{size}}px;background:${{Math.random()>0.5?'#E8C97A':'#B97333'}};--dur:${{5+Math.random()*8}}s;--delay:${{Math.random()*12}}s;`;
  }}
  pc.appendChild(p);
}}

// Navigation dots
const dots = document.querySelectorAll('.nav-dot');
const sIds = {sid_list};
const sections = sIds.map(id => document.getElementById(id));
dots.forEach((d,i) => d.addEventListener('click', () => {{
  if(sections[i]) sections[i].scrollIntoView({{behavior:'smooth'}});
}}));

// Intersection Observer — révélations + nav active
const revealObs = new IntersectionObserver(entries => {{
  entries.forEach(en => {{
    if(en.isIntersecting){{
      en.target.querySelectorAll('.reveal,.reveal-left,.reveal-scale,.light-line').forEach(el => el.classList.add('visible'));
      const idx = sections.indexOf(en.target);
      if(idx >= 0){{
        dots.forEach(d => d.classList.remove('active'));
        if(dots[idx]) dots[idx].classList.add('active');
      }}
    }}
  }});
}}, {{threshold: 0.05, rootMargin: '0px 0px -50px 0px'}});
sections.forEach(s => {{ if(s) revealObs.observe(s); }});

// Effet parallaxe léger sur la cover
window.addEventListener('scroll', () => {{
  const sy = window.scrollY;
  const coverContent = document.querySelector('.cover-content');
  if(coverContent) coverContent.style.transform = `translateY(${{sy * 0.3}}px)`;
  const logo = document.querySelector('.logo-main-wrap');
  if(logo) logo.style.transform = `translateY(${{sy * 0.15}}px)`;
}});
</script>
</body></html>"""


CSS_PRINT = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Jost:wght@300;400&display=swap');

:root {
  --or: #C9A84C;
  --or-clair: #E8C97A;
  --cuivre: #B97333;
  --creme: #F5EDD8;
  --encre: #1C1409;
  --muted: #7A6E58;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Cormorant Garamond', serif;
  font-weight: 300;
  background: var(--creme);
  color: var(--encre);
  font-size: 12pt;
  line-height: 2;
}

@page {
  size: A4;
  margin: 2cm 2.2cm;
  @bottom-center {
    content: "ORIGIN · Lecture personnalisée · Confidentiel";
    font-family: 'Jost', sans-serif;
    font-size: 6.5pt;
    letter-spacing: .2em;
    color: #9E9478;
  }
  @bottom-right {
    content: counter(page);
    font-family: 'Jost', sans-serif;
    font-size: 7pt;
    color: #C9A84C;
  }
}
@page cover { margin: 0; }
.cover { page: cover; }

.page { page-break-after: always; }
.page:last-child { page-break-after: avoid; }

.cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  text-align: center;
  padding: 4cm 2cm;
  background: #0A0A08;
  color: var(--creme);
}
.cover-symbol { font-size: 22pt; color: var(--or); margin-bottom: 1.5cm; }
.cover-eyebrow { font-family: 'Jost', sans-serif; font-size: 7pt; letter-spacing: .5em; text-transform: uppercase; color: var(--cuivre); margin-bottom: 1cm; }
.cover-origin { font-family: 'Cinzel', serif; font-size: 42pt; letter-spacing: .22em; color: var(--or); margin-bottom: .5cm; }
.cover-tagline { font-family: 'Cormorant Garamond', serif; font-size: 13pt; font-style: italic; color: rgba(245,237,216,.75); margin-bottom: 1.5cm; }
.cover-ligne { width: 60px; height: 1px; background: var(--or); margin: 0 auto 1cm; opacity: .5; }
.cover-names { font-family: 'Cormorant Garamond', serif; font-size: 22pt; font-style: italic; color: var(--creme); margin-bottom: .4cm; }
.cover-meta { font-family: 'Jost', sans-serif; font-size: 7pt; letter-spacing: .3em; text-transform: uppercase; color: rgba(245,237,216,.4); margin-top: 1.5cm; }

.section { padding: 1.5cm 2cm; }
.section + .section { border-top: 1px solid rgba(201,168,76,.18); }

.eyebrow { font-family: 'Jost', sans-serif; font-size: 6.5pt; letter-spacing: .45em; text-transform: uppercase; color: var(--cuivre); margin-bottom: .4cm; display: block; }
.section-title { font-family: 'Cinzel', serif; font-size: 16pt; font-weight: 400; color: var(--or); margin-bottom: .35cm; letter-spacing: .08em; line-height: 1.3; }
.light-line { width: 50px; height: 1px; background: var(--or); margin: .4cm 0 .8cm; opacity: .5; }

.prose { font-size: 12pt; line-height: 2; color: var(--encre); }
.prose p { margin-bottom: .65cm; }
.prose em { color: var(--cuivre); font-style: italic; }
.prose * { color: var(--encre) !important; }
.prose em, .prose em * { color: var(--cuivre) !important; }
.lettre .prose * { color: var(--encre) !important; }

.lettre { background: rgba(201,168,76,.04); border: 1px solid rgba(201,168,76,.2); border-left: 3px solid var(--cuivre); padding: 1cm 1.4cm; margin-bottom: .5cm; }
.lettre-signature { font-family: 'Cinzel', serif; font-size: 7.5pt; letter-spacing: .2em; color: var(--cuivre); margin-top: .5cm; }

.mantra-block { text-align: center; padding: 1cm 1.5cm; border: 1px solid rgba(201,168,76,.15); margin-bottom: .5cm; background: rgba(201,168,76,.02); }
.mantra-prenom { font-family: 'Cinzel', serif; font-size: 7pt; letter-spacing: .45em; text-transform: uppercase; color: var(--cuivre); margin-bottom: .35cm; }
.mantra-txt { font-family: 'Cinzel', serif; font-size: 13pt; color: var(--or); line-height: 1.6; margin-bottom: .25cm; }
.mantra-note { font-size: 9.5pt; font-style: italic; color: var(--muted); }

.ornament { display: flex; align-items: center; gap: 1cm; margin: .6cm 0; opacity: .4; }
.ornament-line { flex: 1; height: 1px; background: var(--or); }
.ornament-symbol { color: var(--or); font-size: 10pt; }

.final-section { padding: 1.5cm 2cm; text-align: center; border-top: 1px solid rgba(201,168,76,.18); }
.final-prose { font-size: 12pt; line-height: 2; color: var(--encre); max-width: 14cm; margin: 0 auto .8cm; }
.final-prose p { margin-bottom: .65cm; }
.final-prose em { color: var(--cuivre); font-style: italic; }
.final-origin { font-family: 'Cinzel', serif; font-size: 7.5pt; letter-spacing: .55em; color: var(--cuivre); }

/* CARNET D'INTÉGRATION */
.carnet-cover { page: cover; display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; padding:4cm 2cm; background:#0A0A08; color:var(--creme); text-align:center; }
.carnet-cover-title { font-family:'Cinzel',serif; font-size:28pt; letter-spacing:.18em; color:var(--or); margin-bottom:.8cm; }
.carnet-cover-sub { font-family:'Cormorant Garamond',serif; font-size:13pt; font-style:italic; color:rgba(245,237,216,.7); }
.carnet-page { padding:2cm 2.5cm; }
.carnet-header { font-family:'Cinzel',serif; font-size:.65rem; letter-spacing:.4em; text-transform:uppercase; color:var(--cuivre); margin-bottom:1.2cm; border-bottom:1px solid rgba(201,168,76,.3); padding-bottom:.4cm; }
.carnet-question { font-family:'Cormorant Garamond',serif; font-size:12pt; font-style:italic; color:var(--encre); margin-bottom:.5cm; line-height:1.6; }
.carnet-line { width:100%; height:1px; background:linear-gradient(to right,rgba(201,168,76,.4),rgba(201,168,76,.1)); margin-bottom:.55cm; }
"""

def generer_pdf_imprimable(offre, clients, narratif):
    annee = date.today().year

    if offre == 'solo':
        noms_display = f"{clients[0]['prenom']} {clients[0].get('nom','')}"
        tagline = "Ce que ta date de naissance révèle de qui tu es vraiment."
    elif offre == 'couple':
        noms_display = f"{clients[0]['prenom']} & {clients[1]['prenom']}"
        tagline = "Ce que vos deux lignées ont traversé pour que vous vous retrouviez."
    else:
        noms_display = " · ".join(c['prenom'] for c in clients)
        tagline = "Ce que votre lignée vous a transmis, et ce que vous pouvez en faire."

    sections_html = ""
    for sec in narratif.get('sections', []):
        sections_html += f"""
<div class="section">
  <span class="eyebrow">{sec.get('eyebrow','')}</span>
  <h2 class="section-title">{sec.get('titre','')}</h2>
  <div class="light-line"></div>
  <div class="prose">{sec.get('contenu','')}</div>
</div>"""

    mantras_html = ""
    for i, m in enumerate(narratif.get('mantras', [])):
        sep = '<div class="ornament"><div class="ornament-line"></div><span class="ornament-symbol">✦</span><div class="ornament-line"></div></div>' if i > 0 else ''
        mantras_html += f"""{sep}
<div class="mantra-block">
  <p class="mantra-prenom">{m.get('prenom','').upper()}</p>
  <p class="mantra-txt">{m.get('texte','')}</p>
  <p class="mantra-note">{m.get('note','')}</p>
</div>"""

    html_print = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>{CSS_PRINT}</style>
</head>
<body>

<div class="cover page">
  <p class="cover-symbol">✦</p>
  <p class="cover-eyebrow">Lecture personnalisée · {offre.capitalize()} · {annee}</p>
  <h1 class="cover-origin">ORIGIN</h1>
  <p class="cover-tagline">{tagline}</p>
  <div class="cover-ligne"></div>
  <p class="cover-names">{noms_display}</p>
  <p class="cover-meta">Numérologie · Astrologie · Transgénérationnel</p>
</div>

<div class="section page">
  <span class="eyebrow">Avant tout</span>
  <h2 class="section-title">Une lettre pour toi</h2>
  <div class="light-line"></div>
  <div class="lettre">
    <div class="prose">{narratif.get('lettre','')}</div>
    <p class="lettre-signature">ORIGIN · Lecture personnalisée {annee}</p>
  </div>
</div>

{sections_html}

<div class="section page">
  <span class="eyebrow">Mots pour avancer</span>
  <h2 class="section-title" style="text-align:center">Tes mantras personnalisés</h2>
  <div class="light-line" style="margin:.4cm auto .8cm;"></div>
  {mantras_html}
</div>

<!-- CARNET D'INTÉGRATION -->
<div class="carnet-cover page">
  <p style="font-family:'Cinzel',serif;font-size:7pt;letter-spacing:.5em;text-transform:uppercase;color:#B97333;margin-bottom:1.5cm">ORIGIN · Carnet personnel</p>
  <h2 class="carnet-cover-title">Carnet d'Intégration</h2>
  <p class="carnet-cover-sub">Tes réflexions · Tes prises de conscience · Ton chemin</p>
  <div style="width:60px;height:1px;background:#C9A84C;margin:2cm auto;opacity:.5;"></div>
  <p style="font-size:9pt;color:rgba(245,237,216,.4);letter-spacing:.2em;font-family:'Jost',sans-serif">À imprimer · À compléter à la main</p>
</div>

{"".join([f'''
<div class="carnet-page page">
  <p class="carnet-header">Réflexion {i+1} · ORIGIN</p>
  {"".join([f'<p class="carnet-question">{q}</p>' + '<div class="carnet-line"></div>' * 6 for q in [
    ["Qu'est-ce qui t'a le plus touché dans ta lecture ?",
     "Quelle phrase résonne encore en toi ?",
     "Qu'as-tu envie de changer à partir d'aujourd'hui ?"][i % 3]
  ]])}
  {"".join(['<div class="carnet-line"></div>' for _ in range(12)])}
</div>''' for i in range(6)])}

</body>
</html>"""

    return WeasyprintHTML(string=html_print, base_url="https://origin-famille.fr").write_pdf()


def envoyer_email(html_content, pdf_bytes, clients, offre, email_client):
    prenoms = " & ".join(c['prenom'] for c in clients)
    date_str = date.today().strftime('%Y%m%d')
    filename_html = f"ORIGIN_{offre}_{prenoms.replace(' ','_')}_{date_str}.html"
    filename_pdf  = f"ORIGIN_{offre}_{prenoms.replace(' ','_')}_{date_str}_imprimable.pdf"

    body_txt = f"""Nouveau livret ORIGIN généré automatiquement.

Client(s) : {prenoms}
Offre : {offre.upper()}
Email client : {email_client}
Date : {date.today().strftime('%d/%m/%Y')}

Pièces jointes :
- {filename_html} → livret interactif (ouvrir dans un navigateur)
- {filename_pdf}  → version imprimable A4
{"- Les_Heritages_Invisibles.pdf → ebook bonus inclus" if offre in ('famille','prestige') else ""}

Valide le contenu puis transfère au client.
"""

    attachments = [
        {"content": base64.b64encode(html_content.encode('utf-8')).decode('utf-8'), "name": filename_html},
        {"content": base64.b64encode(pdf_bytes).decode('utf-8'), "name": filename_pdf},
    ]

    if offre in ('famille', 'prestige'):
        ebook_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'heritages_invisibles.pdf')
        if os.path.exists(ebook_path):
            with open(ebook_path, 'rb') as f:
                attachments.append({
                    "content": base64.b64encode(f.read()).decode('utf-8'),
                    "name": "Les_Heritages_Invisibles.pdf"
                })
        else:
            print(f"⚠ Ebook introuvable : {ebook_path}")

    payload = {
        "sender": {"name": "ORIGIN", "email": "contact@origin-famille.fr"},
        "to": [{"email": EMAIL_DEST}],
        "subject": f"✦ ORIGIN — Nouveau livret {offre} — {prenoms}",
        "textContent": body_txt,
        "attachment": attachments
    }

    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_SMTP_KEY, "content-type": "application/json"},
        json=payload,
        timeout=30
    )
    print(f"Brevo API response: {r.status_code} — {r.text[:200]}")
    r.raise_for_status()
    print(f"✅ Email envoyé à {EMAIL_DEST}")

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/webhook", methods=["OPTIONS"])
def webhook_preflight():
    return jsonify({}), 200

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
            for i in range(3, 7):
                if data.get(f'prenom{i}'):
                    def safe_int(val, default):
                        try: return int(val) if val is not None and val != '' else default
                        except: return default
                    clients.append({
                        'prenom': data.get(f'prenom{i}',''),
                        'nom':    data.get(f'nom{i}',''),
                        'jour':   safe_int(data.get(f'jour{i}'), 1),
                        'mois':   safe_int(data.get(f'mois{i}'), 1),
                        'annee':  safe_int(data.get(f'annee{i}'), 2000),
                        'ville':  data.get(f'ville{i}',''),
                        'heure':  int(data[f'heure{i}']) if data.get(f'heure{i}') else None,
                        'minute': safe_int(data.get(f'minute{i}'), 0),
                        'asc_force': data.get(f'asc{i}') or None,
                        'filiation': data.get(f'filiation{i}',''),
                    })

        profils_txt_parts = []
        for c in clients:
            txt, _, _ = fmt_profil(c)
            profils_txt_parts.append(txt)
        profils_txt = "\n\n".join(profils_txt_parts)

        def generer():
            try:
                narratif = appeler_claude(offre, profils_txt)
                # Vérification que le narratif n'est pas le fallback d'erreur
                lettre = narratif.get("lettre", "")
                if "erreur technique" in lettre.lower() or "en cours de préparation" in lettre.lower():
                    raise ValueError("Narratif invalide — fallback d'erreur détecté après parsing JSON")
                html = generer_html(offre, clients, narratif)
                pdf = generer_pdf_imprimable(offre, clients, narratif)
                envoyer_email(html, pdf, clients, offre, email_client)
                print(f"✅ Livret {offre} envoyé à {email_client}")
            except Exception as ex:
                print(f"ERREUR génération : {ex}")
                import traceback; traceback.print_exc()
                # Alerte email interne
                try:
                    prenoms = " & ".join(c['prenom'] for c in clients)
                    payload_alerte = {
                        "sender": {"name": "ORIGIN — Alerte", "email": "contact@origin-famille.fr"},
                        "to": [{"email": EMAIL_DEST}],
                        "subject": f"🚨 ORIGIN — ERREUR livret {offre} — {prenoms}",
                        "textContent": f"Une erreur est survenue lors de la génération du livret.\n\nOffre : {offre}\nClients : {prenoms}\nEmail client : {email_client}\n\nErreur :\n{ex}\n\nRelance manuelle nécessaire."
                    }
                    requests.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={"api-key": BREVO_SMTP_KEY, "content-type": "application/json"},
                        json=payload_alerte,
                        timeout=15
                    )
                    print("📧 Alerte erreur envoyée")
                except Exception as mail_ex:
                    print(f"Impossible d'envoyer l'alerte : {mail_ex}")

        t = threading.Thread(target=generer, daemon=True)
        t.start()

        return jsonify({'status': 'accepted', 'message': 'Livret en cours de génération'}), 200

    except Exception as e:
        print(f"ERREUR : {e}")
        import traceback; traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
