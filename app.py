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
7. MESSAGE FINAL (2 paragraphes — élan vers l'avenir, chaleureux et concret)""", "4500-6000", 8000),

    'couple': ("""
1. LETTRE D'OUVERTURE (3 paragraphes — ce qui rend cette rencontre unique, résonances entre leurs deux thèmes)
2. PORTRAIT INDIVIDUEL PERSONNE 1 (4 paragraphes — numérologie complète, astrologie, année perso, pinnacle)
3. PORTRAIT INDIVIDUEL PERSONNE 2 (4 paragraphes — idem, avec ses spécificités propres)
4. CE QUE VOUS CRÉEZ ENSEMBLE (3 paragraphes — résonances des chiffres croisés, dynamique de couple, zones de friction et de complémentarité)
5. OMBRES VERS LUMIÈRES (2 tensions de couple — situation concrète + bascule + lumière + phrase commune)
6. MANTRAS (un par personne + un mantra commun)
7. MESSAGE FINAL (2 paragraphes)""", "4500-6000", 8000),

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
    prompt = PROMPT_NAISSANCE.format(annee_courante=annee_courante, profils_txt=profils_txt)
    r = _appel_claude_raw(prompt, max_tokens=20000)
    return _extraire_json_claude(r) or FALLBACK_NARRATIF


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
  text-align: center;
  padding: 4cm 2.5cm;
  background: #0C0B08;
  color: #FDFAF5;
}
.cover-logo {
  max-width: 200px;
  max-height: 130px;
  margin-bottom: 1.5cm;
  opacity: .92;
  object-fit: contain;
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
.section { page-break-before: always; padding-top: .6cm; padding-bottom: 1cm; }

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
  page-break-before: always;
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
  page-break-before: always;
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
.notes-page { page-break-before: always; padding: .8cm 0 0; }
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
/* ── MODE NAISSANCE : graine de vie en bas de chaque page ── */
@page {
  @bottom-center {
    content: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 200 200' fill='none'%3E%3Ccircle cx='100' cy='100' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.45'/%3E%3Ccircle cx='100' cy='72' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.35'/%3E%3Ccircle cx='124' cy='86' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.35'/%3E%3Ccircle cx='124' cy='114' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.35'/%3E%3Ccircle cx='100' cy='128' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.35'/%3E%3Ccircle cx='76' cy='114' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.35'/%3E%3Ccircle cx='76' cy='86' r='28' stroke='%23C9A84C' stroke-width='4' fill='none' opacity='.35'/%3E%3C/svg%3E";
  }
  @bottom-left {
    content: "ORIGIN · Carnet de naissance · Confidentiel";
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

def _get_logo_b64():
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'logo-main.png')
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"[logo] Erreur lecture : {e}")
    return ''


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

    html_print = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>{CSS_PRINT}{css_extra}</style>
</head>
<body>

<div class="cover">
  {logo_html}
  <p class="cover-eyebrow">{cover_eyebrow}</p>
  <h1 class="cover-origin">ORIGIN</h1>
  <p class="cover-tagline">{tagline}</p>
  <div class="cover-ligne"></div>
  <p class="cover-names">{noms_display}</p>
  <p class="cover-meta">{cover_meta}</p>
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
                if "erreur technique" in narratif.get("lettre","").lower():
                    raise ValueError("Narratif invalide — fallback d'erreur détecté")
                html = generer_html(offre, clients, narratif)
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
