#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORIGIN — Serveur webhook
Reçoit les données → génère le livret → envoie par email
"""

from flask import Flask, request, jsonify
import threading, time
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

SIGNIF_CHIFFRES = {
    1:"leadership, indépendance, initiative, volonté",
    2:"harmonie, sensibilité, coopération, diplomatie",
    3:"créativité, expression, joie de vivre, communication",
    4:"structure, travail, stabilité, sens pratique",
    5:"liberté, changement, aventure, adaptabilité",
    6:"responsabilité, amour, famille, service",
    7:"introspection, spiritualité, analyse, quête de sens",
    8:"puissance, ambition, réussite matérielle, autorité",
    9:"sagesse, universalité, compassion, accomplissement",
    11:"inspiration, intuition élevée, mission spirituelle",
    22:"vision grandiose, réalisation concrète, bâtisseur",
    33:"amour universel, guérison, enseignement sacré",
}

THEMES_ANNEE = {
    1: ("Nouveau départ","Énergie pionnière, semences plantées","Oser commencer, affirmer sa direction"),
    2: ("Patience & Alliance","Sensibilité accrue, partenariats","Écouter, tisser des liens, laisser mûrir"),
    3: ("Expression & Créativité","Légèreté, expansion sociale","Créer, communiquer, célébrer la vie"),
    4: ("Construction & Travail","Effort, ancrage, mise en ordre","Poser des fondations solides, s'organiser"),
    5: ("Changement & Liberté","Mouvement, imprévus, renouveau","Accueillir le changement, ne pas résister"),
    6: ("Amour & Responsabilité","Foyer, famille, service aux autres","Prendre soin, équilibrer donner/recevoir"),
    7: ("Introspection & Quête","Retraite intérieure, analyse, foi","Se retrouver, chercher le sens profond"),
    8: ("Pouvoir & Abondance","Ambition, récolte, autorité","Prendre sa place, gérer ressources et pouvoir"),
    9: ("Clôture & Lâcher-prise","Fin de cycle, bilan, libération","Terminer, pardonner, se préparer au renouveau"),
    11:("Éveil Spirituel","Haute vibration, révélations, mission","Faire confiance à l'intuition, rayonner"),
    22:("Réalisation Majeure","Projets d'envergure, impact collectif","Concrétiser la vision avec méthode"),
    33:("Service Sacré","Amour inconditionnel, guérison, enseignement","Se mettre au service avec le cœur ouvert"),
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
    if key in VILLES_FR: return VILLES_FR[key]
    for k, v in VILLES_FR.items():
        if k in key or key in k: return v
    return 43.2965, 5.3698

CORPS_EPHEM = {
    'Soleil':sw.Sun,'Lune':sw.Moon,'Mercure':sw.Mercury,
    'Vénus':sw.Venus,'Mars':sw.Mars,'Jupiter':sw.Jupiter,
    'Saturne':sw.Saturn,'Uranus':sw.Uranus,'Neptune':sw.Neptune,
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
            if nom == 'Soleil': lon_deg = (lon_deg + 180) % 360
            else: lon_deg = lon_deg % 360
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
    filiation_str = f"\n  Filiation     : {p['filiation']}" if p.get('filiation') else ""

    chiffres = analyse_chiffres(j, m, a)
    num_pin, val_pin, reste_pin = pinnacles(j, m, a)
    ap = num['ap']
    theme_ap, energie_ap, focus_ap = THEMES_ANNEE.get(ap, ("Transition","Énergie de passage","Rester à l'écoute"))

    dom_str = ", ".join(f"{d} ({sig})" for d, sig in chiffres['dominants']) or "aucun"
    man_str = ", ".join(f"{mn} ({sig})" for mn, sig in chiffres['manquants']) or "aucun"
    pin_str = f"Pinnacle {num_pin} — valeur {val_pin}"
    if reste_pin: pin_str += f" (encore {reste_pin} ans dans ce cycle)"
    else: pin_str += " (dernier cycle, permanent)"

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
    for np_nom, d in astro['planetes'].items():
        lines.append(f"  {np_nom:<10}: {d['signe']} {d['degre']}°")
    if astro['ascendant']:
        asc = astro['ascendant']
        deg_str = f" {asc['degre']}°" if asc['degre'] else ""
        lines.append(f"  Ascendant  : {asc['signe']}{deg_str}")
    return "\n".join(lines), num, astro


# ─── FALLBACK & HELPERS ───────────────────────────────────────────────────────

FALLBACK_NARRATIF = {
    "lettre": "<p>Une erreur technique est survenue. Nous vous recontactons sous 24h.</p>",
    "sections": [],
    "mantras": [{"prenom": "Vous", "texte": "Votre lecture est en cours de préparation.", "note": ""}],
    "message_final": "<p>Nous avons bien reçu vos informations et préparons votre livret. Il vous sera envoyé sous 24h.</p>"
}

def _extraire_json_claude(r):
    resp_json = r.json()
    stop_reason = resp_json.get('stop_reason', '?')
    usage = resp_json.get('usage', {})
    print(f"[Claude] stop_reason={stop_reason} | in={usage.get('input_tokens','?')} | out={usage.get('output_tokens','?')}")
    if stop_reason == 'max_tokens':
        print("⚠️ Réponse tronquée (max_tokens atteint)")
    raw = resp_json['content'][0]['text'].strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw).strip()
    m = re.search(r'\{[\s\S]*\}', raw)
    if m: raw = m.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("JSON invalide — tentative de réparation...")
        for end in [raw.rfind('"}'), raw.rfind('"}')+1]:
            if end > 0:
                candidate = raw[:end+1]
                candidate += ']' * (candidate.count('[') - candidate.count(']'))
                candidate += '}' * (candidate.count('{') - candidate.count('}'))
                try: return json.loads(candidate)
                except: pass
        return None

def _appel_claude_raw(prompt, max_tokens=8000):
    last_ex = None
    for tentative in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-opus-4-6", "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
                timeout=600
            )
            r.raise_for_status()
            return r
        except Exception as e:
            last_ex = e
            if tentative < 2:
                print(f"Tentative {tentative+1}/3 échouée : {e} — relance dans 30s")
                time.sleep(30)
            else:
                raise last_ex


# ─── PROMPTS ──────────────────────────────────────────────────────────────────

def _preambule(annee_courante, mots_cible, profils_txt):
    return f"""Tu es le moteur narratif d'ORIGIN, service de lecture personnalisée (numérologie + astrologie + transgénérationnel).

ANNÉE EN COURS : {annee_courante}
Toutes les références à "cette année", "en {annee_courante}", l'année personnelle doivent se baser sur {annee_courante}.

LONGUEUR IMPÉRATIVE :
- Chaque paragraphe = MINIMUM 5-6 lignes de prose dense.
- Respecte EXACTEMENT le nombre de paragraphes indiqué.
- Le livret complet doit atteindre environ {mots_cible} mots.
- Si tu as l'impression d'avoir dit l'essentiel, creuse encore : ajoute un exemple concret, une image, une connexion entre données.

STYLE OBLIGATOIRE :
- Tutoiement systématique, chaleureux, direct
- Tout en prose narrative — zéro liste à puces
- Profond, immersif — le client doit sentir qu'on a passé des heures sur son cas
- Utilise les prénoms régulièrement (minimum 2 fois par paragraphe)
- Chaque paragraphe apporte quelque chose de nouveau — jamais de redite
- Situations concrètes, émotions précises, images sensorielles
- Ton bienveillant mais direct sur les zones d'ombre

DONNÉES :
{profils_txt}
"""

STRUCTURES = {
    'solo': ("""
1. LETTRE D'OUVERTURE (3 paragraphes — accroche sur ce qui rend cette personne unique, références aux nombres et planètes, chaleur et profondeur)
2. PORTRAIT NUMÉROLOGIQUE (4 paragraphes — chemin de vie, expression/intime/réalisation croisés, année perso avec thème et focus, pinnacle actuel)
3. PORTRAIT ASTROLOGIQUE (3 paragraphes — Soleil+Lune narrativisés ensemble, planètes personnelles, synthèse du thème natal)
4. FORCES ET CROISSANCE (2 paragraphes — dominants comme forces célébrées, manquants comme zones d'invitation avec exemples concrets)
5. OMBRES VERS LUMIÈRES (2 transformations — situation concrète vécue + bascule + lumière + phrase à dire à voix haute)
6. MANTRA PERSONNEL (1 mantra + note explicative de 2-3 lignes)
7. MESSAGE FINAL (2 paragraphes — élan vers l'avenir, chaleureux et concret)""", "3500-4500", 6000),

    'couple': ("""
1. LETTRE D'OUVERTURE (3 paragraphes — ce qui rend cette rencontre unique, résonances entre leurs deux thèmes)
2. PORTRAIT INDIVIDUEL PERSONNE 1 (4 paragraphes — numérologie complète, astrologie, année perso, pinnacle)
3. PORTRAIT INDIVIDUEL PERSONNE 2 (4 paragraphes — idem, avec ses spécificités propres)
4. CE QUE VOUS CRÉEZ ENSEMBLE (3 paragraphes — résonances des chiffres croisés, dynamique de couple, zones de friction et de complémentarité)
5. OMBRES VERS LUMIÈRES (2 tensions de couple — situation concrète + bascule + lumière + phrase commune)
6. MANTRAS (un par personne + un mantra commun)
7. MESSAGE FINAL (2 paragraphes)""", "3500-4500", 6000),

    'famille': ("""
1. LETTRE D'OUVERTURE (4 paragraphes longs — ce qui rend ce foyer unique, les résonances entre membres, mission collective)
2. PORTRAIT DE CHAQUE MEMBRE (4 paragraphes denses par personne — numérologie + astrologie + année perso + pinnacle — chaque membre traité avec la même profondeur)
3. DYNAMIQUE FAMILIALE (4 paragraphes denses — ce que chacun apporte au collectif, tensions créatives, complémentarités, rôles non dits)
4. HÉRITAGES ET TRANSMISSION (4 paragraphes denses — patterns qui se répètent, loyautés invisibles, ce qui cherche à se libérer)
5. COMMENT ACCOMPAGNER CHAQUE ENFANT — LE CŒUR DU LIVRET (pour CHAQUE enfant, 1 paragraphe dense et distinct — nature profonde, conseils concrets et actionnables, comment éviter de transmettre les schémas identifiés, comment l'aider à devenir la meilleure version de lui-même. Termine par un paragraphe de synthèse.)
6. OMBRES VERS LUMIÈRES (3 tensions familiales, 1 paragraphe dense chacune : situation concrète + bascule + lumière + phrase)
7. MANTRAS (un par membre + un mantra de foyer commun)
8. MESSAGE FINAL (3 paragraphes longs)""", "8000-10000", 12000),

    'prestige': None,  # géré séparément en chunks
}

PROMPT_NAISSANCE = """Tu es le narrateur sacré d'ORIGIN, service de lecture personnalisée de naissance.

Tu reçois les données numériques et astrologiques d'un enfant qui vient de naître ou qui est sur le point de naître.

TON RÔLE EST EXCEPTIONNEL :
Tu crées le document le plus précieux que ces parents recevront jamais — un carnet d'empreinte de naissance qui sera lu le jour de la naissance, relu à chaque anniversaire, offert à l'enfant quand il sera adolescent, puis adulte. Ce document traverse le temps. Il doit être à la hauteur de ce moment.

POSTURE ET TON :
- Parle de l'enfant à la troisième personne avec son prénom très souvent — jamais "l'enfant" seul, toujours "{{prénom}}" ou "ce petit être", "cette âme"
- Ton : contemplatif, lumineux, ancré, bienveillant — comme une sage-femme de l'âme qui a passé des semaines sur ce cas
- Jamais de jargon ésotérique brut — traduis TOUT en langage humain, concret, sensoriel
- Les parents doivent ressentir une surprise profonde, une émotion vraie, une reconnaissance — "c'est exactement lui/elle"
- L'enfant, en grandissant, doit pouvoir relire ce texte et se sentir vu, compris, aimé inconditionnellement
- Chaque phrase doit être belle, juste, mémorable
- Bienveillance absolue sur les zones d'ombre — formuler toujours comme une invitation, jamais comme une limite

ANNÉE EN COURS : {annee_courante}

LONGUEUR IMPÉRATIVE — C'EST CRITIQUE :
- Chaque paragraphe = MINIMUM 6-8 lignes de prose dense et riche
- Respecte EXACTEMENT le nombre de paragraphes indiqué pour chaque section
- Le livret complet DOIT atteindre entre 7000 et 9000 mots — c'est un livret premium, pas un résumé
- Si tu arrives à la fin d'une section et que tu n'as pas atteint la profondeur requise : CONTINUE, ajoute des images concrètes, des scènes de vie, des détails sensoriels, des projections dans l'avenir
- Ne jamais sacrifier la profondeur à la concision

STYLE ABSOLU :
- Tout en prose narrative — zéro liste, zéro tiret, zéro bullet
- Des scènes concrètes et précises : décris des moments que cet enfant pourrait vivre, des situations spécifiques à son profil
- Des images sensorielles : ce qu'il verra, sentira, entendra, ressentira dans son corps
- Croise systématiquement numérologie + astrologie — ne traite jamais une donnée isolément
- Utilise le prénom au moins 3 fois par paragraphe
- Alterne les longueurs de phrases pour créer un rythme — courtes pour l'impact, longues pour la contemplation

DONNÉES :
{profils_txt}

STRUCTURE — 10 SECTIONS (respecte chaque section avec la même rigueur) :

1. LETTRE D'OUVERTURE AUX PARENTS (4 paragraphes denses)
Ce que le cosmos a voulu ce jour précis. La signification de la date de naissance dans son ensemble — pas juste le nombre, mais ce que cette combinaison unique de jour, mois, année révèle comme intention de vie. L'énergie fondamentale que cet enfant porte comme signature. Ce qu'il/elle est venu apporter dans cette famille précisément, dans ce monde précisément, à ce moment précis de l'histoire. Terminer sur ce que les parents tiennent entre leurs mains ce soir.

2. SON CHEMIN DE VIE — LA MISSION (4 paragraphes denses)
Le chemin de vie narrativisé avec profondeur — pas juste sa définition, mais comment il se manifestera concrètement dans la vie de cet enfant. Des scènes précises de son enfance, de son adolescence, de son âge adulte. Ce qu'il/elle cherchera naturellement. Les types de situations qui le/la nourriront. Ce que ce chemin lui demandera comme courage. Ce qu'il lui offrira en retour.

3. SES DONS NATURELS — CE QUI LUI VIENT FACILEMENT (4 paragraphes denses)
Les forces issues des chiffres dominants et des positions planétaires favorables. Pour chaque don : une description narrative profonde + une scène concrète d'enfance où ce don apparaîtra naturellement + comment ce don évoluera à l'âge adulte. Ces dons sont des cadeaux — les nommer avec célébration, avec émerveillement.

4. SON MONDE INTÉRIEUR — LE CIEL NATAL (4 paragraphes denses)
Le Soleil et la Lune narrativisés ensemble comme le cœur de sa personnalité — son énergie vitale et sa vie émotionnelle profonde entremêlées. Mercure comme il pense et communique. Vénus comme il aime et ce qui le touche. Mars comme il agit et où il met son feu. Une synthèse du tempérament global — ce qui rend cet enfant unique au monde dans sa façon d'être.

5. SES ZONES DE CROISSANCE — LES APPRENTISSAGES QUI L'ATTENDENT (3 paragraphes denses)
Les chiffres manquants et positions planétaires de tension, traités avec une bienveillance absolue — jamais comme des manques, toujours comme des invitations à grandir. Pour chaque zone : une description de ce que cet enfant pourrait traverser + ce que cela lui enseignera + comment les parents peuvent l'accompagner sans projeter. Ces zones sont des cadeaux déguisés — les présenter ainsi.

6. LES GRANDES ÉTAPES — SA VIE EN PERSPECTIVE (3 paragraphes denses)
Les cycles numériques clés de sa vie : les années personnelles importantes dans son enfance (7 ans, 9 ans, 12 ans...), le tournant de l'adolescence, le premier grand cycle adulte. Le pinnacle actuel et comment il façonnera ses premières années. Des moments de transformation prévisibles — formulés comme des rendez-vous avec lui-même, pas comme des épreuves. Une vision douce et confiante de qui il deviendra.

7. POUR VOUS, PARENTS — L'ART D'ACCOMPAGNER CETTE ÂME (4 paragraphes denses)
Le paragraphe le plus important du livret pour les parents — concret, actionnable, profond. Ce dont cet enfant a besoin pour s'épanouir selon son profil précis. Ce qu'il faudra respecter en lui — ce qui ne se plie pas, ce qui doit rester sacré. Comment lui parler, comment le toucher, comment le gronder, comment le féliciter selon sa nature propre. Ce que ces parents-là, avec leur propre profil, peuvent lui apporter de particulièrement précieux — et où ils devront faire attention à ne pas projeter. Une phrase finale sur le privilège immense que c'est de recevoir cette âme-là.

8. SA PLACE DANS LA LIGNÉE (2 paragraphes denses)
Ce que cet enfant apporte de nouveau dans la famille — ce qui n'avait jamais existé avant lui/elle. Ce qu'il/elle est peut-être venu réparer, transformer ou accomplir dans la lignée familiale. Sans aller dans le transgénérationnel profond (c'est l'offre Famille/Prestige), donner une note d'espoir sur ce que ce petit être inaugure.

9. SON MANTRA DE VIE (1 mantra beau et fort + note de 4-5 lignes)
Un mantra profond, poétique et ancré — pas générique, vraiment issu de son profil unique. Une phrase que cet enfant pourra un jour faire sienne. La note explicative doit raconter pourquoi ces mots précis ont été choisis pour lui/elle.

10. UNE LETTRE POUR LUI — À LIRE QUAND IL SERA GRAND (3 paragraphes denses)
Écrit directement à l'enfant, à la deuxième personne, comme s'il avait 18 ans et lisait ce texte pour la première fois. Commence par "Tu es né(e) le..." et raconte qui il/elle était en arrivant au monde. Ce que ses parents ont ressenti ce jour-là. Ce que le ciel et les nombres disaient de lui/elle. Ce qu'il/elle porte comme lumière unique dans ce monde. Terminer sur un message d'amour inconditionnel et de confiance absolue en son chemin — quelque chose de si beau et si juste qu'il/elle voudra le relire toute sa vie.

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{{
  "lettre": "<p>...</p><p>...</p><p>...</p><p>...</p>",
  "sections": [
    {{"titre": "...", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p><p>...</p>"}},
    ...
  ],
  "mantras": [{{"prenom": "...", "texte": "...", "note": "..."}}],
  "message_final": "<p>...</p><p>...</p><p>...</p>"
}}"""


# ─── APPELS CLAUDE ────────────────────────────────────────────────────────────

def appeler_claude_naissance(profils_txt):
    annee_courante = date.today().year

    def pre(sections_txt, mots):
        return f"""Tu es le narrateur sacré d'ORIGIN, service de lecture personnalisée de naissance.
Tu reçois les données numériques et astrologiques d'un enfant qui vient de naître ou qui est sur le point de naître.

TON RÔLE EST EXCEPTIONNEL :
Tu crées le document le plus précieux que ces parents recevront jamais — un carnet d'empreinte de naissance relu chaque anniversaire, offert à l'enfant adulte. Il doit être à la hauteur de ce moment.

POSTURE ET TON :
- Parle de l'enfant avec son prénom très souvent — jamais "l'enfant" seul
- Ton : contemplatif, lumineux, ancré, bienveillant
- Jamais de jargon ésotérique brut — traduis TOUT en langage humain, concret, sensoriel
- Chaque phrase doit être belle, juste, mémorable
- Bienveillance absolue sur les zones d'ombre — toujours comme une invitation, jamais comme une limite

ANNÉE EN COURS : {annee_courante}

LONGUEUR IMPÉRATIVE :
- Chaque paragraphe = MINIMUM 6-8 lignes de prose dense
- Cette partie du livret doit atteindre environ {mots} mots
- Ne jamais sacrifier la profondeur à la concision

STYLE ABSOLU :
- Tout en prose narrative — zéro liste, zéro tiret
- Des scènes concrètes : décris des moments que cet enfant pourrait vivre
- Croise systématiquement numérologie + astrologie
- Utilise le prénom au moins 3 fois par paragraphe

DONNÉES :
{profils_txt}

""" + sections_txt

    prompt_a = pre(f"""STRUCTURE (rédiger UNIQUEMENT ces 2 sections) :
1. LETTRE D'OUVERTURE AUX PARENTS (4 paragraphes denses)
Ce que le cosmos a voulu ce jour précis. La signification de la date de naissance dans son ensemble. L'énergie fondamentale que cet enfant porte. Ce qu'il/elle est venu apporter dans cette famille. Ce que les parents tiennent entre leurs mains ce soir.

2. SON CHEMIN DE VIE — LA MISSION (4 paragraphes denses)
Le chemin de vie narrativisé — comment il se manifestera concrètement. Des scènes précises de son enfance, adolescence, âge adulte. Ce qu'il cherchera naturellement. Ce que ce chemin lui demandera comme courage et lui offrira en retour.

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{{
  "lettre": "<p>...</p><p>...</p><p>...</p><p>...</p>",
  "sections": [
    {{"titre": "Son chemin de vie — La mission", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p><p>...</p>"}}
  ]
}}""", "1800-2200")

    prompt_a2 = pre(f"""STRUCTURE (rédiger UNIQUEMENT ces 2 sections) :
3. SES DONS NATURELS — CE QUI LUI VIENT FACILEMENT (4 paragraphes denses)
Les forces issues des chiffres dominants et planètes favorables. Pour chaque don : description narrative + scène concrète d'enfance + évolution à l'âge adulte. Célébration et émerveillement.

4. SON MONDE INTÉRIEUR — LE CIEL NATAL (4 paragraphes denses)
Soleil et Lune narrativisés ensemble. Mercure, Vénus, Mars. Synthèse du tempérament global — ce qui rend cet enfant unique au monde.

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{{
  "sections": [
    {{"titre": "Ses dons naturels", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p><p>...</p>"}},
    {{"titre": "Son monde intérieur — Le ciel natal", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p><p>...</p>"}}
  ]
}}""", "1800-2200")

    prompt_b = pre(f"""STRUCTURE (rédiger UNIQUEMENT ces 3 sections) :
5. SES ZONES DE CROISSANCE — LES APPRENTISSAGES QUI L'ATTENDENT (3 paragraphes denses)
Chiffres manquants et tensions planétaires avec bienveillance absolue — toujours comme invitations à grandir. Pour chaque zone : ce que l'enfant pourrait traverser + ce que cela enseigne + comment les parents peuvent accompagner. Des cadeaux déguisés.

6. LES GRANDES ÉTAPES — SA VIE EN PERSPECTIVE (3 paragraphes denses)
Les cycles numériques clés de sa vie : années importantes dans l'enfance, tournant de l'adolescence, premier grand cycle adulte. Le pinnacle actuel. Des rendez-vous avec lui-même, pas des épreuves. Vision douce et confiante.

7. POUR VOUS, PARENTS — L'ART D'ACCOMPAGNER CETTE ÂME (4 paragraphes denses)
Le plus important pour les parents — concret, actionnable, profond. Ce dont cet enfant a besoin selon son profil précis. Ce qu'il faudra respecter. Comment lui parler, le toucher, le gronder, le féliciter selon sa nature. Ce que ces parents-là peuvent lui apporter de précieux — et où faire attention. Une phrase finale sur le privilège de recevoir cette âme.

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{{
  "sections": [
    {{"titre": "Ses zones de croissance", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p>"}},
    {{"titre": "Les grandes étapes — Sa vie en perspective", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p>"}},
    {{"titre": "Pour vous, parents", "eyebrow": "...", "contenu": "<p>...</p><p>...</p><p>...</p><p>...</p>"}}
  ]
}}""", "3000-3500")

    prompt_c = pre(f"""STRUCTURE (rédiger UNIQUEMENT ces 3 sections) :
8. SA PLACE DANS LA LIGNÉE (2 paragraphes denses)
Ce que cet enfant apporte de nouveau dans la famille — ce qui n'avait jamais existé avant lui/elle. Ce qu'il/elle est peut-être venu réparer ou inaugurer dans la lignée. Note d'espoir.

9. SON MANTRA DE VIE (1 mantra beau et fort + note de 4-5 lignes)
Un mantra profond, poétique, vraiment issu de son profil unique. Une phrase que cet enfant pourra un jour faire sienne. La note raconte pourquoi ces mots précis ont été choisis pour lui/elle.

10. UNE LETTRE POUR LUI — À LIRE QUAND IL SERA GRAND (3 paragraphes denses)
Écrit directement à l'enfant, à la deuxième personne, comme s'il avait 18 ans. Commence par "Tu es né(e) le..." Raconte qui il/elle était en arrivant au monde. Ce que ses parents ont ressenti. Ce que le ciel et les nombres disaient. Sa lumière unique. Terminer sur un message d'amour inconditionnel — quelque chose de si beau qu'il/elle voudra le relire toute sa vie.

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{{
  "sections": [
    {{"titre": "Sa place dans la lignée", "eyebrow": "...", "contenu": "<p>...</p><p>...</p>"}}
  ],
  "mantras": [{{"prenom": "...", "texte": "...", "note": "..."}}],
  "message_final": "<p>...</p><p>...</p><p>...</p>"
}}""", "2000-2500")

    a  = _extraire_json_claude(_appel_claude_raw(prompt_a,  max_tokens=5000))
    a2 = _extraire_json_claude(_appel_claude_raw(prompt_a2, max_tokens=5000))
    b  = _extraire_json_claude(_appel_claude_raw(prompt_b,  max_tokens=5000))
    c  = _extraire_json_claude(_appel_claude_raw(prompt_c,  max_tokens=4000))

    if not a or not a2 or not b or not c:
        print("⚠️ Un chunk Naissance a échoué — fallback")
        return FALLBACK_NARRATIF

    return {
        "lettre": a.get("lettre", ""),
        "sections": (a.get("sections") or []) + (a2.get("sections") or []) + (b.get("sections") or []) + (c.get("sections") or []),
        "mantras": c.get("mantras") or [{"prenom": "Votre enfant", "texte": "Tu es exactement là où tu dois être.", "note": ""}],
        "message_final": c.get("message_final", ""),
    }


def appeler_claude_prestige(profils_txt):
    annee_courante = date.today().year
    pre = lambda mots: _preambule(annee_courante, mots, profils_txt)

    prompt_a = pre("3000-3500") + """
STRUCTURE (rédiger uniquement ces 3 parties) :
1. LETTRE D'OUVERTURE (4 paragraphes longs — à la lignée entière sur 3 générations, ce que cette famille porte comme héritage et comme mission)
2. PORTRAIT DE CHAQUE MEMBRE DU FOYER (4 paragraphes denses par personne — numérologie + astrologie + année perso — chaque membre traité avec la même profondeur)
3. LES RACINES — LECTURE DES PARENTS DES DEUX ADULTES (5 paragraphes denses — profil de chaque parent, ce que chaque lignée a transmis, les schémas dominants de chaque branche familiale)

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{
  "lettre": "<p>...</p>",
  "sections": [
    {"titre": "Portrait de chaque membre du foyer", "eyebrow": "...", "contenu": "<p>...</p>..."},
    {"titre": "Les racines", "eyebrow": "...", "contenu": "<p>...</p>..."}
  ]
}"""

    prompt_b = pre("3500-4500") + """
STRUCTURE (rédiger uniquement ces 4 parties) :
1. L'HÉRITAGE INVISIBLE (4 paragraphes denses — répétitions sur 3 générations, silences familiaux, loyautés inconscientes, blessures transmises, ce qui cherche à se libérer)
2. COMMENT ACCOMPAGNER CHAQUE ENFANT — LE CŒUR DU LIVRET (pour CHAQUE enfant du foyer, 1 paragraphe dense et distinct — nature profonde, conseils concrets et actionnables, comment éviter de transmettre les schémas identifiés. Termine par un paragraphe de synthèse.)
3. CE QUI PEUT SE DÉNOUER (3 paragraphes denses — pistes concrètes de libération pour chaque membre et pour le foyer)
4. OMBRES VERS LUMIÈRES (3 tensions transgénérationnelles, 1 paragraphe dense chacune : pattern concret + bascule + lumière + phrase de libération)

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{
  "sections": [
    {"titre": "L'héritage invisible", "eyebrow": "...", "contenu": "<p>...</p>..."},
    {"titre": "Comment accompagner chaque enfant", "eyebrow": "...", "contenu": "<p>...</p>..."},
    {"titre": "Ce qui peut se dénouer", "eyebrow": "...", "contenu": "<p>...</p>..."},
    {"titre": "Ombres vers lumières", "eyebrow": "...", "contenu": "<p>...</p>..."}
  ]
}"""

    prompt_c = pre("1200-1800") + """
STRUCTURE (rédiger uniquement ces 2 parties) :
1. MANTRAS (un par membre du foyer ancré dans son profil + un mantra de lignée commun qui honore les racines et ouvre vers l'avenir)
2. MESSAGE FINAL (3 paragraphes longs — ancré dans l'espoir, la transmission consciente et la beauté de ce que cette lignée peut créer)

RETOURNE UNIQUEMENT ce JSON valide, sans markdown :
{
  "mantras": [{"prenom": "...", "texte": "...", "note": "..."}, ...],
  "message_final": "<p>...</p>"
}"""

    a = _extraire_json_claude(_appel_claude_raw(prompt_a, max_tokens=6000))
    b = _extraire_json_claude(_appel_claude_raw(prompt_b, max_tokens=16000))
    c = _extraire_json_claude(_appel_claude_raw(prompt_c, max_tokens=3000))

    if not a or not b or not c:
        print("⚠️ Un chunk Prestige a échoué — fallback")
        return FALLBACK_NARRATIF

    return {
        "lettre": a.get("lettre", ""),
        "sections": (a.get("sections") or []) + (b.get("sections") or []),
        "mantras": c.get("mantras") or [{"prenom":"Vous","texte":"Votre lecture est en cours de préparation.","note":""}],
        "message_final": c.get("message_final", ""),
    }


def appeler_claude(offre, profils_txt, type_analyse='adulte'):
    if type_analyse == 'naissance':
        return appeler_claude_naissance(profils_txt)
    if offre == 'prestige':
        return appeler_claude_prestige(profils_txt)

    annee_courante = date.today().year
    structure_txt, mots_cible, max_tokens = STRUCTURES.get(offre, STRUCTURES['famille'])

    prompt = _preambule(annee_courante, mots_cible, profils_txt) + f"""
STRUCTURE :
{structure_txt}

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

    r = _appel_claude_raw(prompt, max_tokens=max_tokens)
    return _extraire_json_claude(r) or FALLBACK_NARRATIF


# ─── CSS LIVRET HTML ──────────────────────────────────────────────────────────

CSS = """
:root{--noir:#090907;--encre:#111109;--or:#C9A84C;--or-clair:#E8C97A;--cuivre:#B97333;--creme:#F2ECD8;--muted:#9E9478;--dim:#5A5340;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{background:var(--noir);color:var(--creme);font-family:'Cormorant Garamond',serif;font-weight:300;overflow-x:hidden;}
.ambient{position:fixed;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(38% 34% at 28% 22%,rgba(185,115,51,.10),transparent 70%),radial-gradient(34% 40% at 78% 72%,rgba(201,168,76,.075),transparent 72%);animation:ambientDrift 24s ease-in-out infinite alternate;}
@keyframes ambientDrift{0%{transform:translate3d(0,0,0) scale(1);opacity:.85}100%{transform:translate3d(-3%,2.5%,0) scale(1.1);opacity:1}}
.shimmer{background:linear-gradient(105deg,#8A5E26 0%,var(--or) 28%,#FFF7DA 48%,var(--or) 66%,#8A5E26 100%);background-size:250% auto;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent;animation:shimmerShine 4s linear infinite;}
@keyframes shimmerShine{to{background-position:-250% center;}}
.cover{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;overflow:hidden;padding:4rem 2rem;text-align:center;}
.cover-bg{position:absolute;inset:0;background:radial-gradient(ellipse 70% 60% at 50% 40%,rgba(185,115,51,.15) 0%,transparent 65%);}
.cover-bg-pulse{position:absolute;inset:0;background:radial-gradient(ellipse 40% 40% at 50% 50%,rgba(201,168,76,.08) 0%,transparent 60%);animation:bgp 8s ease-in-out infinite;}
@keyframes bgp{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.15);opacity:1}}
.particles{position:absolute;inset:0;pointer-events:none;overflow:hidden;}
.particle{position:absolute;border-radius:50%;opacity:0;animation:pf var(--dur) var(--delay) ease-in-out infinite;}
@keyframes pf{0%{opacity:0;transform:translateY(0) scale(0)}15%{opacity:.9}70%{opacity:.3}100%{opacity:0;transform:translateY(-150px) scale(2)}}
.star{position:absolute;width:1px;height:1px;background:var(--or-clair);border-radius:50%;animation:twinkle var(--dur) var(--delay) ease-in-out infinite;}
@keyframes twinkle{0%,100%{opacity:0;transform:scale(1)}50%{opacity:.8;transform:scale(1.5)}}
.cover-content{position:relative;z-index:2;max-width:720px;margin:0 auto;}
.cover-eyebrow{font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.55em;text-transform:uppercase;color:var(--cuivre);margin-bottom:1.5rem;}
.seed-wrap{width:110px;height:110px;margin:0 auto 2rem;position:relative;}
.seed-svg{width:100%;height:100%;animation:sr 60s linear infinite;filter:drop-shadow(0 0 18px rgba(201,168,76,.45));}
@keyframes sr{to{transform:rotate(360deg)}}
.seed-pulse{position:absolute;inset:-18px;border-radius:50%;border:1px solid rgba(201,168,76,.15);animation:pr 3s ease-in-out infinite;}
.seed-pulse:nth-child(2){inset:-32px;animation-delay:1s;border-color:rgba(201,168,76,.08);}
@keyframes pr{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.05);opacity:.5}}
.cover-title{font-family:'Cinzel',serif;font-size:clamp(2.8rem,8vw,5rem);font-weight:400;letter-spacing:.28em;text-indent:.28em;color:var(--or-clair);margin-bottom:1.5rem;text-shadow:0 0 60px rgba(201,168,76,.5);}
.cover-names{font-family:'Cormorant Garamond',serif;font-size:clamp(1.6rem,4vw,2.4rem);font-style:italic;color:var(--creme);margin-bottom:.6rem;}
.cover-amp{color:var(--or);font-style:normal;margin:0 .5rem;}
.cover-tagline{font-size:1.05rem;color:var(--muted);font-style:italic;margin-bottom:2.5rem;line-height:1.7;}
.cover-ligne{width:80px;height:1px;background:linear-gradient(to right,transparent,var(--or),transparent);margin:0 auto 1.8rem;}
.cover-meta{font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.3em;text-transform:uppercase;color:var(--dim);}
.scroll-hint{position:absolute;bottom:2rem;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:.5rem;opacity:.4;animation:bounce 2s ease-in-out infinite;}
@keyframes bounce{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(8px)}}
.scroll-hint span{font-family:'Jost',sans-serif;font-size:.55rem;letter-spacing:.3em;color:var(--or);}
.scroll-arrow{width:20px;height:20px;border-right:1px solid var(--or);border-bottom:1px solid var(--or);transform:rotate(45deg);}
.nav-dots{position:fixed;right:1.8rem;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:.7rem;z-index:100;}
.nav-dot{width:6px;height:6px;border-radius:50%;background:rgba(201,168,76,.25);cursor:pointer;transition:all .4s;}
.nav-dot.active,.nav-dot:hover{background:var(--or);box-shadow:0 0 12px rgba(201,168,76,.7);transform:scale(1.5);}
.section{max-width:820px;margin:0 auto;padding:7rem 2.5rem;}
.section-sep{border-top:1px solid rgba(201,168,76,.08);}
.s-eyebrow{font-family:'Jost',sans-serif;font-size:.58rem;letter-spacing:.5em;text-transform:uppercase;color:var(--cuivre);margin-bottom:1rem;display:block;}
.s-title{font-family:'Cinzel',serif;font-size:clamp(1.5rem,3.5vw,2.2rem);font-weight:400;color:var(--or-clair);margin-bottom:2.5rem;letter-spacing:.06em;line-height:1.3;}
.s-title-center{text-align:center;}
.prose{font-size:clamp(1rem,1.8vw,1.12rem);line-height:2;color:var(--creme);font-weight:300;}
.prose p{margin-bottom:1.8rem;}
.prose em{color:var(--or-clair);font-style:italic;}
.lettre{background:rgba(201,168,76,.03);border:1px solid rgba(201,168,76,.12);border-left:3px solid var(--cuivre);padding:2.8rem 3rem;position:relative;}
.lettre::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(to right,var(--cuivre),transparent);}
.lettre-signature{margin-top:2rem;font-size:.85rem;letter-spacing:.2em;color:var(--cuivre);font-family:'Cinzel',serif;}
.ornament{display:flex;align-items:center;gap:1.2rem;margin:3rem 0;opacity:.4;}
.ornament-line{flex:1;height:1px;background:linear-gradient(to right,transparent,var(--or));}
.ornament-line:last-child{background:linear-gradient(to left,transparent,var(--or));}
.ornament-symbol{color:var(--or);font-size:1rem;}
.mantra-wrap{text-align:center;padding:4rem 2rem;position:relative;}
.mantra-bg{position:absolute;inset:0;background:radial-gradient(ellipse 60% 60% at 50% 50%,rgba(185,115,51,.08) 0%,transparent 70%);pointer-events:none;}
.mantra-prenom{font-family:'Cinzel',serif;font-size:.62rem;letter-spacing:.45em;color:var(--cuivre);margin-bottom:1.5rem;position:relative;z-index:1;}
.mantra-txt{font-family:'Cinzel',serif;font-size:clamp(1.1rem,2.5vw,1.6rem);font-weight:400;color:var(--or-clair);line-height:1.7;position:relative;z-index:1;}
.mantra-note{margin-top:1rem;font-size:.95rem;color:var(--dim);font-style:italic;position:relative;z-index:1;}
.final-wrap{min-height:60vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:6rem 2rem;position:relative;}
.final-glow{position:absolute;inset:0;background:radial-gradient(ellipse 50% 50% at 50% 50%,rgba(185,115,51,.12) 0%,transparent 70%);}
.final-prose{font-size:clamp(1rem,1.8vw,1.1rem);line-height:2;color:var(--creme);max-width:680px;position:relative;z-index:1;margin-bottom:2.5rem;}
.final-prose p{margin-bottom:1.5rem;}
.final-prose em{color:var(--or-clair);font-style:italic;}
.final-origin{font-family:'Cinzel',serif;font-size:.75rem;letter-spacing:.55em;color:var(--cuivre);position:relative;z-index:1;}
.final-seed{width:80px;height:80px;margin:0 auto 2rem;opacity:.6;animation:sr 30s linear infinite;}
.reveal{opacity:1;transform:translateY(0);transition:opacity 1s ease,transform 1s ease;}
.js-loaded .reveal{opacity:0;transform:translateY(40px);}
.reveal.visible{opacity:1 !important;transform:translateY(0) !important;}
.reveal-scale{opacity:1;transform:scale(1);transition:opacity 1s ease,transform 1s ease;}
.js-loaded .reveal-scale{opacity:0;transform:scale(0.92);}
.reveal-scale.visible{opacity:1 !important;transform:scale(1) !important;}
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

def generer_html(offre, clients, narratif, type_analyse='adulte'):
    annee = date.today().year
    is_naissance = (type_analyse == 'naissance')

    if is_naissance:
        prenom_e = clients[0]['prenom'].strip().capitalize()
        nom_e    = clients[0].get('nom','').strip().capitalize()
        noms     = f"{prenom_e} {nom_e}".strip()
        tagline  = f"Le carnet d'empreinte de {prenom_e} — un trésor pour toute une vie."
    elif offre == 'solo':
        noms = f"{clients[0]['prenom']} {clients[0].get('nom','')}"
        tagline = "Ce que ta date de naissance révèle de qui tu es vraiment."
    elif offre == 'couple':
        noms = f"{clients[0]['prenom']} <span class='cover-amp'>&</span> {clients[1]['prenom']}"
        tagline = "Ce que vos deux lignées ont traversé pour que vous vous retrouviez."
    else:
        noms = " · ".join(c['prenom'] for c in clients)
        tagline = "Ce que votre lignée vous a transmis, et ce que vous pouvez en faire."

    nb = 2 + len(narratif.get('sections',[])) + 1 + 1
    nav = "\n".join(f'<div class="nav-dot{" active" if i==0 else ""}" data-section="{i}"></div>' for i in range(nb))

    sections_html = ""
    for i, sec in enumerate(narratif.get('sections',[])):
        sections_html += f"""
<section class="section section-sep" id="s{i+2}">
  <div class="reveal" style="transition-delay:{i*0.1}s">
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
  <p class="mantra-txt shimmer">{m['texte']}</p>
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
<div class="ambient"></div>
<nav class="nav-dots" id="navDots">{nav}</nav>

<section class="cover" id="s0">
  <div class="cover-bg"></div>
  <div class="cover-bg-pulse"></div>
  <div class="particles" id="particles"></div>
  <div class="cover-content">
    {'<img src="data:image/png;base64,' + LOGO_B64_EMBEDDED + '" alt="ORIGIN" style="width:260px;max-width:62vw;margin:0 auto 2.4rem;display:block;" /><div class="cover-ligne" style="margin-top:1.4rem;"></div>' if is_naissance else '<p class="cover-eyebrow">Analyse personnalisée · ' + offre.capitalize() + ' · ' + str(annee) + '</p><h1 class="cover-title">ORIGIN</h1><div class="seed-wrap"><div class="seed-pulse"></div><div class="seed-pulse"></div>' + SEED_SVG + '</div><p class="cover-names">' + noms + '</p><p class="cover-tagline">' + tagline + '</p><div class="cover-ligne"></div><p class="cover-meta">Numérologie · Astrologie · Transgénérationnel</p>'}
  </div>
  <div class="scroll-hint"><span>Découvrir</span><div class="scroll-arrow"></div></div>
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
document.body.classList.add('js-loaded');
const pc = document.getElementById('particles');
for(let i=0;i<60;i++){{
  const p = document.createElement('div');
  const isSmall = Math.random() > 0.5;
  if(isSmall){{
    p.className='star';
    p.style.cssText=`left:${{Math.random()*100}}%;top:${{Math.random()*100}}%;--dur:${{3+Math.random()*5}}s;--delay:${{Math.random()*8}}s;`;
  }}else{{
    p.className='particle';
    const sz=Math.random()*3+1;
    p.style.cssText=`left:${{Math.random()*100}}%;top:${{60+Math.random()*40}}%;width:${{sz}}px;height:${{sz}}px;background:${{Math.random()>.5?'#E8C97A':'#B97333'}};--dur:${{5+Math.random()*8}}s;--delay:${{Math.random()*12}}s;`;
  }}
  pc.appendChild(p);
}}
const dots=document.querySelectorAll('.nav-dot');
const sIds={sid_list};
const sections=sIds.map(id=>document.getElementById(id));
dots.forEach((d,i)=>d.addEventListener('click',()=>{{if(sections[i])sections[i].scrollIntoView({{behavior:'smooth'}});}}));
const obs=new IntersectionObserver(entries=>{{
  entries.forEach(en=>{{
    if(en.isIntersecting){{
      en.target.querySelectorAll('.reveal,.reveal-scale,.light-line').forEach(el=>el.classList.add('visible'));
      const idx=sections.indexOf(en.target);
      if(idx>=0){{dots.forEach(d=>d.classList.remove('active'));if(dots[idx])dots[idx].classList.add('active');}}
    }}
  }});
}},{{threshold:0.05,rootMargin:'0px 0px -50px 0px'}});
sections.forEach(s=>{{if(s)obs.observe(s);}});
window.addEventListener('scroll',()=>{{
  const sy=window.scrollY;
  const cc=document.querySelector('.cover-content');
  if(cc)cc.style.transform=`translateY(${{sy*.3}}px)`;
}});
</script>
</body></html>"""


# ─── CSS PDF ──────────────────────────────────────────────────────────────────

CSS_PRINT = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Jost:wght@300;400&display=swap');

:root {
  --or: #C9A84C;
  --or-clair: #D4A843;
  --cuivre: #A0622A;
  --creme: #FDFAF5;
  --encre: #1A1208;
  --muted: #6B6050;
  --bordure: rgba(180,140,60,.18);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Cormorant Garamond', serif;
  font-weight: 300;
  background: #FDFAF5;
  color: var(--encre);
  font-size: 13pt;
  line-height: 2.15;
}

@page {
  size: A4;
  margin: 2.2cm 2.8cm 2.4cm;
  background: #FDFAF5;
  @bottom-center {
    content: "ORIGIN · Lecture personnalisée · Confidentiel";
    font-family: 'Jost', sans-serif;
    font-size: 6pt;
    letter-spacing: .25em;
    color: #A89E82;
  }
  @bottom-right {
    content: counter(page);
    font-family: 'Jost', sans-serif;
    font-size: 7pt;
    color: #C9A84C;
  }
}

@page cover { margin: 0; background: #0C0B08; }
.cover { page: cover; }

/* ── COUVERTURE ── */
.cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 29.7cm;
  width: 21cm;
  text-align: center;
  padding: 3cm 2cm;
  background: #0C0B08;
  color: #FDFAF5;
  box-sizing: border-box;
}
.cover-logo {
  width: 11cm;
  max-width: 11cm;
  height: auto;
  margin-bottom: 1.2cm;
  opacity: 1;
  display: block;
}
.cover-symbol { font-size: 24pt; color: #C9A84C; margin-bottom: 1.5cm; opacity: .8; }
.cover-eyebrow {
  font-family: 'Jost', sans-serif;
  font-size: 7pt;
  letter-spacing: .6em;
  text-transform: uppercase;
  color: #A0622A;
  margin-bottom: 1.2cm;
}
.cover-origin {
  font-family: 'Cinzel', serif;
  font-size: 52pt;
  letter-spacing: .28em;
  color: #C9A84C;
  margin-bottom: .5cm;
  line-height: 1;
}
.cover-tagline {
  font-family: 'Cormorant Garamond', serif;
  font-size: 13pt;
  font-style: italic;
  color: rgba(253,250,245,.6);
  margin-bottom: 2cm;
  line-height: 1.8;
  max-width: 11cm;
}
.cover-ligne { width: 60px; height: 1px; background: #C9A84C; margin: 0 auto 1.4cm; opacity: .4; }
.cover-names {
  font-family: 'Cormorant Garamond', serif;
  font-size: 26pt;
  font-style: italic;
  color: #FDFAF5;
  margin-bottom: .6cm;
  line-height: 1.3;
}
.cover-meta {
  font-family: 'Jost', sans-serif;
  font-size: 6.5pt;
  letter-spacing: .4em;
  text-transform: uppercase;
  color: rgba(253,250,245,.28);
  margin-top: 2cm;
}

/* ── SECTIONS — chaque titre sur nouvelle page ── */
.section { break-before: page; padding-top: .5cm; padding-bottom: .8cm; margin: 0; }
.section:first-of-type { break-before: avoid; }

.eyebrow {
  font-family: 'Jost', sans-serif;
  font-size: 6.5pt;
  letter-spacing: .55em;
  text-transform: uppercase;
  color: var(--cuivre);
  margin-bottom: .6cm;
  display: block;
}
.section-title {
  font-family: 'Cinzel', serif;
  font-size: 18pt;
  font-weight: 400;
  color: var(--or-clair);
  margin-bottom: .5cm;
  letter-spacing: .08em;
  line-height: 1.35;
}
.deco-line {
  width: 50px;
  height: 1px;
  background: var(--or);
  margin: .5cm 0 1.1cm;
  opacity: .4;
}

/* ── PROSE — respiration maximale ── */
.prose {
  font-size: 13pt;
  line-height: 2.15;
  color: var(--encre);
  font-weight: 300;
}
.prose p {
  margin-bottom: 1.1cm;
  text-align: justify;
  hyphens: auto;
}
.prose p:last-child { margin-bottom: 0; }
.prose em { color: var(--cuivre); font-style: italic; font-weight: 400; }
.prose strong { color: var(--or-clair); font-weight: 400; }

/* ── LETTRE D'OUVERTURE ── */
.lettre {
  padding: .2cm 0 .8cm 0;
  margin-bottom: .4cm;
  margin-top: .2cm;
}
.lettre-signature {
  font-family: 'Cinzel', serif;
  font-size: 7.5pt;
  letter-spacing: .25em;
  color: var(--cuivre);
  margin-top: .8cm;
  display: block;
  opacity: .7;
}

/* ── MANTRAS ── */
.mantra-block {
  text-align: center;
  padding: 1.2cm 2cm;
  border-top: 1px solid var(--bordure);
  border-bottom: 1px solid var(--bordure);
  margin: .8cm 0;
  page-break-inside: avoid;
}
.mantra-prenom {
  font-family: 'Cinzel', serif;
  font-size: 7pt;
  letter-spacing: .55em;
  text-transform: uppercase;
  color: var(--cuivre);
  margin-bottom: .5cm;
  opacity: .7;
}
.mantra-txt {
  font-family: 'Cinzel', serif;
  font-size: 14.5pt;
  color: var(--or-clair);
  line-height: 1.7;
  margin-bottom: .4cm;
  letter-spacing: .03em;
}
.mantra-note { font-size: 10.5pt; font-style: italic; color: var(--muted); line-height: 1.7; }

/* ── ORNEMENT ── */
.ornament { display: flex; align-items: center; gap: 1cm; margin: 1.2cm 0; opacity: .3; }
.ornament-line { flex: 1; height: 1px; background: var(--or); }
.ornament-symbol { color: var(--or); font-size: 9pt; }

/* ── MESSAGE FINAL ── */
.final-section {
  break-before: page;
  padding: .6cm 0;
  text-align: center;
}
.final-prose {
  font-size: 13pt;
  line-height: 2.15;
  color: var(--encre);
  max-width: 13cm;
  margin: 0 auto 1.2cm;
  text-align: justify;
  hyphens: auto;
  font-weight: 300;
}
.final-prose p { margin-bottom: 1cm; }
.final-prose em { color: var(--cuivre); font-style: italic; }
.final-origin {
  font-family: 'Cinzel', serif;
  font-size: 7.5pt;
  letter-spacing: .65em;
  color: var(--cuivre);
  display: block;
  margin-top: .8cm;
  opacity: .6;
}

/* ── CARNET D'INTÉGRATION ── */
.notes-cover-page {
  break-before: page;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 25cm;
}
.notes-cover-ornament { width: 50px; height: 1px; background: var(--or); margin: .8cm auto; opacity: .3; }
.notes-cover-title {
  font-family: 'Cinzel', serif;
  font-size: 22pt;
  color: var(--or-clair);
  letter-spacing: .22em;
  margin-bottom: .5cm;
  font-weight: 400;
}
.notes-cover-sub {
  font-family: 'Jost', sans-serif;
  font-size: 7pt;
  letter-spacing: .5em;
  text-transform: uppercase;
  color: var(--cuivre);
  margin-bottom: .8cm;
  opacity: .7;
}
.notes-cover-intro {
  font-size: 11pt;
  font-style: italic;
  color: var(--muted);
  max-width: 11cm;
  margin: 0 auto;
  line-height: 1.9;
}
.notes-page { break-before: page; padding: .5cm 0 0; margin: 0; }
.notes-page-header {
  display: flex;
  align-items: center;
  gap: .8cm;
  margin-bottom: .7cm;
  padding-bottom: .3cm;
  border-bottom: 1px solid rgba(201,168,76,.15);
}
.notes-page-label {
  font-family: 'Jost', sans-serif;
  font-size: 6pt;
  letter-spacing: .5em;
  text-transform: uppercase;
  color: rgba(160,98,42,.38);
  white-space: nowrap;
}
.notes-page-decor { flex: 1; height: 1px; background: linear-gradient(to right, rgba(201,168,76,.1), transparent); }
.notes-symbol { font-size: 7.5pt; color: rgba(201,168,76,.18); }
.note-line { width: 100%; height: 1px; background: rgba(180,140,60,.11); margin-bottom: .80cm; }
"""


CSS_PRINT_NAISSANCE_EXTRA = """
/* ── MODE NAISSANCE : footer override ── */
@page {
  @bottom-left {
    content: "ORIGIN · Carnet de naissance · Confidentiel";
    font-family: 'Jost', sans-serif;
    font-size: 6pt;
    letter-spacing: .25em;
    color: #A89E82;
  }
  @bottom-center {
    content: element(seed-running);
  }
  @bottom-right {
    content: counter(page);
    font-family: 'Jost', sans-serif;
    font-size: 7pt;
    color: #C9A84C;
  }
}
/* Graine de vie — méthode WeasyPrint avec running element */
.seed-fixed {
  position: running(seed-running);
  width: 35px;
  height: 35px;
  opacity: .14;
}
/* Palette légèrement plus douce pour naissance */
:root {
  --or: #C9A84C;
  --or-clair: #D4A843;
  --cuivre: #A07040;
  --creme: #FDFAF5;
  --encre: #1A1208;
  --muted: #7A6E58;
  --bordure: rgba(180,140,60,.15);
  --rose-doux: rgba(201,168,76,.06);
}
/* Couverture naissance */
.naissance-cover-accent {
  font-family: 'Cinzel', serif;
  font-size: 9pt;
  letter-spacing: .5em;
  color: rgba(201,168,76,.5);
  margin-bottom: .6cm;
  text-transform: uppercase;
}
/* Lettre finale à l'enfant — style plus intime */
.lettre-enfant {
  background: rgba(201,168,76,.03);
  border: 1px solid rgba(201,168,76,.12);
  padding: 1cm 1.5cm;
  margin-top: .3cm;
  font-style: italic;
}
.lettre-enfant .prose { font-style: italic; }
"""

SEED_SVG_FIXED = """<svg class="seed-fixed" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="100" cy="100" r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
<circle cx="100" cy="72"  r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
<circle cx="124" cy="86"  r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
<circle cx="124" cy="114" r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
<circle cx="100" cy="128" r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
<circle cx="76"  cy="114" r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
<circle cx="76"  cy="86"  r="28" stroke="#C9A84C" stroke-width="5" fill="none"/>
</svg>"""

# ── Logo ORIGIN embarqué en base64 (logo-main.png, 73ko) ─────────────────
LOGO_B64_EMBEDDED = "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"

def _get_logo_b64():
    """Retourne le logo ORIGIN en base64 — embarqué directement dans le code."""
    return LOGO_B64_EMBEDDED


def generer_pages_libres_pdf():
    labels = [
        "Ce qui résonne","Questions ouvertes","Engagements","Observations",
        "Ce que je veux retenir","Prises de conscience","Intentions",
        "Ce que je lâche","Ce que j'accueille","Réflexions",
        "Notes libres","Notes libres","Notes libres","Notes libres",
        "Notes libres","Notes libres","Notes libres","Notes libres"
    ]
    html = """
<div class="notes-cover-page">
  <div class="notes-cover-ornament"></div>
  <h2 class="notes-cover-title">Carnet d'intégration</h2>
  <p class="notes-cover-sub">Notes · Réflexions · Prises de conscience</p>
  <div class="notes-cover-ornament"></div>
  <p class="notes-cover-intro">Ces pages t'appartiennent. Utilise-les pour noter ce qui résonne,<br>
  tes prises de conscience, les engagements que tu veux prendre.<br><br>
  Ton livret ORIGIN est vivant — il grandit avec toi.</p>
  <div class="notes-cover-ornament"></div>
</div>"""
    # 29 lignes × 0.80cm = 23.2cm → remplit la page jusqu'en bas
    for label in labels:
        lignes = '\n'.join(['<div class="note-line"></div>'] * 29)
        html += f"""
<div class="notes-page">
  <div class="notes-page-header">
    <span class="notes-page-label">{label}</span>
    <div class="notes-page-decor"></div>
    <span class="notes-symbol">✦</span>
  </div>
  {lignes}
</div>"""
    return html


def generer_pdf_imprimable(offre, clients, narratif, type_analyse='adulte'):
    annee = date.today().year
    is_naissance = (type_analyse == 'naissance')

    if offre == 'solo':
        noms_display = f"{clients[0]['prenom']} {clients[0].get('nom','')}"
        if is_naissance:
            tagline = f"Le carnet d'empreinte de {clients[0]['prenom']} — un trésor pour toute une vie."
        else:
            tagline = "Ce que ta date de naissance révèle de qui tu es vraiment."
    elif offre == 'couple':
        noms_display = f"{clients[0]['prenom']} & {clients[1]['prenom']}"
        tagline = "Ce que vos deux lignées ont traversé pour que vous vous retrouviez."
    else:
        noms_display = " · ".join(c['prenom'] for c in clients)
        tagline = "Ce que votre lignée vous a transmis, et ce que vous pouvez en faire."

    logo_b64 = _get_logo_b64()
    logo_html = f'<img class="cover-logo" src="data:image/png;base64,{logo_b64}" alt="ORIGIN" />' if logo_b64 else '<p class="cover-symbol">✦</p>'

    # CSS supplémentaire si mode naissance
    css_extra = CSS_PRINT_NAISSANCE_EXTRA if is_naissance else ""

    # Sections — la dernière section naissance (lettre à l'enfant) reçoit un style spécial
    sections = narratif.get('sections', [])
    sections_html = ""
    for idx_sec, sec in enumerate(sections):
        is_last = (idx_sec == len(sections) - 1)
        lettre_class = 'lettre-enfant' if (is_naissance and is_last) else ''
        inner = f'<div class="{lettre_class}"><div class="prose">{sec.get("contenu","")}</div></div>' if lettre_class else f'<div class="prose">{sec.get("contenu","")}</div>'
        sections_html += f"""
<div class="section">
  <span class="eyebrow">{sec.get('eyebrow','')}</span>
  <h2 class="section-title">{sec.get('titre','')}</h2>
  <div class="deco-line"></div>
  {inner}
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

    pages_libres = generer_pages_libres_pdf()

    cover_meta = "Numérologie · Astrologie · Carnet de naissance" if is_naissance else "Numérologie · Astrologie · Transgénérationnel"
    cover_eyebrow = f"Carnet de naissance · {annee}" if is_naissance else f"Lecture personnalisée · {offre.capitalize()} · {annee}"

    seed_fixed_html = SEED_SVG_FIXED if is_naissance else ""

    html_print = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>{CSS_PRINT}{css_extra}</style>
</head>
<body>
{seed_fixed_html}

<div class="cover">
  {logo_html}
  {"" if is_naissance else f'<p class="cover-eyebrow">{cover_eyebrow}</p>'}
  <p class="cover-names">{noms_display}</p>
  <div class="cover-ligne"></div>
  {"" if is_naissance else f'<p class="cover-tagline">{tagline}</p><p class="cover-meta">{cover_meta}</p>'}
</div>

<div class="section">
  <span class="eyebrow">Avant tout</span>
  <h2 class="section-title">Une lettre pour toi</h2>
  <div class="deco-line"></div>
  <div class="lettre">
    <div class="prose">{narratif.get('lettre','')}</div>
    <span class="lettre-signature">ORIGIN · Lecture personnalisée {annee}</span>
  </div>
</div>

{sections_html}

<div class="section">
  <span class="eyebrow">Mots pour avancer</span>
  <h2 class="section-title" style="text-align:center">Tes mantras personnalisés</h2>
  <div class="deco-line" style="margin:.5cm auto 1cm;"></div>
  {mantras_html}
</div>

<div class="final-section">
  <div class="final-prose">{narratif.get('message_final','')}</div>
  <span class="final-origin">ORIGIN · origin-famille.fr</span>
</div>

{pages_libres}

</body>
</html>"""

    return WeasyprintHTML(string=html_print, base_url="https://origin-famille.fr").write_pdf()


# ─── EMAIL ────────────────────────────────────────────────────────────────────

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
- {filename_pdf}  → version imprimable A4 + carnet d'intégration (18 pages)
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
        json=payload, timeout=30
    )
    print(f"Brevo: {r.status_code} — {r.text[:200]}")
    r.raise_for_status()
    print(f"✅ Email envoyé à {EMAIL_DEST}")


# ─── FLASK ROUTES ─────────────────────────────────────────────────────────────

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
        type_analyse = data.get('type_analyse', 'adulte').lower()
        email_client = data.get('email', '')

        def safe_int(val, default):
            try: return int(val) if val is not None and val != '' else default
            except: return default

        clients = []
        if offre == 'solo':
            clients = [{
                'prenom': data.get('prenom1', ''),
                'nom':    data.get('nom1', ''),
                'jour':   safe_int(data.get('jour1'), 1),
                'mois':   safe_int(data.get('mois1'), 1),
                'annee':  safe_int(data.get('annee1'), 1990),
                'ville':  data.get('ville1', 'Paris'),
                'heure':  int(data['heure1']) if data.get('heure1') else None,
                'minute': safe_int(data.get('minute1'), 0),
                'asc_force': data.get('asc1') or None,
            }]
        elif offre in ('couple', 'famille', 'prestige'):
            for i in range(1, 3):
                clients.append({
                    'prenom': data.get(f'prenom{i}',''),
                    'nom':    data.get(f'nom{i}',''),
                    'jour':   safe_int(data.get(f'jour{i}'), 1),
                    'mois':   safe_int(data.get(f'mois{i}'), 1),
                    'annee':  safe_int(data.get(f'annee{i}'), 1990),
                    'ville':  data.get(f'ville{i}','Paris'),
                    'heure':  int(data[f'heure{i}']) if data.get(f'heure{i}') else None,
                    'minute': safe_int(data.get(f'minute{i}'), 0),
                    'asc_force': data.get(f'asc{i}') or None,
                })
            for i in range(3, 8):
                if data.get(f'prenom{i}'):
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

        profils_txt = "\n\n".join(fmt_profil(c)[0] for c in clients)

        def generer():
            try:
                narratif = appeler_claude(offre, profils_txt, type_analyse)
                html = generer_html(offre, clients, narratif, type_analyse)
                pdf  = generer_pdf_imprimable(offre, clients, narratif, type_analyse)
                envoyer_email(html, pdf, clients, offre, email_client)
                print(f"✅ Livret {offre} envoyé à {email_client}")
            except Exception as ex:
                print(f"ERREUR génération : {ex}")
                import traceback; traceback.print_exc()
                try:
                    prenoms = " & ".join(c['prenom'] for c in clients)
                    requests.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={"api-key": BREVO_SMTP_KEY, "content-type": "application/json"},
                        json={
                            "sender": {"name": "ORIGIN — Alerte", "email": "contact@origin-famille.fr"},
                            "to": [{"email": EMAIL_DEST}],
                            "subject": f"🚨 ORIGIN — ERREUR livret {offre} — {prenoms}",
                            "textContent": f"Erreur génération\nOffre : {offre}\nClients : {prenoms}\nEmail : {email_client}\n\n{ex}"
                        }, timeout=15
                    )
                except Exception as me:
                    print(f"Impossible d'envoyer l'alerte : {me}")

        threading.Thread(target=generer, daemon=True).start()
        return jsonify({'status': 'accepted', 'message': 'Livret en cours de génération'}), 200

    except Exception as e:
        print(f"ERREUR : {e}")
        import traceback; traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
