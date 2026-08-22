
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
  max-width: 260px;
  max-height: 200px;
  margin-bottom: 1.2cm;
  opacity: .95;
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
/* ── MODE NAISSANCE : footer override ── */
@page {
  @bottom-left {
    content: "ORIGIN · Carnet de naissance · Confidentiel";
    font-family: 'Jost', sans-serif;
    font-size: 6pt;
    letter-spacing: .25em;
    color: #A89E82;
  }
  @bottom-center { content: ""; }
  @bottom-right {
    content: counter(page);
    font-family: 'Jost', sans-serif;
    font-size: 7pt;
    color: #C9A84C;
  }
}
/* Graine de vie fixe en bas de chaque page — méthode WeasyPrint */
.seed-fixed {
  position: fixed;
  bottom: .55cm;
  left: 50%;
  transform: translateX(-50%);
  width: 22px;
  height: 22px;
  opacity: .32;
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
LOGO_B64_EMBEDDED = "iVBORw0KGgoAAAANSUhEUgAAA0UAAALdCAYAAADjxcgvAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAP+lSURBVHhe7P13vGTXdd+JfvfeJ1S6+XZu5NQIjGCmSAWKohIlWcmSHMeWLL+xPbb0ebZHz555lj3jjyU/y57xyJSsZOUsUSJFiiIl5kwQBIjYDaCBRudw++YKJ+z3x9qn6tzq2w000OiAu74fHJyqU6dOrNu1f7XW+i2zb98+D1CW5YapKArOnDmFoiiKoiiKoijKpWJubhvOOay1G6YryZXdu6IoiqIoiqIoyhVGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoiqIoirKlUVGkKIqiKIqiKMqWRkWRoiiKoiiKoihbGhVFiqIoiqIoiqJsaVQUKYqiKIqiKIqypVFRpCiKoiiKoijKlkZFkaIoiqIoiqIoWxoVRYqiKIqiKIqibGlUFCmKoiiKoiiKsqVRUaQoiqIoiqIoypZGRZGiKIqiKIqiKFsaFUWKoiiKoiiKomxpVBQpiqIoz4m5BJOiKIqiXK2oKFIURVGGDEWMkbkFrAnPzzfZsWn89TDZMNW3r2JJURRFuRpQUaQoirIFqQRJJXrOmQBnwNraMmsw1siy4WSwZmyqvS7rmw3bdvbC+9XokqIoinK5UVGkKIryMmcogOrioxI7YW6GIqYmdixB5IyEjQvLnLFYY0frutp61uCsDfP69moC6Zz9jR3X2FRFlhRFURTlpUBFkaIoysuMKj3tHAFUe26Gy4OIMQZrbRAzFmfl+UjkGJyTeeQMzkHkILJm08nZ0WsuTCNhJPuppuF+hpEmEWRDwWRCZCk81tQ7RVEU5VJj9u3b5wHKstwwFUXBmTOnxtdXFEVRrkJM+F8liPAy98Zg8EFEjNSEkWfDNw/fN3yvvDp8T/X6UIwYfNjuOL56H+DxMpcZ+LBM/gv7k7W8D28OM1+9MaxbbQs/XDxk/LmiKIpy9TI3tw3nXPhRbDRdSVQUKYqiXKMMhUz1uPZgKHrCSvXXxfhgJIqqx0OBU1un2sTw/8OVqv2ci4iZzZ+PRJIfCiXvZVve15abMB8TQENBFcRVWHVsnfC+8FxRFEW5ulBRpCiKorwogsbZ8NgHcWIrlVITOVX0Rx6bDQLIGDFCqESPCKHwOOygEj0bxVD1jgszFCxDITRaPhItIn5Gy8LzII58EFDV+4bLh+8JIqnay7hAUnGkKIpy1aGiSFEURblo6gKlekzQJhYpuKlHhkwVKQrRHhuWWytrjYuf4fNKMFWiJ9TyDEXQZiJpM2VUiZ+aCKoeU0uVG4qcauWwrBy+3w9f92XtfUPxtFEgjaJIoyjUcFvhf9VhKIqiKFcOFUWKoijK82ZcDIlw2Sh4qnXEgKAWCRqKoGq5vK/6zhkKJ1sTTdV6YTsWg7EeakIqyKOhKBqKoxp1MVSJIHwlUDzeG7z3lFUEqPSUG4SPpwzCp3rfUAiFdcqgdsqglMoNkaWRMKoiT5UaGr4uTxVFUZQrgIoiRVEU5TmpRM1QbwRBIlGheuSnEkhic20qYQMYazHBsW1cAJlgiy3vE7c3EVG1ZdU2gytcJZaqxyLORtuuqKfKjSZPiceXNcFTyrKyDIKmrMSPvC4ip3q9JpgqATWMEkniXFl7/zkRpDGBtFG0qUBSFEW53KgoUhRFUc7LMBoUegqJ8KhHb8JyQl+gsH4lYoYRoQ3LRj2CnB0JKBvsta2p223bkf123Yq7sssO1t3GhePBYGw47ioKQxAaQYiUpafw1XcMlL6kKD1FIcuK0o+mohRBFJaXpacowZdQ+BLvZb2RSKoei+Apg9ASgTVKvStLOaZRNGkUPdpwzBvuhqIoivJSoaJIURRFOYcqKhT0ziiysyGlbVQTVPUXGkZuhv17gmip9wUy0jOoEj3OGqLISv8gZ4kjS+QMcWSJnSVyljiq1pE+QlEUtucskQHjrBxfEG9Vyp5EZUbRG4+hLEqKEPHJCxE7eeHJi4Ki8GSFJ8sL8tyTFSV5XpIXZVinpKjm4f1lWQktiTCVRRVxClGm8wikshyLHlWvqzhSFEW57KgoUhRFUYaM0s9GYkjqeILgCN8Pw8amtVS2kRiqGq+GSE6IALmqcWoldiJLEjniyJBEjiS2pLElSSLSyJLEljhyQSQFIWRCE1dXa7waIk1yvEGw1c5pQ6QoRGkkYlRSVpGewlOUQfjkpQijrGCQF/QzzyDP6Wcl2aCknxdkeTmcZP2SohTBVEWZJKpUS8fzsu+yqjcKy4cpemUl4kbrqzhSFEW5PKgoUhRFUZ6XGBrV+4xS4epCqJ4SJ1EfifwMoz5BBIn4iWiklkbiaCQRjSQSQRTL60MhFN4v6XRBENWjTkNRNl5btFEWjSIyG2uCKlFUCRoRMlVUSKJHeVYyyGXqZwW9QUGvX9Ab5PQGBf2sYJCVDLKCQV6SZSKQqm1s2PZQEI2iRRuen08cVRGvMFcURVEuLSqKFEVRtjCVGKJWMzQuhoYCqBJGVR2PHUWMRLhYnDNDMZOEaE8SOxqJo5k4mo1IpiSimTjS1AWh5Eii0XujIKKq9DlrK3Ek+7BDI4YqSiQHP/r+OidWNEyjo1ZbJPVCIZUu1BBVIiYLaXNZXlLkJYOyIMsltW6QlSKIBgXdfs56v6Dbz+j2RCz1s5JBVpLlxTAFryjCPsLky6peaaNAqtLsqojWppEjjRopiqJcUlQUKYqibEHqkaEquiJiSKIs50SGhrVAo7S5Ki0ushYXGWLniGNLGo0iQK2mo5VGtCsxlEakSUSaOEmRi0KKXBzS5ZwTQRSEUeQM1lqMsSEqNTJvIESI5IRExBkJE51LiBIRIjDhQYi6jFLZRICUUndUiEjKgjDKCokCDfJiOB/knn6WM6iJo7VuTreXsdaTSFJvUDDICvpZKZGnXGqR8mHaXhWxqgRQSVlsHjmS10fRIhVHiqIolwYVRYqiKFuMDYJoaKE9irqcK4YsLrwuaWwSsYkiQ+wMceRIh2lwjnYzotOMaDdj2o2YZiqviRByJImsn8ZSL1TNnZPJBvMFjB3ab4sAEi9vM3xeiaGREKo00uhMR5KhnnYmEaMgjBCxISJJmhB5L/VGlF6+g3yIIhUSLRpkBYNCIkX9rJBao6yglxX0+zndQcFaL2dtPWOtl4lQ6ufhdalVyoqSIvdktVokiVpVgmhMHFUpgCGSRNUvSVPqFEVRXjQqihRFUbYIQyFEiAzVBFDQGzhjMZYQEbK4yjihSouzBhcZEidpcWniaIZIUKcZ02nFTLZims04pMxFpGG9RuJI4iCOYksUu+A+ZzHWSkpciApJREjmVShLIkRyEgaDD9Gh6uSGUaMLsCFKBJihIAqRGDwmiCMfzBC8L/FlOXw8/E4qy2G9UX9QMMg2Roa6/ZxeSKtb7WasrGesrmes9nJ6QTgNBgWDohxFj4KrndQ2hchRWVLUDRpCyp8cdphXESONHCmKorwgVBQpiqK8zNkQGQqqaFg3VPUPClGioZFBLUUuCoYJsQsuccP6oJiJZsREK2ayndJpRrQaMY00iKE0opk6MVVIgoFCXH3hyNwMBdFIABlja9EgOU7vJVIVgjd4YGVtQOlFCA3ygv6g3Dx1rsJDmoiYw4M1nsl2ApWRBCI2jDEigkQpDcWRpNmJQCrD3Jch1a6U1LhBVtLvF/QzET29fj6MHIk4yllZH7CyNmB5PWe9l9HtS8RpkEsUqkqtK4pyKI4kja6kLKEYirVa76NaxGgokBRFUZTnjYoiRVGUlzH16FBlnlBPldtQK1R77KxEhqRWSMRQGsROuxkx2YqZbCcihloxzSCAmklEqyF1Q800Jk0sUeRCWpzDuroQcmCqmqEQEQoiCA/drGC9l7PWLcgLzyAvMUAjdhhn6DRijJFoShJb2o3oOfLIDGv9nEFWhhgRrPdyiqKkn+V4DEmoY2o3Ha1GTDO2GCNiSZTGKGIkYikIpKLEl0WoRSrIC3Gj6/VzeoOc9Z6kz4k4krS6le6A5VWZVmuvD7KaOAq1TVJzFOZFZRAhIskHMSdRIxMiXs9xKRRFUZQNqChSFEV5GTIeHarMCaQ+J9QHGYNzyD/8yGMXXN6qvkBJNHKNazdjpjsJk62EyXZCpxXTCuYJrTSi2YhppRGN1BHFkYgq50QEOYe1ToSZtVixrguRK0OelyyuZqx0c/pZQeQs7UZMmjim2xFnl9fxZckjT5yk28v50kNH6PZLeoOMxw+eHqaNiQ7wmA3VRKM0OwN4A9ftnGR2soW1htfdtYtOO2bfLduIo5iZ6SarXXGXW+9lZLknTRwTTcf0REzkbIgghTS8Shh5EUdlWQznRV6Q5cGlrpez3s9EIA1kvtbNWVnPWFrts7Q2YK0b6o82iCMxZxj2P6oEUu25WHqHdLughjRqpCiK8vxRUaQoivIyoy6IsJIqV9UNicX2yDjBWqkbqiJDkTPiBBfME9rpSAxNTSRMtZOhgUIrjWg1I1qNJESHHJFzuMhh3WiS6E8QR8ZgnWWQFSytZiyuZZQlNFPHzESCs54zC6s8dOAk9z98lEPHl3n22BLHTq1IGllQOyPRc6F8uQsxenc5XCTLds132DbT4pbrZnntXTu589bt7No+ibURi2sD1nsF1sB0J2aqE5PEjlIKgKTmKDwWcVRQFkWIHhUMKvvunhgwrPdEHFVpdYsrA5bW+qysy/JeX4wcKmvwUd8jSZ0rqpS6ECkqy5ERg69c6zRqpCiK8pyoKFIURXkZYQxYZLQ/rBeqokRVrVCw0h6mylXNVZ3YYjcq84RmwvREzMxEylQ7YaKdiBBqxHSaMa2GRIqSJCIKQsg5hwnRIYkMiYODdZb1Xs7ppT5r3YJWM2J2MqUReZ46tMDnvnKIzz5wmEefPMXZlb4IqXBO3osEqgb3kjIng/3hOrLiplGRetTImGrJ6LVxZJ0gJEJ6XiuNuO2GWd5wz27ecu8N3HXLDryxnF3JWFvPaDcd89MprUYURBEhclQEoSTiqMwL8iInyyRytNbPWOtmrHeDS10vZ2lFxNHiap+VbrD27udDK/A89+SlGDJsjBiNUuoqQ4Zz6o3GT1ZRFEUBFUWKoigvD+rRoVG6XFU3JNEhGyJCzsrjUZqc9AtKk9BTqBkz3U6YmUiZnkyZbMW0gwjqtEKUqBGRxBFuGBmKsJHUDGEcxjqsM3T7BafO9ljr5kxNJGyfTjm1sMqHPnWAT9//LPufOsXiygCPHNvQdnoog0TRjGyzzx3Yjz9/LjaIpDD3w+sXrL7DK+JoJ+l4xoR6HS+RrVuum+GNr9zDt7z9dm7cO8/Z1T6LKwNajYjtMw2aqcMXYq1NSKkrinwokIq8YJDn9HoFa70Bq10RSGu9jNW1jMXVAWdX+pxdHbC2PpDIUbAAzyvHuipqVHoKX0WNRk1hq3S6KlKkwkhRFGVzVBQpiqK8DLBhdG9CulwVGbLGEFnE6KBylLPiKBc7G5qmSmSo04yYbKfMTabMTIqJQrsR0WnFdFoJ7UZMuxnEUBSJcULkcFGEcRZjJFo0KEpOLvRY7eZMthNmJxKePnyKD3xsP5/48iGePbpEXnpsECOlhGOAEOFAUsCoxMp5hM+FXjsfG0RQ7fFmVK9XIlMk0yiSNJx7z/a5Nq+7Zw/f8XW3c/e+3ax1SxbXBkw0I7bPNkkiEyJIo4hRmRcUZUGZ5wzynG6vYK07YGU9Y607YK2XsbyasbjSZ2FFBNdqd8B6SKnLsiqlLvQ5CpGiYfTIy9yXbEynU2GkKIpyDiqKFEVRrmGqQbqpCyIrjVelbkgaocp8FB2KoypVTiJDE62E2cmE2ckGM52EditmoiliqOo/NBRDToTQqGbIYSPLynrGiYUeUeTYMZ2ysLjKhz91gPd9bD8HD58dRnnKSoiMWUqHRUOu9MC9LrgqgVQ9sUh+og3RJYsnmOYxN93iXW+7lW/92ju4fvc0C6s5WVayYzZlohXjC4+vxFEhoqgI80Ge0+3mrAZxtLI+YK2bs7TWZ2Gpz8LyyJCh2xdTiiwfRY0qC++iKIciadQMtkqpU2GkKIoyjooiRVGUa5ShIBqrH5I0uSpdThqujnoOWdI4pMqFhqsznZS5qQYzk6m4ygWRNNESMZQmsdQMRSNRZKMIjMU6w8JSxpmVPhPNmNmpmI9+9kl+/0MP8+VHj5MHG+1KBPkghIYOaeMndQ1SpSpW96OKgFkDN+2d4bvfeSff9Y476WaG5fUBs5MJc5NpEEclZZVSl+cUeS5pdVnOWjdjdX3A8vqA1XVp/rq40uf0Uo+zK/2hYOpnNae6MkSNymDCUCBiadjwVYRRPU1RURRFUVGkKIpyTTIcgA9F0agBa2Qtzo1S5VxIlYtCdEh6DUnd0OxUg7lJqR2aaIoQmmiL7XaaRsRxhHNREEQihox1lB5OLHRZ7RZsm2ng84z3fuQR/ugjj3HkxHLom2NCLVCttmX8RF5myP2wGyJ41sD0ZIOvf+NN/N3vfg0TnQ6nF3t0mhE7ZhsSYSrraXWZuNVlOf2BWHZXDV9XuwMWVzMWlrucWeqFlDqJGvUGJVkuPZ0qhzqZj2y8pfFr3YhBhZGiKAoqihRFUa496hEiGYTX3OQqZzlriZwIpMpIIQkW251WzOxkyvy0RIemWqkIoSCGWq2INI6xTiJDLhYTBWMcJYYTZ7us9Qp2z7c4e3aVX/7D+/jQp55kvZeFxqFiSDCMTNSOvXrsx9LTXk5UqXZig27EvAGPsxDHjtfds4d/8P33cusNOzh+Zp1WM2LHTF0c5ZRZIVGjIifLc7q9jJW1AUurA5bXM1bX+pxd6XNmqcfp5T4raxujRoOipMhL8tJTDiNHVa2R1GwVoc4IJHKkKIqylbkaRZGbn5//N1BZiW6cut318fUVRVG2DBsF0SgtzgUzhWgsMhRHLlhsx0w0I2YmU3bMNtk112b7dJOZiQazkzLNTDZoNxOSJCGKE6IkwaUxNhKBdHqpz/GFPvPTDbJ+n/f85mf5D7/4KR7af4J+XkiKlg/uZ2UwTBg/gcCGGp2XGZXY88E4YngVvKEoPUeOLfHBTxzgkSdOcM+tc+zeNsnhU13K0tNpp0PnvqrJrZhlONLEkjhH5Awu2KcnsTw3w4hPCE8Nj0TmZlh4JgIN5D3VwZpQD6UoirJVabXa2NBPrz5dSVQUKYqibMJQEAVrbWm+KhbbVb2Qc3ZkpBA5Gqmj1YiZ6iTMTTXYOddix1yb+ckG0xMpc9MNZiebTE4kNNKEOBExFCURNopxUczyesbhU+tMthKKrM9/+83P8VO/8Cke2H+CQSb1KlVkqLxAyOH8r7y0GOlhK/2brgCeUS0VgPeGvPAcPr7EBz95gEeePME9t8wxO93myOl1osjQbCRi4OAk6meMIbKWODYihKIQDbRSIxbHDmNqUbkQsTOMtJHUPdWU0PAFFUaKoigqihRFUa4Bqtoha8FRiSExUhBXuRAlioykygWb7XYzZrqTsG26yc75FjtmWsxONJiZajA70WR6MqXTSojjOIihmCgWQTQo4dDJLs4aJpuOX33vl/m3P/sxHtx/gl5WDAf6RRnqU8YP+goLIQNEwGQE7QhaDvJS3O8qM4TLiRkTRxhDWXqOHF/izz/xBE8dPsNbX7UH6yJOLPRpNWPiOApuglbmxhK7IIyclaiREWv1OJLIUiWNvPdB99S+1I1l43d8TRjV5JKiKMpW42oURVpTpCiKUkNsn0eW2xIhCoLIVfMQSagasYa+Q1NtEUTbZ0QATbUSpiYSptsp7XZMEsdEUYwLdtu4CBdZjp3pMcg82yYTPvyZ/bznd77EidOrFEH9VH1wqMUcrvRg2gAuPG7HcO+84eYpQzOu+jgZstJzfBXuO1FyrAt5sAi/UgwdA4NrXaeT8H3ffA9/8ztezVrfE0eGXXNNyqLEF+JMV+QZRZaRZRnrvZzl1T6LK2LVvbgy4PTiOifP9ji72md1PZOGr5UJQ+mDO13lUldSbGLZfYGAn6IoyssSrSlSFEW5irmwIAqpc1ZS55JIUqmajYjJVszcRIOds012zbelIetEg7mplJnJJp12QjqsHYqJYkmVW+sXHD7ZZXoi5cTxBX7yPR/ldz7wEMsrfUovBgqF95IyN36wV5AqPS4CXj1v+PabHTfNWDopNGNLO4ZGAo3IMNu03LPNElnP4ZUrK4r8sO5I0tsGWcFDjx3nrz7/FDfunuTmvbMcPtUljS2NNA7RIgkZWmMkahS5YTqls4Ykls+ER5riisAR6Tqq9BrVGHnqwSR5cDWIXEVRlMvJ1RgpUlGkKIoSBqY21BCNC6KoEkTBVCGJpBC/1YiYbI/qh3bOtZiZbDA7lUra3GRKq7GxdshFMTaOOHqmSz/zzHUi/scf3cdP/eKneObIEnlQDUVZUmV+Vcd3pbEhOuSAGHjHdYY373EksaERG9IIkghajfA8lmtnreGGaUc/8xxfvbApxOWiSnsrjWF5pcfHv3CQpw4v8LWvvY5BYVnp5kx2UggGG8ZISp2zhjiWWrKh82CIGoKnxAxt0cGAr3LlxgSQCiNFUbYwKooURVGuQsKP+NjzCCIb5rGT+qFGYoeGCtumG+yc77BjpsnsVIPZCTFTmJ5IN5opxOIsNyg8h091mZ1o8OyRM/yvP/MXfOTTTzHIKke5YK9dS5W7WtgQIdpmeNNeRxJB5KCdGFqJoZMaWqmhkRjS2JDGEFlD6WFn2/Lw6YKskHO7kiLAI6lreDAYyhIOHTnLX37+ILu3tbj9pnmOn+nSTKXWqBJGGIMzkESW2DlJxavcCJ30TCrKII7qd7D28FxhFI5DzRcURdkiqChSFEW5yni+giiyhiRxpKmlHQTR9mlJl9s2Hay2JxrMTjWZnEhJkpg4ScVqO5gpLK1nnF3OmZ2I+dU//hI//Yuf4uipVcqQ1uWDicLVhg3XqYoSRRa++zZHIzW0E0mVayXQaRiSGBLnSSKDc3JNIwdliICt9uHYVRItqr5+vQ/HYwzr6wM+/eVDPH3kLG999XWs9ks80GokQ2v2Kp0uiQxRJI9N6FsVR2K+ULkEVtuWHV1AGIUFKowURdkKqChSFEW5itggiEKa1KaCyEntSJq6jYJoW5v56WZwmJNIUaeVkiYJLk6I0hjnIrARxxa6GCyDfo//7//9l3zgY/vpZQVlKUYKVXSITcTC+PPLjQmTBZyBuabh7Tc4EUMxNCJIY2jEDFPoYifiydhqC5B7sch+6HRJWUVrxnd2BaiOw+MxRqJGzx4+yyfue5pX3DbP7PQEC6t9JtoJxlhssCesGvjGkTjVGRi6ExqgKILYHYquMWFkCOGqcaWkKIry8kZFkaIoylVCJYiMAWdMqBfZaKowFESRpZE62o2E6XbCjlmx3N42LU1Y56aazE42aDdT4jQ0Yk1irIsZlIajZ7pMdxK+/NAhfuJnPsLjT58Ru+pSLLYrI4WrRSSMUwkiC8QGdrfhtbuhEXli52klJY3Yy/PIE1kvznS175OihLz0LPY8D570FFfh+Xqg8BKt88DKap+PffEgcWR47V27ObHYp9mIiJwb1RkZ6WMVOxFGIpYgisRFSe5v6Cnl68JopIw2pNld2TGBoijKZUFFkaIoylVAJYhsNVkbIkSSJudc3VRBBFGrIT2Idsw22TnbYttMMzjMNZidTGk2R/VDLklwUcR6v+T08oDZTsSv/uGX+L9+4/MsLvXEhnnMZvtqpi6KIgM72vDaXYbIQhJDGtLn4kiua+TCmN+a0KNIaoqK0rCwBl856SVl8Co990qsGWPIc8/9jx7liUOn+dp7b2CtVxJFljSRnkZDYWQMcSzRo+rz5ZzBYjYXRjB8IG1eVRgpirJ1UFGkKIpyFVCJIUmdq+yVQ0PW0Jg1juwoZS4VQbR9tsnOuRAhmkjFWGGyQbORiiBKE1yw2z67OmBlPWeyZflX/+UjvO+jj5NlJd5A6a8+Z7nzUYkhFwRRbGB7y/DqXVJpFEeGZoLMU0MUGcpSLq5B6nSK0pAVsv7xFc9DQRQNxcf4Tq8wQ81Su0lHji/ziS89wzvfdBN5KY1gW81kmEYHYsAgrnTVduTzZLwnL0QUVb2n8IyEkKn2Gp5fZRbsiqIolxoVRYqiKFeYUS+iUBMSbJadk/5DkgolFstp4mg3xyNEDaZDytzMRINmIyFOYqIkxcYxLoo4dqYLGPJBn3/0797HA4+dCM5yJUUVLRg/sKsUUwkjMxJG8w3Da3ZbXGxIIkgcNFNIEqklGl5jYzAGvLeUpUSMlntw//GSopYyWO3namIkjEbCbWW1x0c+8wSvuH078zMTLK1lTHVEGMl3uQgjF8wXKpyTPkZFqB0bNm4Ne/EYMHIl5P8ikIbHMNySoijKywMVRYqiKFcQU4miylihEkVBEEVW3MTiqoYojZhq1yNEzRAhajI7mdJoJMRxgktSbBSJIFro025EPLT/GD/x//sQh44v4b2hLMth+tS1xDBSZOQCxsB8W0SRNRDHhtRJpMg5cNaH9Dnp1yNNaCVVLi8Mp9Y89x8biaIXSjicl4xq26YmjMDQH+R84ovP0Gg6XrNvF2eXM+lnhMFYMEiELIqqCJLgnESAsqIUgSjNjMK2z42X1a+NSCRFUZSXDyqKFEVRrhCGmrHCMEok/WWcDaLIGZLYkcaWVhox1UnZNtNg11zNdnuqycxEQqORiiBKE2wUYZ3j2EKPTiPiK48e5l/9zEdYWOlSlLXeQzUhMD6/GqmERxUpskYiRdOJ4XV7LcaK/XYj8UTOkzipJ4qC+5y1YPAYKyl1WQmHFzxfPeHFiS6c/wu5BtVXZ8hUe8kE0vA+efDGYzAURcn9Dx/BOjFgWFgZMNGOh/VFI2Ek4tvjMR6ss3gPeVGSV46D4QIMI0RhhxuuyQu5QIqiKFcxKooURVGuEMMaomC97SxEldNcJYgiSxo7Wo2IydCYVQRRk5nJRqghSkeCKEmwcQTW8eypdSaaEZ//yjP86//7r1jvZhQeylBLspkIutrHupUoGgqj0Lh1rgX37jY4I1GhNCqJnQn9iUQYORe2YcEacdjLCsPTC56HT2zuPvd8r8f4MVXTS44H6VpkwBvuf/QYkYG7b9/BwnLGZDsNrnRjwggj5+bBOqlHygtx5JN0urB5L8rdDx+P7V9RFOVlgooiRVGUK8DQZS4YK1R1RJGzWGuJQ9PNNHY0G46JdsLcZIOdc222zYjdtthup6GGKAiiKMZbx9HTXXbMNPnNP/kyP/Mrn6E7KELvITFU2Gywv9myq43NxEdkYLYBr7/OEjvpTRQ76VPkrDjQieCsCxUxW8hzw2PHPY+fkUhRRejr+ryojmMqhesnDDdOWuYaEv0bFNIL6aX6Wh1u11c7MTzw6DEOHVvkm992K6eXBky0asLIy9y5IJHC+4wxFIUnL6TGzHsfGr6OjtwAslTE1XDXtceKoijXKiqKFEVRLjOmihKFOqKqhkjmEiGKnSNNLM0kYqIVMzvRYPd8i+1BEEkNUYNWMyWqbLfjGOscR0532Tbd4Df++Ev8/O9/SVzGvMf7MNSvzMVqx3O5qPZViZuL3XcliEwQQ9ZAYmEiNrzlRnGeS2OJusXOEEU+NC8NkSIr8xJDUVrywvDFQ55DS568FikaH+jXj7favwtRqtTC11/v+M7bYt68N+KVOyJeucPx2p2O22csRQlnuyEt7SVgeA1DVMcAh44tcvDwWb7prTdzeqnP1EQavuDlHTbYlHsMvvTDSFJelCFi5IMRRYgo+o0fmupULvb+KYqiXK2oKFIURbmMGBm3yq/1tbS5qkFr5Kz0IorFaa7TjJmeTNk52xRBFCy3NwqiGBfHGBdxYqHHRDPit9//Ff77736Rwofmn2WJL0eD2fr4fDMR8FJQFxX1Zc9339X7qaIzRuaxgamG4S03VGJIokJJgqTOWYhjueYVRSmRokFu+PSTJcdWIfMy9q9fo+ot1b7r52AQQfYdt0W85bqITiJW4M2w3yQ2TDYsd847Umc4uCRmDi8pw4iR5dDRszx9ZJGvff1NrHRzJlpSY1RhjVwbAF/KCXkgz4MwKkJUMUSNhp8TL9Ei6hHH2nVTFEW5FlFRpCiKcpkYCiKk4N9a6R/jnCGyVowVIkMcObHebsRMdRJ2zDTZOdeWpqwTIogm2ilxKhGiKI4xznFysU8zcXzicwf4mV/9DEUpgqisBrdjx7OZQHqpsCGykjpoxhLlIYi05yuMxkVJVZMl6XOG1+0xWAuJ9aRJSSMRo4UkHm2j9FAW4L2hKKHbh0896TnVlTS3zY6j/pU43HeYXrvD8g03WyLnaSbQSCQCY60cn3Pypr0TlrzwPL00quV6qajqgCxw6OgiS6tdvua1N7Lczeg0Y2nwGq66C+JchI+cX+khy0ryqr6oDKYO1faR9asr81Kfj6IoyuVARZGiKMplohrEb0ibs4bIhUatzpBETuqI0jgYKzTZNd9ibrIhxgqTDSYnQmPWkDJnXMSp5QGNOOKrjx3l3//cx+kNyvMKotFw9qXHBDG0vQlv2Gl5+17Lm3Y67pk33DJlKb1hsff8hEJdFLlapGhjTZEniiCNPI1KpEQiUipXNQzBeU4iRR/fX7LQH4mi0eB/dJ3qYsyEtLnYwnfvc8y0DK3E0E5houFphWhRHIk9uDUiJOablgdOFPSL2km9VAxrhSxPHTpDM4245/adrPQK2s1Yombhy94ajzFGHAlDjl9RerKsJAupdFXEaHhFjIgq6Vw06l+kKIpyraKiSFEU5TJQjUGNBUdIm3NG+hA5SZ2LI0sSRzRSx2QrZm4qZddcm/mZ4DQ32WBqIiVNa2lzUczyek6We/Y/eZyf+JmPsLqekZeeYhNThfqA/3KQGHjNNsO33xhx27xltgntBkw3DbsmLK/YLl84VQTl+X791IVRJbruvc4QGT80W0hjSaFzTtLDht9tBopCprUufPhxz+JA0ucIJgubXZ9KGLlK6LXgG26yNCJoJJ5O6uk0Pa2GJ008aSwSyyD7twaeXvCcWq+lor0EDO+xFwMFD9z3yDE6rYhbrt+G955mIx6mMRqkl5OlSrWUa5UVJVleUlTCqPpeDnvxYWfDsww38KU6L0VRlJeSq1EU1dPNFUVRrnkqQSSRDYOxBuvqNUUjcZTElvbQfrvJ3FTKdDthupMw1UlIQ3RIIkQxq92C9V7BoNfjX/+Xj7C2PpAIURBE41zOf94tcM+84RtvcEy1DK3E02nAZBBFEw3opIZ33uy4cVLSvZ4vEp8YDcCrtMSilDP01TVHnOds2Lit2XJX79vsOlHfdu26VWlzBtjdMeJ0FyHRodTTbniaiQijZupppxI5ihwkkWH3RG0HLyHVtSkKadDri5Kf/50v8uiBo6z3Cla7OcZFuDjCRTFxHNNpx0y3U6Y6CdMTKdtnpP9VpxnRiKXWzQUBb42Vz29lKW9G396X8zOmKIrycuZivhcVRVGuekxImyO4f1UDSedC01ZbRYkszcTRacXMT0kPoqlOymQnYaqT0khjGcTGMdZFDHJYXBkQ2YIf/w8fZGm1T4n0INqw/w3PRoP88eWXEgvMpoa37I4wxhJHhthZ0tjSTC1pakgTmRqx5e03RERV9Cdsozq+6lgrMTL+OiE64RGxWV1rG0I6pa+pmXA/QH4BdNZQBJtqG3ZQ3281r++XcD/nmvKKpD0akjjcyzhEASOZbHhsraGdBiHxEl7/8ftbll6iX6XnJ3/2rzh6fIGzywP6ucfYIIzimCRJhp+1qXbC7ESDuakGk+2EVjMmSUQYRUHI2+EkESmLXMeX7MQURVG2GCqKFEV52VAfuI9+VTchShQc56whclJL1G7FzE6kzE81mGknTLRlkNpqVBGiBBdFlMZw/GyX6U7Mf/rFT3Lw8FkxERj2mNk4Nr2c49RqX3fNWSZTiaYkkTjApVFIbYugkYh9duzgpmlDO95ckFTUpV41+K4yG0ovYkMEaLAR8CEXbrh89A1TCaDKjGJIPTx0nutmDDgDM00TIkAQRZ7YeeLIE0WeJPRIEsEg64sglohYpR022/6LpX6dfLgOZSE1ZuvrGf/nez5GWWQcX+hSAjaKiOIYF0U00pipdhBHEzHbpprMTqW0mzHNJCKJxRDEuVEKaBUpqlJNLPJZVxRFUV4cKooURXn5UA2GQ2RCXOfCL+whUiFNWg3tRsRUK2F+usHMZMpEO2WqndJuJURVhCi4Bpxc6DHbSfjF3/8CH/7sUzLw9RIlkqL4UQPSShtUKVXVso3xpEuLBa6bMDjriZzHGo8z8tg5ERCR9VLLYj2TKexobWwKytjxblgeFlTmCT6ceznsuirFLqWHIpf15NrLq2IuINfMmWob4X6Ft1ez8X1XC5qxbMcajxFPNlxwnjOm9i7vMUbOtyg22d5LQHXPq/teeChCv6pnjy3ykz/7V7QS+RwZY0MqnQjvZjNhqt1gsiWpdPNTkkbXbkQkiSOO7NAkxBobGsPWImBVRG78oBRFUZSLQkWRoigvC6qMreEv6EYEkUQQZGAZOUscWxppRKeVMDclLnOTrYSpiYTJdkwaaohcFOGcY2U9x0WO+x56ht96/1chOIf5mtNcXUyMD8LHn19qTHCEm0yN9AtyRqyxHUTOk7rgzOZEFDkLcWToxGIKUFE/h/qyzc4prvcX8pUn2kjgiA23TC7UFZUl9HNDXuvfFFbfMK+oR3Ys0IpEdBkqUwMgiCPvPb4MImh4wJ5uttH5YnwfLwXVPsoyNGXF8OCjx/mNP7kPjGF5PcNFrlZfFNFpx0y2UyZaCTMTCXOTTUmjSyOSyIowqhoOh8lYMCFENIzMKYqiKC8YFUWKolzzmPA/EyIPVXqRrdLmLETBcS6NpSfRTEdE0VRIm5tspzTSZDhYtS6iX3gWVzP63S7/x3s+TlF68tKT59IYtB4R2kw8XC6sBWdEnFhTEoWIUWI91pY4W2KNJwqpZc6UtGJxQHu+Y+mqdMogttsG8IW4p5WFiJ48D41Jw8WwjMIneeZZ63l6uWxrJF7OvW7j1zIy0Ek8lioKJudjkYlS3O2qjZbek+eepa5sZXz7LyW+FjHKC09eSI3R77z/qzx64ChnVzJ6mcfYIIzimCSOmOzEUtPWTpifSpmdbNBpxqRpRByaDIvAl7opO6yZGxVmPd97qSiKopyLiiJFUa59ql/KTfgFfRglCmlzzhBV5gppxGQrYW66wXQnYaIlgqjVHBkruNjhjeX4mR6znZif/Nm/4uxyT375L8vLOsh+PtjQVNVZiGyor6nV9lT/0Mt1kaNPQwTnfFTnWBcoVWSsLEPUxoTUNSPCKMsgy2uRovDeopB11wcb0ww3bHsTMUQY6DsLsTMbhFRZylQUIsaKUvYtk2FQwJmaKBrf7ktNdZ5FUYqYLjz/5899HF8MOH6mG4wqRIC7OKaRxky0EyZaIozmJuXz2W5EpIkliiwuRDxdVSdXiX81XVAURXnRqChSFOWaZjgWrMwVqr5ERtLmIoekzVVRombEzFTKTCcNEaKEibb8Wl9FiIyNWFjuM9VJ+OXf/yJffvg4pQ9pc2G0e7kH2efDINEfhoN/OffYhahZ/VhDhMb74MR3EePounhpx+C91Gz5EKmqhIcL3yreh6hREKulNyNRtEm6V/V0s3kjlvOpMMFNkGALnhdi/pAVMMgNgyCMVrLae0YPLwvV/jwj44Xl5S7/x3s+RiM2nFnuY53DOkcUxURRRLsZM9kWcTQzETM7mdJpxjTSiDiyQ1c9G9z+5LFcjypgdLnPU1EU5eWCiiJFUa5pqmiIjL2DuUJIm5O6IhtsnC2thqQozU3Kr/ETrZiJdkojiaSGKI6wkWOllzPI4eDTJ/jtDz4EldVyUTXT3DjovZKYkNrm/Sg6VCmOSqhUqVZRzZY8dSH9anyD5xlYe8CHF/IiGAkgA3Rfuygl0p/IWjEBKItqfVjujQbu1bGNX7/68+o42hFEVt5ZlEYiRKWhKAx5bsgLQ38AeW7JC4kWrQ88g3yjmLuc1M/NB6fCwhseeOQYH/zEYwwyz3I3x0YOG7lg0x2JUG8ldNoJs5MNpicS2mlMGrmhRbd8xm24r0EYUXMEHDsWRVEU5bnZ7PtQURTlmmA4+Au1FSKQQs1F1ai1qiVKIzrNmLkJ6Qsz0YrptFJaTSeCKIqx1uG9YWF5QCc1/NQvf4pBVgSnuaHV2lXDUGCUUIRlRTjMIhS2+FLMEMT1TWpwDJ7ZZijBqZtU1K7p+eYAvRzWMlFiEpUR0VOWIToU8F6Oo/SQl3BsSXboARNqjqp9VtOmx+Kr+hzZVpYbshwGYb/ehzS6wpOHmiWDiMDNtnc5GYq/yrEP+JU/vI/l5RUWlgdib+6CKA823Z12QqeZMNmJg+lCTDN1xEOLbnGhqwQu9fTRK3SeiqIo1zoqihRFuWapokRDC26D1FsgrnPOSRPTJHK004jpThzstxM6LRFGSeU2FzuMc5xZHjDVivnVP/4S+59eqPUj2hh1uNyRh/Phw//6uccTrLFLiWhVg3FKL1EEK450zsKOCUOVkbaZ8NnsOV7spg+twPsf8nz6gGdpTaJCZRnuR4gQVZbcxopIObPsObVaEwljU53hfkPUoxGHmhmC0UUBgwHkIVUuLyR6hBezbow47MXBqnt8+5eL+n49UJYlpfesdzN+5n98hkYEZ5b6GGuHwjyOIjrNiMkgjGYmE6YnJI0ujcWie2ND15A2WgmioIrOuXeKoijKBVFRpCjKNcmGgXMYBEranMGEAWMUDBYaqaPdjJmZSJnoJLSbMZ1WQrMx+oXe2IhB5unnJU8dOsVv/dlXRQSUo1/4xwfyV2qwXVEdQ1W6Uxay1PtRqt8wgmBKaXjqPGkMs01oRM8dRdnsPDsx3DgDOyZgset59Ag8eQIOHIHHnoFHn4ZHn4KvPgGPPAUHDntW+/CKXaHGKWxwfLsVw+VBiM61xGIcQuRr6IYnvZKyXFL0BsF8oSxhte9ZGVz5+1Xdn7Lq41R4ihK+/NARPvSJx+hlJf3Mg3W42GHjiCSO6bTC1IiYmUjptGOaaUQcy+d6aCISUkWrHwg0WqQoivLCUFGkKMo1yTlRomEtUYgSWUk1SmJLuxExM5EwNZEy0YillqgVEVWCyDk8lhOLPSZbEf/1Nz9HP5PieF9cfW5z5xDS1LyHwvuhM1xlj22Q5qnWSMNTZz1JJI51F6I67/oXhQHumIOvuc2yb7fhjt2GV1wHd98A99wIr7gFXnkr3HPb6PFd1xtu2GaYbBnykNpWbX/82lbP68tnmuF8QmNUH8RRWYoartzu8HKA3kv9UlarKboa8LX+RRjDr733K+SDPifOihudsaPatmYjptOUiOZUJ2Gmk9JuxqRxJE50IUV0FC0KNt0aLVIURXlBqChSFOWa45woUUgfqvq31KNEzTSi00yY7iRMtmKJEjUTSZsLosi5iNVeRjON+PAn9/OVR48Hl7bRkLr+6/vVNNistEC/qAbCltJb8tJIdMtI5My5cH2COYKzGx3L6udWTVUUqVpeDbTTxEjkI9htF14iNVkhx5KHOiJMiNwg6WxZVW+0yX4rNjwPRhCpk+2JqYORNDkTUuWQ8/NexLExkESG1YHHX2A/l5PxffuyxHvP0kqXX/q9LxA7y2owXXCR1LglccREMxlGi6YnUiZbEi1Kas1cR9GikdFCFS1SFEVRnj8qihRFueaohJCp1RLZ0K/FDqNEhiRyNNOIqXbMVEibm2iKMIriCBuiRIWHhZUMnw/477/3BRl8h3yneqSh/vhqGnSWwNpAIkTSQ6iqLQpNTZGDd0Yar9pw8DXNB5uc03iUJbQ4YrJp8GXolzPsCyXGBsbW9hGWxw7iKLwethU00wbqzyshY4HEiOtcFswcinAcIpTAGE8UVRFCmZ9ckZUq0Xg1UbnReQwf/dxTPPnMCRaWBxSlH0WLXESjEdFpJLSbCVOtWKJFDRFMsd0YLaqiQ/J3MPobURRFUZ4fKooURbmmGI7zQl+iYZRomEpUjxI5Os2Y6Y6kIbUbMa1mQhIEkXUOYy2LqxkTrYjf+bMHObXYDSloG9PmxgfW48+vJCXQLeTalN7jvRHXt1IiKJWYyGv1OJVY2GzcXF9ezSuRYwxExmOsx7iQ1hY2VpSjrqUm9CxyUZhbTy8L162WQrcZlSAyQGyhmUBelOSlZ5BL+pmkzPmR610lgIIYXM+unjtUHcnwGAFfyHlkueeX/+jLpLHh7EoG1mCsw0YRcSS1cJ1WTKuVMNmRnlrN1JHENcOFEPkbiaNR7tyFrrOiKIoyQkWRoijXFKOULxmhD523Ql3RsJaoFiWaDPUYnVZCqxFJipKLsC5iUMBat+DM6WV++wMPSWqWlwL+uuNcRTWovdroh/S1ohRziEoc5KWcS9UrqMhHwqFun13HjJ2jYaOQaUYQWREsxogJgjGjxq2G4EBX3a+gcHq5RLPq4uBCGGTbqfVEVmqgrIEs8+SFNNL1VVSskPMsSsgKz+pAtl4XJFeS+v590I7eewrggUeO8dn7nmIt9MeSNDqJGKVpRLsR025ETLZjpjsprUZEEjux5x7+GDDqWzSKomq0SFEU5fmiokhRlGsOU9kQB3EkFtDyi3nkIHKGNHG0GzFTEymdVkw7jWg1YpJ4ZK5grGFhqc/0RMz/eO/99LJcokQhP2vDL/tXwcB6M6pjWh2U4pIXaqGKQgRR1c9nMIBBBoNMIhR5ca7NeH2b9eXj5y5pcB5fllgjJg4SDRql61XCqhJkZQEL68GFbZNt16cq4CTnAvtPe/af9Ow/WfLEyZLHjnm+8rTnvidLHnrGs9otccZTlCW9Qcn6oORM1w9NGYLfxBXnnPMsPEXhMcbwa3/6AKmDhaUexliMq6JFUaiDkyjnVFtq4xqJ9C2qUugMo8a8w2CRRosURVGeNyqKFEW5ZtjwD1aIGoi5gsWZqp7EkkSWVuKYbIvTXLshA8sqSmSjCBs5stwwKOD4ibN87PMHZaPjhTbXCEvd4EAXTA48EkkpitGyvIBBiCgNLtKZrVrXAw0HvuoJFHBGUuXKEpyrDf6DsPFejtGHjdT3PT5or54bYK4B++YNuzpw8xzcuQtecwO89ibDK6633LHHsNIzfPkZz+PHSoocVnpssOO+Whg/TwDvS0oPh48u8qkvHZR7lHusc1gnn9M0jSValEZMtGKm2hLxTCJLZEO0yNXq6ywSMQrRok13rCiKomxARZGiKNcOG9zE5IkJ9S7GikByzhDHjmZIN+o0Y5qJRIniKAw0ncVay5nlHrOdmP/x3q/Qy4pzHOfGuVrHlgYYeBE7/RJKL8YEJgyQPVB4I9GJ8Jq18pwxwXP+sxcioJuNcuJkMA4+6MnSV/2S5HkRUvoMhl5wp6siN+P7r6gvn58w7Jm13LbHcvNOy95thtkpw8QERDFkJUw24a49hjt2Wb5ypODzz5QMzpMaeCXZ7DzlmolF92++7wFi56WhqzFYZ3HOEUWWVkNEfSuNpPlwIyJN3NBgop5GKoKo/reiKIqiPBcqihRFubYY/go+brAgv5gnkaWZOCZaEZOthHYqUaJmo+pL5KRRayFF+8dOLPLxLx6UgWMtn2x8QDn+/GqgfjyDEvKgNIpSojhlWKMSREVpyAt5vlhLL9tsm5udp1xz6OUj0wZfypqmcr4L7nBS2wQeQ+5ln+uD86eyVcvGr3fTyfsHuZHUPC9peomDTtPI1LY0U0mffM11lsx78prhw2bncqUZikIvFt2l9xw6ushn7nuKrPBkBUPDBeci0oajFaKdnWbERDulmYgZQ2St2HJX0dOaGx21HxIURVGU86OiSFGUa4LRGE9GedaCCXVEEhExRNYSRyFK1EroNCMajTjUEjls5CQtyVqW13I6rZhf+5P76fYLGcgXJUWIdhS12pZqAHu+Af2Von4sqwM4tlIyyD3rg5J+LvU1WV6S5wX9gdQSOSuKpR8svDc7n82WVRRlaBBbePJyOLSHcH+q+qEih3wQTBFy6A08q33ZZ53z7cuE1+baMtgHMMaL9beVx96HBD7vgwCTerJ2Eno0XWD7V4rqmKqpCHVXZQkYw2+//6tYSpbWBiKKnHxuIyfRzlZDLOUn2yKQ0sTiotCHakNNURUxChFVVUWKoigXREWRoijXBNUv3wawUi0RismDDbc1RFFlsBAx0UpoplJPVEWJrHNgHaU3rPVyzpxZ5uNfOAhV35irbQT9PKiEW17C5w97njwjgme9L+l0ZQl5Dstdz7OnPA8/W/JnDxd8eH+xQeSNz8fxwfigBLJcpjyT1/JC9k+oHapc4MpQ01QU0O171nrn334len0tqmGATjKyXgdJb5RJlokFeUjVC41il3vBfe8qFUZsclyVi97BI2f50oPPsNYrREBai3XS1LWRuqEwmmhKvVwjiYjrLnTD6GnNbEEFkaIoynOiokhRlKue4SA5iCBjJErkKhtuI72JYuckda4Z026JGGqkEUkigsi6CGsdy92MdhrxF5/az2ovl4hJMSpCqf+Sfy2RlXB4yXNsueTsmmdh1bPcg+5AGnp2UsNU03DdlGEmlfqgi/kSqK7HWh9KpBdSVkg6Wxw2lpcilspg/V0JzV4+qik637WtllVzZ2AyNljjia1EiZwF6yRSKCtKVKgMZhIGWLgMJguXQmfUr0VZSiTPY/jgJw8QW1heH2BDtMg5J1HQNKKRRDQbIoqqnkXO2mHa3NCiPogiiR1dmmNWFEV5uXIx34eKoihXBBnYyeCu+vW7qp2o5s4aktjSSCNpdpnGNNOIdhoTh0GlcRYMLK1m+CLnfR8/gMFItOECg/WrmfpAt/Cw0IdnV+DkSsmZNTh81vPMgufIouf0ujSkvX7O8o47HDPNytb8wgPmDYN3YLUvIiQrxcWuCLbbeS6230VoFJsX0M8M/Qx6maxfiaQLXevqeBoJtFN5T3XfnQuNZDGyLS+PiyCK+gUs9V/6+1kd41Cwj71+MQyvbeiP9ZVHjnLk6GmW1iQUV6XRRS6i2XC0GhHNNBKb7kZMGkfEcTBcsJXZQvh7CZJoGDVSFEVRNkVFkaIo1wRDYVRFi2wlkkQQSW8iS6fp6LTEWKHZiEhTGVCaUEvUHZTEkeWTXzrI6TNrMmgOXUzrA9xrafxoJMuK1++Cd91ieNsNltdc77hnt+GePZbX3WR55fWWO3ZZds0YZlow27Zsa210Kau2tdm5V18W3osoKSBYzokAKir775A+Z40YO5TeMMjEJCEPNUwXEir1fTei0Pso2H/L/Q8mElXtV83QwXtY7Xu6Ia2v4kL7uxhMuA63Tli+++aIv7Mv5gduT3jlnMOd57pdFKFGKy89H/jo41hjWB+UmJBCZ50lTkQQtVIxXphoxuJC50Iz1xAhctXfSBUtCgf3oo9RURTlZYqKIkVRrmqGgzgZEQ9FkUUGfc4YnLPEkaQVdRoJrTSiEcvzKJLBpHUWYy1nVwa0Ust7P/IomFEtB2HwXB80XksDyNjCzo6hnUh9SRVViZ00W40dpDE0U4giQ+xgMh0JhguJIzNmOJF7aQpblpJGl+XiapeXUmvkvViklx7W+4Z+YVjti2h5LlFUf63hgsNgGNHLIN9jkA2VXqJjZUjLM8aw0pdeTJe6nqi6Ht+wN+J774i5bT5i74zj1jnLt98W8zfuSmi68XddmPHPlw+i02D41Jefodftcna5j7UW46Shq7MhhS6NaDUcnRA1iiP5cWBUTyR/I9RS6Mb3pyiKooxQUaQoylXNMEK0aeqcuG45C3FsaCQRrVZMI41opjJ4jFyIFBlHXsqv8E88c4rHD54O0YZQqB/2Vx9IX6oB9eUgryy5TejZZEVQ5MFwwBiJujgjIslaw2RapVltPkA/3+OsgJUurGfQHcAgNwxyyAoZlGelods3rPYM6wPDet9wdl0ETJ3Nrm/9OBpOjjsP6XjifBcMHzwUhaEszdACHANnulCGc9ps+y8UC7xtt+M1O+SgXKhvclau53WTlm+5KeFidNGmn7lgz720MuCTX3iKovDkRYkx0rPIOUeSVLVF8dCmO40dzlV1RWEKn4GhHNrsRiuKoiigokhRlGuC2sDdUNkOj4rKo8iSRI52U5znmon8kh7HVZRI6onWugXt1PGXn32SrCglShQ8oi/1IPpyU3rIi1H9iA3zkBkY6q4keuScCKckGqXPUbsG4+Pm+nUxwPoA1jJPN5P+QYMcegMjNUQ59LOqlsiQFYbuAE6seEKboeE0PkYf3WOh4YKbWhDCEERQESJThdQ0Vb2XygKOL8kJb7b9F4oFdrYMr98ZYY2YSjRiSe9LnExRZLhrm6Mdj7/7+eMZmVOUBj75xaexFla6BcbKZ9g6sZ1vJBGN2NFuRrSDKIqcJXIjA5LKcIEqfe48AlhRFEVRUaQoylXMcPBWDeiGjVtDeliIFEXOksaOdiOmmUSkiQwa41pfImMsS2sZviz53ANHhjUo9UH6tYz3cLor7VrFmEAGxt5XAsmPBAbSbLURyYmbTUTEZgNnH9LoegWs9DyLa56Vnpgb5KUIo/WBoTcwrKxb1vqG9T6sDWCx64dRq3Hq+63fhzKIPWPA+5EgGuSGXgb9PDR1DbbjpTecWJMtXKr7asIX5Vt2O4wR44eJBkyk8riZQuokHTF2sKdjL+qLdfz4fHCi8x4OPHuW06eXWFkbhPvpsFaiRY0g/BvBgl4+7xIpqgxIJIWuLog2u6uKoigKKooURbkWMOEnbsOoZ421ButEFCWRpZE6mg3p5ZImMjnnMFZ6Ew3yEo/hwceOcujIYvhFfuOQ9FocMtaP+cSqpNCVXowIGAoDjzNBCQWMlQjH8PnYnNqAvRJNlSg62YVnFj0nVj3HFj1nVyRi0+0bun0RK6sDRBQNxH3u5NqoWWy13ecjXHwQRtV8kI+iQ6U3eGR/eQn93LM4GDnPXQosMNOA22YdnQZMtmCm5ZloeZoJNBOInMcaj+z5hVF/p/ee0nu6vZy//MwT4bxLMKFnkbMkiQ2fc6kpajYcSWSJqhQ6ail0hBq8mkBSFEVRNqKiSFGUq5aqhkh+rR9FiCrLYWsMzlriyNJKJVKUJi6kzkmqUWWwsN4vaCWOv/rckyGNS/KUxoex9QH7tUAlVEqgF+yxCQYEhGuYFzJ3BqzxIfIic8xGU4IqkrNhkD62fDmDJ5fgqyc9nztU8icPlfz650p+9wsFH3q45LP7PfuPlDxxouTZswVPnC54etmT1URRfZ/1qb5vG6ImFjCE2q9g9Q1yDpWuLUqJHq1lIQVtbJsvhEo/vHLekkQSGZpsQKshduFp5ImMlxqt8Jlcyy5+j/XzHh6zl51/9oHD+KJgrZtjrMU4g3GOKAriP3LitBh+DHDBnr4eLaqn0KkeUhRF2RwVRYqiXNXUf92uBnhSYzKy4k5iRzMVg4U0cqG+wskg0lqMMSyvZRRFxpcfPY5lNHBmbFBaRUWuFeoD6X6YlyGiBmCtnI2xMiEu2pQeIrsheHTO9dhsuQfmG/A1ewzfcJPh3fdYvuMeyzffaXnTTZZbtlkW1jwPHvF87EDB+x8t+PBTJWd6IyE0vs36tqvnJZKOJhEvyfErvJg8EKJ8RSmpc9V0as2z3t+4nxeLs/Cq7Y5m4oeRomYsgiiOwEVBWHpPUcJi/8XtuTrdMnxAnz2+xLFTS6x0sxD5qaXQxRFJiBa1GzFJbIlCCl0VJap+QDC1UKAGixRFUc5FRZGiKFclw0FbeDCKGo2iRNaO6omaqRSbJ4kjjUeuc1jLoPB4DM8ePcuZxfUw8NxY3fLihrJXjg0DXA9RcJnzeMrS4EtJacvzUHdTiiHBIDPgJaUqaKVNp/F9GGA1g6fOeo4seZ444Tm2JKl0p9Ykney2nYbXXm95ww2WHe0qYnH+7VXUHwO0gmlBUUKRSx+kwktdUVFYCg+DYLhQeljqyfqX4ovNAA7Y1oT5CUsjhokmxLHHOYkOARS5XE+AXubphccvhPpnsEqhy/OSh/cfCyl0UmBlnMVaS5pYGomjEVuatboiiRYhpiTVtQ8/KshSRVEUZZxL8d2hKIrykiCDt8piWJ4PC8gtOGeII6mtaDUcSeRoJI4kloGjRIks/UFOGls++oWDZHkZUufCTq5VNRSoCwxCBMgZSTcswmmuD2SeFzJlhURdhtGDTYTKuFipL+uXYraw0BUTBYCZluH2XYabt1uum7fsnjXsnbXcNGPE0KG2rWp+oX0AtJ0hy8WgISvEXtz7akU/jIZVNVTPLpbDKNFm27tYDHDXrMMZEXuN2IvYMKPPzbDeqYTFXklZXqKPVPURNYZPf+kZTOnpDSSFzhqDdRYX2RApks99M3EkwYGu+puh+vsJAjgsenEXRlEU5WWIiiJFUa5OwsBtOLj1BhN+9q7S5yJriJ2lmTgasSNNLElInbN25MS1vFYQWc+XHz4GGHwZBrM1bVQx/vxqphrX1vWdrf2rbkO9C14iRFU/n7wAHy7Ac30JVPuoiwyLCK/rpgy3zBnm2oayhKU1z+HTJV85WPLnD5b82UMFn3625GyvVuNU2/b4ta4/90BkPIPc0x9Ad+BF1JWQlSKSxApcDBbW+579C8Wwvmp8exeLDQL8lllH7Dyt1BM5KWoqCi+Rt1I+Q0Up6z67dGlMHqptVDVTTx1dZHWty8p6jjFB7FtLZCVVNIksjViEURxLFMlV1tzBzlzrihRFUS7Mc30fKoqiXDEM4Vf5MKiTtLmQOucM1lriWFKI0kQGh0loYmmsAyzeQ1aULC93OXJyGeBFuYRdzQybnAbr69KbYX1RUUg6XeklFW0QevxUI+Tqimw2YDbhdRO2FVtYHsB9x+D+Y56DC57jS54za7CSybqNWPohNSKpDRqPSlXzaqqoi4rPHfd8/nDJk6dLzqx5Vtc9vb6nN4BeJk1jy1KiNKdWS852Nxo4VNu7WCrhN5XA7glDEokILAsYDCDLgg15IdsvSjm/QytiiX7JKD3ee9bWMg4dOUNWBCVv5PNtnSOJw5Q4mqlES+PQ32lDtMhWj8Pf03nutaIoylZFRZGiKFclBvBh1DasiQj1RBItCiYLURgMJmFwGHoTVb+m93NP5AyPHzzF2nom6VfBr3p8wDz+/GqnPvgHGaiv9mXpcNAbIhndTNzZigKy0rPeLzmxLOlmFdX2xkWFrw2gLXDzFLx7n+M77nZ8zS2OfTstd++1vPp6w703Wd50q+Wddzu+6xUx774z5vU7R7176se72X7qz9cG8OSi53NHSj74WMEfP1DwB/cV/NXDBQ89U3ByqWR94MkKzzOLJf1QWzS+rReCB26ZtjgrdubDRrGloajqnAqp0yKkzy10L43cHt+GN3D/I8dwBvpZuSFaFDv5IWDU0FXS6sSBLvyYYMH48JnQuiJFUZRNUVGkKMpVx+gH7ZDyU0UUqnoiI2liYrJgSZOI2IVfyaPwq3hw4BpkBY3U8eWHj4bB5viQ8+VDVkA3F6ttE2y381xqik4te548WfLFgyWfeqLgLw8U7D8jA+W6ENmM+nKDRE/S2NCMDRMNmGnDVCtYVUeeKKrS+KSXz+4pQ1VWNLq3F8aESM2bdxu+a5/lB15j+bZXWN54s2V2wnBwwfORx3M+/HjBF54peOTkqJ7oUrjPWQP7ZqX/UW8g0alBLtc4y8NUeEogLz3rmTjPbbTvePFU5/HwEycxeHpZiQl229YaqSuKqr8DiZjGVa8iE2zsEWFUXXVT/e+5boKiKMoWQkWRoihXjMhBu+mY7ER02hHN1I4GzUMxFEZvVQodYTAY7LjTONRVJJY4pM7ZUIxurGW1W2DKgoeeOCkCYJNaohcbVbga8EDmYbErtTeDHM6uwaPHS+47VLL/pNTC7JmCW+fhjvlggBBO3I+NkatrstnyTmJwRpqWRlbuow33a/jYiCBKY3HEq9eyVNe6GpfX91HNYwNtB/0cTq1B5h1z0wm37Ul4w+0p77435Vvvjrh9u2H/gufo2rmW3y/0nhpgJoXtLYsvJfqTBzHUHxi6fcMgpO9luezl4NmC7EWYLNSvdzWVXvo04eHwiRWWltekX1H4bBtrQ58uRxpbpialT1fkqkhRiBKFv6PqHtXvp6IoiiKYffv2eYCyLDdMRVFw5syp8fUVRVFeEM7Cnu0tbtjd5vYbJtm7s8VUJyZJrNRreMhzz3o/5+TpHgePrPLU4VWOL/RYXyvEac5Jo9ZG6mg3ImYnUvbuaHPjrkl2z7fZOddmbqpJ2mwSNxJcnHLw2Cpl3ufv/sQfs7I2oChKfDn6Rf9Cg+edcw3uvm2GTjMKv7yDc5Y8L3HO0G7GLK8G+7VNGOQli8sDTp/tceJMj8WV86/7YrBhioHbJ+CV2w2TKUw1DJ0G7NjeYGZbm7zwnF1DLLRX4Pia58xAxFReuxYLy32eObI2FCw2DKQjIDXwQ3dadk9ZJhuedsPQSj3tFJqprDcooNs3rPQMC2vw9ELJb361oFtCMRbJqeZ1UTTdjrl5V5vX3jbJ6++cYm6+iUsibOg55awo2/4gp7fU55GDq3zsoUUOHlvjxEKPQYjgnO++PhcR8DW7LW/e45hqQieFxHmckzS5rDB4D/3C4CNHa2aKjz6Tc3CpJGTTnZduL2f/Mysids5DJVwMIiYjZ3HG8G//6Tu4+87ruHFnmzIfkPX7DLo9llZ6LKys054s+cvPnODAoVVOL3ZZ7eb0+jmDvCQvSrLCkxclZell8sNM0ovi7luniOzzk1bPnlhjYSkbX6woyhZnbm4bbmiKNJquJCqKFEV5SZmZjHn93XO8/fXbuWl3m6lOQunh9GKPhcU+692cLC8xxpAmlsl2zLa5Ju1mRJF7jp3u8tATi3z+gTMcOdnFgoiiZsz8VIMbdna4YdckO2db7JpvMz3RJGk2cEmKN44jZ3ocePIo/+I//oUMAosCH4wI2GRwXqfdjNgx22DHfJO/9o7ref0rto2v8rxY7+WcWOjx4OML/Pknj7D/mSXKS5RnVQ2eXRjMdyzcPg27JgydBGaanp3bmiRzbVabE9x05x727OiMb4azy30+9KkjPPj4AidOd3n2+NrwGE0QRm6DKJLUuU5q6DQ9rYbYVvsw0F7vGZZ7hjOrhmcWSn7jq/lQFFXiq37NnTXctKfD171xF69/xTy7d7RoJBHdQc6pBRGUvX5BWXpJm0wsk52EbbMNWo2IvCxZONvnqWdX+NgXj/PlRxc4dTY0LroILNCK4EfuieikhqmmmEbEVfNbH6zNMQxyA5Fj0Orw+cWYb3rbdey7eQpbd5UA+oOcj37+OJ994CQnTvc4eGRFeg6dhw2iCKRGyBh+8Nvu5vve/Xr2zDdxlOQDEUVra11OL6/TmfEcPr7KBz9+nONneqysDegOCgZ5QZZ58lLEUVFID6QyuOed/0g2Z99Nk6QR3HPbNN/ytj3MTKbD10rvue/h03zsCyc4ebbHsZM9zq5mNdmrKIqiokhRlC1EI7F8w5t28u6v3cN1O1oYYzhyYo3PP3iKLz50mlNnuqz1CgaDkqKUOpjIWZqpo9OKuGlvhze9ejuvumOOyU5Mt5/zwOOL/NXnjnPyTJ9OM2bbTJObdna4fucEO2db7JzvMNFuDEVRv4DF1Zw//OCX+aU//IoM2ItiWIxfcSFhZJD6mLmpBv/qR1/JK++YHb7223/2JF94oPbvZDB/aDYi2s2IiU7EbTdM8co7Ztg228Qaw/L6gA9+/Ai/+f6nWFl/8b+gV4KlEi0RsD2F12w33LHdsHsKWqnhzACeOgv9xgTf9F2vZMe21nAbK+sZP/2LD/LVx89SFCV5ESIJNVFUCa/UwHfeYrlzp6UZw0QDWim0m540lvU8hu4AltYNp1cMj5wo+INHCwaVK17Yb3W99+xs8X3ffBNvfe12JjsJg7zksaeW+Mz9J3j0ySVWVwdYX+B8iTU+pE4G++kkZteuCd7wym3cc9sMk52EwnsOH1/nw585zIc/fYyTFyGOIuDeHZZvvskRO2inDN3nXMg/62ehtshLA9kvHyn4s4M5k5Mp/+ofvpK7bp3ZIIze89uP8pHPHmUwKBmU0ssorzzKa1TvqM8NEp10zvD6u3byE//4XWyfadCIDcWgz6DXo7ve4/TSGo3JkjQxHHh6hT/40CFOnu3R7RcMspIsL8nzktxX91dS816IKAIQX0N4/d1z/IsfvodmIt1sP/KZI/zSHx5gvZdTYvBhUlGkKEqdq1EUufn5+X8DVT+EjVO3uz6+vqIoynNyy94O/+Rv3M67v3Yvk52Ys0t9fvN9T/Kr732Czz94ilMLfVZ7Jb3ck3tDiaHwlqw09AYly+slz57o8qWHTvOVR88QObh+d4cbd3d49Z0zOGtYWsloJTHz0w2mJ1KmOgmT7YQkSYjiGBtFrHQLjIU//ouHOXRsCe9lsF9nPGKxGd7DWi9ndT3jG964a7j8w585ypcePs3xhR6nFvucOtvjxEKPwyfXefroKgeeXuHzD5ziC189TRJbbtwzQSuNuOvWafbubHP/I2foD15cyGh8AB0Du9uwvSV9fA6egcdPeE4uenrrHtPtMzvh2Hb93HAbn/jicf7sY88yGBT0szBgPs9g2QB7WrBr0tBIJIISRzJFDiIr7y0Kw3rf0M/hkeMlB5clpa2e1hbHlm986y7+2d+9h9fcOUeSOL564Cz//Xcf50/+8hAnjy5xc2vAO64v+MYbPN90i+Ed1xvedr3htdvgpnbJHBkffWCJj335FPc/egaAvdvbbJtp8Oo753j9PfOs9XKeOry64Tw2oxJ+r99h2TVhhufjZLyPtWJzXnhxoRuEsNcHnsxZ6HqWuzknz/T4+jfuEgEFPPXsMr/0hwdY6+asD0qKcG3Px7gwAsRYIWzvm77mNqIoopU4fFngi5KizOn2clxSEkWG6cmEVtPxxDMr9Pvyo0PpoUTmvvrQn+cePz/kE3fkVI/bb5jgup1tAH7qF7/K2eWMHIvH1T6ZiqIoI1qt9jAluj5dSa6sJFMU5WXHW149x0/+o1dw750y6P7q/gX+9//6Zf7sY89yZqlP5i05lnIY3xgfNIXHBgpvOXSixy//8UF+/nf2c2Khy0Qr5lu/djff9Y17mZ1OiCNLFBmiyGJdaPBqpRB9vV/gDBw7tXFAfKHI0IV47ODS+CLpg5T7c6ZBJk5h64OSJw+v8v/81mP82SeepSg91hjefu8O/u5fu5U4enFfArXxLRZoBqODY+uewsNN84avuc3yzrss3/ZKx7vudsznixu28fCBRYpCjru+vWr7lZCpHq9koR9S6M/jvTSDLXKPsxJ9qISVNYa1wShNq9pusxnxI99/O//L376b3dta9PoFv/vBp/jpX3iQg08t8NbtOf/wlYYfusvwpj1w4zRMxrK9spTITdPBdAJF6emu5zx8YJH/5zcf5T/9ylc5fGIVaww37Z3gh771ZiZblf/dhWk66A5KvnqiYHHdY8P5SXRnNJWI+9zZNc/hlZIivP+hJ86SFyOh++iTi/QHBb3nKX7r1394D0IT18XVPv3+gG6/GDksWoM1lsiNvs6dNbzmrlne9bZdJImVmwRDI+7hJ65mfvFiePyZleHjpdWMHKPDC0VRrjn0Xy1FUS4Z3/LWXfzY37qTmcmU0ns+8tkj/PQvfJUjx9fJsBRIQ9XnGopVPYnCM0oPX3p0kff81n6ePS6D3TtumuTtb5yn04lxwYVrw69OSMPSldUep86uhW2NZNDo0XMdzYgsq7/r4ljvFfziHx7gycPSQBbgW9+2l9fsG6XjvRiqc0giuGHG8o23Ou69wXLLNst0W6I6NtTF+Lwawgu9QYEvR0lOm8nU+rQ08ETD3j1iOlCW8mpWhKaxpcE5g7PQKzYmUHVaET/2d+7i3d9wPUnkWOtm/OxvPcof/PnTFOsDvuNGePsew2zLSONXDHhDUYTxvRdhlJWw0vd0ByMR0e0XfOyLJ/gPv/DV4bVupI7ZqaR2RptjEeHlS+g46ZN08GzJSl/SO31whCu8nDPe8PiCpGNW9AelvFY9zyRSczGfnHM+j0EUra9nHDmxTOl9uBkieKRn18a/K2cNb3n1Nr7prTtJIjEJGb+vyCm8aLJ8XPBdgo0qiqJcZlQUKYpySXjLq+f4+997K61GROk9H/38MX7p9w+w2i3InqcYGsdQ602E4dkTXX7tT57m+GlJ7d21rcnePTH9LCNyFouVxpbG4JE04DMLa3R7oWlr1cCyto+LGay+WNbWc37/z58mD8U6Sez4tq/dS6vx4v4prmJuAHdus7xihyWOZLBcWTLHkRF7bFv1EBrDb4zbjU/U5it9iZQUJQwKT16YoWDIC0NZAEYG8hjo5aM3p7HlR39gH29/wy6ctfQGOe/57cf4zP0nyPo51zdKdrRkZYOk8uWFDzU4sh+QBrR4WB6IOKofnwceeXKJ//Krj3BioSf1Xe2YCxmmmSrSFsEtc5brZyztxNOMgNJweMlzeo2hWC9Kicjdd6LEPNfn6IIvbk79uguykaMnloYpcPK3IT8GOGurgNCQOLK88y27eMebdhC5IIyCOqpEkqIoiiJs9tWoKIpyUdx6XYd//AO300wcpfc88fQSv/QH++kNSvKLFUNhVRNGhdJ6MgxajeHYqR7v/+hR1rpifrxnR4ukXbK01humEwEMco91ljNLa2SDjZERaoPO6sgu4ghfFJ+5/yRrayODhdfds41t040N67wQqnG3RS5e5CTKErmRe1pkIXZyHcep7lL1pVC/PvXrBLCew2pPIiZlPdQQmoXKsYgaKz0s9kaRku9+1w284y27JQ3Oe37/gwf5zFdOMugXFJln54SVOh4j0Zi8hEFpyErLoBTRlZXgvSH3hhOrkiboN9EeDz+xyG/86ROkqWOqkwzrcjbDAns7hq/Z69i/6Dlw1rNzSsTR0sDLdfNw4FTBUs9TlJ6nF0tOrfth6tylYPwIq+fV+R0/tYw1VXRmlC7qnPxwQHCAK0L4Ko4s7/6Gvbz9ddvOPX8VRoqiKENUFCmK8qJoJIa//923MDUhtrzdXs7P/tZjrHXzixdEgQ3vqH7VDgM4awwHD6/zlUfOShoRcNPeDk8eW2BlfRBG8JJyZzAcO7kyHCz7czZ++VnvFTzx7KgGo9WIuGF3+4JRjAthamLAGOk35ML1ikL6WlVuIssgietbGL1WF0bV4Ywflkcawy72PEUJuRcnttwbBoMglDDkHooCeplnPZP33XbTJN/zzTcN61++8ugZPvCJI2QDEUQgYshaWb8yeyhC/VJeyr77GfQyEb7PLJabCqJq2V994RgP7T/Ltjlx/xvHBHOF2MDb9jpunnN8y60Rr9ltefB4weOnPLfMG2YahkdOlhxf9nz48YxPPFPyFwdzOc7xjV5CPMEYIdyjk2fWKEOvIWrFyVUfLYAjJ9b52BeODv8+0tjx/d98A29+1TzOjNZTFEVRRqgoUhTlRfGNb97FK26bhvAL9Qc+fpinj65dGkE0pCqIGFUaPXJgmeVVibjEkeXmG1t86dGjQzE0yEuaqeXoyRW8MfhQ6V8NMMcH0uOD6peSIyc3OnvunG8Ruc3P/LmozqMaPGeFxxhJE7RWIhyRBWM9ceRxRl4fZ8N2atfD1+5JtXzg4fhKcKnLZVlRSIlL3cY7L+D4omdQgosM/9P330GnJYosy0p++/1PsdbNGfRF2OBFCflwn6wdmRwUpacsZJ7nIojW+55j6yNXu7ohRMV6t+B9H3uWnXONTdMGq3XnG3DTtAnW2zDVhK+71bF7yvDpgyWPnSp5xTbL7klDv4DPHsk5se6HTW8vFePXf/yFY6dWiZzUKhlE/ZpQV1Q5Ny2vDfiNP3mK/QdD/RHQTCP+1nfexL13z5wjwF/YJ09RFOXlxSZfEYqiKM+PqU7E93zjdcPB2NJqxp99/NkwoHsR/7yEUZqk0I2GbNVTaw29geeZZ7vDQd/O+RYr/S6PP70gkaJCRtYnTtec58JIc3zAOf78pWZtTVL/KiY68dDC+YXga4Lg9GqVOuWxRrrEWOOJrQ/20h57gTMeH5RX264LjszDwbOeQV7ijWeQS8+bogz9ezLIchEwT50tyTy84TU7uOu2meFn5RNfOsZTh1fJB8WG4/fB1W1QerKsJoi81BXJtkU4HVnxLIf6pvHjrvPA/rO4yJ4jBiqcgTftsuSlXCtrSmJnsAZ2TMLX3WKZbxv+8lDBo2dKphvQqzWifSmp3weA5e6AXj8Xc4cQ9TEmONHVzq/bL/jgJ47zRM0ZrtOM+eHvuZVX3j4T1j3PBVEURdmCvIhRi6IoW5233bud7bNNCFGij3/hGGeXBxSXcLBlvDh/QTUAlAL3yMDZszn9/mhYetdtk3z8voPkRUkvk6M4fnoNe4EB85XAjkWFfGhe+0IxtWm9kPO0Ie2MKr0rRMuqAv1xxlPn6nPGhs8lcHwdHjzuGWTQHXhWeoaVHqz1YbUPZ9c8y33PfSdKSgPvfsf1xCFtrvCev/j0UbKsGDYxrbY/CFGishBxtN6Hbt/Q7Rt6Gaxl0C8khe7Lx4uhYLsQSysDvvzImU3T5xywswm3z0oz2jiCJDI4OzLlKErD9o7jm26OuHHa8vDiS/tJqo5y417EcW5ltU9/kNEb1snJUdpQz1VnbT3nDz50aEOPpqmJhP/XX7+dO2+erNlWKIqiKCqKFEV5QSSR4Wtft2P4PMsLPvHF42ND6YtjfMhqaoXgEjWSyViDdZYs8xuiLrvmW/T6XfY/fYYsK4kjyb+qhn6bjImvyLBwsrOxqGdpZWS88EKon9ZaLiKlRGyxi1Lc4IpyE2OEMWxtqq9Vu/RD+sBDpzz7T3vWB7DSg5UuLK7BqRU4swZ/vr9gsQ83XTfJbTdODt/75NPLPH1khXzMytkAz654wLA28Kz0RAD1chFD65mhKKWe6KGTBc8sSercc+E9fOYrpxhssj9r4A07Lc4ZYmdJgzmFNGoFHyzhSw+ZN+zoWOZepFvgC6FKKfSIiUaWFaGeKPyd1P9YAsYYzi5n/PqfHuTZ45UtPcxNp/yTH9rHLdd1xt+iKIqyZbn8/7IrivKyYPtck9tvnBg+P7s84NDR1UsUJaqroQ0PMYjLlrUyra+J9XbFrTd0+NSXnwEMiytdziz3hgPH4UauMHu2t4aPS+85dGxtWOv0QjFB4PUL6BXSx6dqoOprg2q89BHajLr4qYRRfarwwQRhvYQvHC75xNMFz5wtOXTGc+Ss58Cpkj94KOeBE+IM97pXbyOJ3fD9X3z4FP1BSZFLNIaw/RJ4etnz1ZMFRXCX6w5gfSCuc/1MIlGHlz0fP1SQ+c3riM7HIB+tVZ3TRAw3TDlSZ0ic9HmKo5F1eVmKEKn2UXjD4VURV89nny+E8e16JGLqgW5vwOHjy8FJbuRCspngt+Fv5+TpHr/yR09x4nR3+NrO+Sb/9G/u47pdo8+ioijKVkZFkaIoL4hX3j5NVKtcv//hM2SFZzTMfXFIw87qSWXLXUuhC4PWPBuliQHctHeC/c+cpNvL6A9y+oMQSQqqY9xjoD4ovxzMTCbcuKczfH5mscfhE2vkwUL5Yhk/7ryQaFFRItGi0Gy0rE3n25MLPY02S6GrRAQ1AdMt4GQfHjoNf/xoyR89VvDbD+X83qMFh1a9pMIBr75rflhLBPDIgUWK2k2rXikRh7kPHRShdXJVokXrmWFxHRbX4YkzJe8/kLGcjWp6nq8oqmNC6tx1bcNECknsSSNP5MS23JhRVC0rgvkDhqMrnl7x3Cl7L5bx+1pR5p619UzO1/jamhv7FBmk9k7+ZgyHjq/z87//BAtL/eE61+/q8GN/ex+75l+8JbyiKMq1jooiRVFeEPUoUek9jx1cGhs6v3CGw/YNm6pCRlJU7ozBGktZSP1Jxfa5Jv3+gINHztKIwyh/mHp07uC5ej6+/KXiHW/aRbsZDZ9/9PPH6PZy8loU42Koi4Kqvub4Son3nrL0IopKT1l4isJT+hA+GiMx0oenLnzMJql01PZXeDFd6BawVsBCX5qpihCTlRqp48a97eF7s7zk0PE1ikIiH/XjrqashC+eKPm9x3L+/Mmcjx/M+eQzOe8/kPG+J3IWB2I9XtTeUx3X86F+bttb0i9JXOfErc/A0KTCh3VL74nw3Hc8k+cXsb8XwrjoKj1SEwYksaQRUp1LPRJaUU+pC689eWiVn/+9J1ip9cm6Ze8kP/Z39jE3lYzeqyiKsgVRUaQoykWTxIbd28RgAaDIPacWepdkkLhxbFd/Jlsflk5UKUNGamcqnDW0m5ZjJ5fDkjBirAmjiktxvBfD3FTK937TjbgQYVtezfjIp4+S5cGS+gUyLi4WeyKGBrkny0QcFaUYOng/6ltUpxmNxs/V1azPxyfq+6yurQ/RmypVD9i9o0VcS507cabLYFBSBIOF6ryreXUOBVJHdGDR8+VTJV86VfL0qqfnRRBVomT8/c8HH85hvgmv22lpxdBwnth5jCmD052cV57L3BhDN5emrpfDdY5Nzs2HdMERG+/UuNFC9dEfPjXS0Pbnfu8A3b5EUI2BfTdN8WN/ex9T7ZFYVxRF2Wps8tWoKIpyYeLIMjctzVoBsqJkYalPOT4ou5SETVe/iptazYSvRYoAts01OHxiMTwTIYARh7eX8AgvyEQr5l/+8D1sn5VUpcJ7fv1PD3DqbI9eaFx6KTDAqXXoZ5481BUVpZGoTiECcrOgVFbKF0IUnP2i8AVRT6EbnxwQ1+7DhnsUnm6fa2ywGz92cp2i8MOo1GapeXWBVIxFhKppk1N43lTHHnk4uloSOU+aQBwZIivpZkUpvZd8aE4LcN/RkvwcYfLSsuE8w0XaUH9m5ILX0xOrF+rXtHrsPdz38AK/8PsHGGRyJtYYXnXHDP/kb9xB8wqYSCiKolwN6L9+iqJcNM4aJmq/Kpelp9+XfjMvmvroeuxh9dQgjUIJNUaMGQfMTCQsnB25bQ25JAd4ccSR4Z5bp/mP//x1vO5uqa0pvecvPnmYj37+OP2sDH2FXjj1wS/Bga6XSXSo8CJ48jBlOfRGZSVDCj8SQ4mBOExREEouPHaVoAjLrQnCpiaETOj9ExmYmYiDKYCw2s3wXuRz9QVUvceO3SK/yXQpMMC2FL52r+HsmufDjxc8frTE4nFOjDuqc6qa/uI9953Ixz+Ol4Xq3Kt9bxBFsuSc4zKE9LnaKz684D188v5T/OqfPjm0RLfG8MZXzvOP/vptJNH41hRFUV7+qChSFOWisdaQJqOUKO8JdseXdzA13NuYKGo1I1bX+jJ4rAaQYX7OePISkCaWVjOi1YzotGJ2zTd47V2zfN+7buTf/7PX8p9/4g3cceMUxhiy3PP+jx7il//oAP1+QXdw6eMO3RxWBtAdhL4+A4l6lKG5arnJLh3QcDI1LbQjaFloOUhNEEo2iCU7mtKxqWXl/Q0r72mn0YZPRa9f4MuRCNosUnQ+Xuy9q/YZhejW8XW4bc7wHXda2in82UMlB0/KjgaFXLc8RNkOnCk5W2sUe7mo72uoz2rLLnTFhq9sskpZwp9/6hi/9+dPD0W5NYa3v24nP/K9t2yaYqkoivJyRv/ZUxTlBTHeCLMYS2G7HJxvcOqsGbnOjVE/6vpg/IVigDe+Yhv//H+6mz/8z1/H+372HfzWf/w6/tM/fwP/8w/s43V3b8MaQ5aXPHt8lZ/6xQf4H3/8BN1ewWr/0l20+nlkORxb8awPPP0MerlhuRsc3NY8T586VxXFFm6fhXfebPjuuyx/7U7LG/cYJuMgloLoqYRT6sLzqLbcQGJHUzuG5saWTOQhVbCKOlWpbHWBVP9iqoul8cf1qU4SWxqpG07N2tROHTdMOb53X8ybbojBGB49JU6G79xneep0yYceLljvyXXLC/AlfPaImM2fe+VeGjY9vxDl2find76/ghqbreIlwvsHH36W933sMGUIPzlreNdb9/A3v/2mc66roijKyxkVRYqiXDTe+42WykbSxC4X54zxxny2s1zMBQhBJE8YUG723ovgfGf4qftO8NO/8CD/75/+Is+e2Ji2d9/Dp/nF33+cf/1f7uPH/v0X+OJXT7Pez1m7hILI1+psSsSI4JHTnlOrnsU1z1q/ZHGtZP+Jki8+VbLaG98CvGqv4ftf63jzzY7bdxj2bbd8w+2Ov/Uax6t3GKZiiRo1QySoFYRQ00Inghsm4F23GX7w1ZYfepXjO++wvG6XYVtz41VLYosL4skZEUR1qhS6SgxUj+v3rXp8vnv55ldu4/vfdSP/5h+9ivf97Dv4wM+9kw/83Dv5s597J+99zzfyv//LN5Ptu5ly7x723dLmLbcY7txjSGLP22+zzLbg1+/POXC6pJ97Di+VHDjrhwYPl4Pqs1pNJiw832dwM+r9u84hbCgvSn7tT5/io58/vkEYfc87r+d737l343sURVFexqgoUhTloilLT7c2qDcGougS/XPih/+rPd/kaQm+MlEYY2U9w7kw6gsDyc3Wu5gBZmrh9qnxpXD3rOXd11tubHmeeGqJ/+2/3MfRU+vD1++8ZZrTZ3s8/MQiK92M5fWc/iU0VqhTNyE4vg6fP+L5zNMlHztQ8pf7S7p9z3QHTm1SbtVJDZ0mTLVgvmOYasvj3TOGb7/b8rYbDTNJEEIhUtSyMB3Dt95h+f5XO95wg+W2bZZbtsEr91jeuc9x97aNXm2N1BEZQxxql6ookal9IY1/ksYFQsX57t/H7zvB73zgKf7df3uAP/jQ0xte+8KDp/jxn/4if/jBJ/n455/lPZ9a45OHPJ3UM9m0NBJ43U2O77jL8cXDBT/7xYz3Hcgvu8HCOJ7aCY+fuDfnfL5H10psvKkJKy//G17MLPf8t9/dz+ceOL1BGP3N77iZb3nrjvBuRVGUlzfj3z2KoijPSV54llZH6WnWGDq13jsvCWEA54fW2qGhpvcYu3FEeHapTyNNaoNHUUZV9IGxceX4GLOOAWZi+N6bLW/fe+4/me0EXrHT8f37Yv6X18TsKHr8u5+9n7VuRuk9rUbEv/yRV/GWe3cw2Mz27RJSP78SONmFJ5bgibOw2IezA8t02/GNd4/HZ6ARQ6dhaKXQasBEE6ZbhqkWTLYMd+yQSNLfep3j7bcabpoxpAa+7lbDrdthpgPtpmGy5Zluy3yqBQ2fbVCkkxMJ2yYM77rVMtcIAiuYMlSpdJVAqs5nPMWums53P0HsyNd6BZ/9yskNy//qc0dpm4Lvu77kb94J/+tbDXfPGz74CHzlaMl6T+ptGpHhm29zXN8xHBtp3KsPL38UI+kzesFXr1ez8VUqPPQGnv/864/x0IHFoTCKrOVHv/8O3v6a+fF3KIqivOw49xteURTlOcjyktNnRzlYUWSZnUkvMOp6/mzcQv3ZaNgbxoHDwvNxUXTs1DoTnVReo3JGC051mwygL7QsNvA1Ow2d1LBZMCwyUlfjLLRS+JabHe+a7vFbv//ocB1nDT/+d+7itXfObnjvpaIuEqq5M3DDFHz9DYbvusvxQ6+NeOcdlpu3n9PNBsI1SiNPI4Y0gck2THUkstRKYPuk5c69kmb2DbdbfuRtlrfcYtk5ZZmbMEy0YLIJnRTaqWemI5GmFhsVxZ4dLbCW19xg+Xuvj3jFNjMURrEdWYJvVm9UOd9VYqgumjZbZoFud2NtWa9fcvcMNGNDGhtKD3tnDd/+SstdOxz3HYFf+1LJ73055wOP5TyyMGoyezkZP4/qOWaTHL6QPnqOMKr+AGpPNzuPatl6r+A//OJDPHloZfhaHFn+2d/Zx713zgyXKYqivBzZ5CteURTlwuQFHD7eHT53zrBzrnnJ/kEZGgxvGMGFgV9QQ2X4ddwAphb4yPKS46e6zM92GGS1pqhhk+Y8UmuzwSLAZAy7Jyyx2zC+HBJHMNUUIdBJDUlkmG4ablw+w1OPnBj+6t5IIv7F37uHXfPSp+hSUh17dXwWmG/Am6+z3DTv2NYx2DCyjq0c8zjOQCOBVhM6DUhjTxJ7WqmnmXim2yWdhme67ZlqQxrDN95j6Pc8SeRpxdBulkx1PBMtmTptT5sepubCMT/ToHCWTsOzexZ+4N6IV+00pE7S6ZLgcBeFY3XBDrwu+sZT7irBUJ8uRGQ9rRBIdFZEYpZDEnnefpvjH7454h13RCxkhl456pN0vs/IS0G1r6GQMeF/HrLCE9U+8+cacgveh/TS8xz4ZouX1gr+3c8/xKHjq8NlaRzxL//+Xdx988SGdRVFUV5OXKoxjKIoW4xHDlbNUUPzx32zmE2HWS8MT62q3Idf68O8LKEM7lnWSZSm4vDxVZbXMm7cM4s1VhqH+qpny7kDwXFBUccEsWCNGArU2u0MSSNoJ57pJnRSTyfxtGJPIyk59sXH6a6MImo75lv8g++745L3galvrRIF108bUmtoRCIAJhsydzaE1zbBAGlUksaeRuJppdBMRRy1U5hqeybbJZNtz2Tbs3e+5MbtJbtnPfMzJTMTnqkJz+ykvD4zUTLVKoh7S8N9WGPYuXOS0sF8G+Y68EP3Ou6cNUxG0DTiYpci84aFpOqdVIuc1CMo4/PqsQsud+Os9WHXJEFOjK6HMYai8KwXMNc2vHq75dLZYbxw6vfXWUMS2aFa8t5DWY76KQW8l78REUYh1bQmsmRV+f/4p/HM0oB/+3MPceLM6IePZiPiX/3oK7h5b2vDuoqiKC8XVBQpivKCeOjAIt3+KDXprltnaKbn1qq8aGpjvUoYlXiKUqY4FTvliv1PL+NsxJ4dk8zPttkx2x6O+sa1wIbtjr1WLc9LqaEq2PjrfEUSQacJzTREWlJoJIZmbPB5wYFPPU5Rawz09tfv5J1v2b1hGy+W+nlUdCKIY4gcRBaiyBBF8jxJzj1baz2N1Mt74tE8SSSdLk48jaan1YJOx9NpeeIEbr1eRtVpw9NsepLE02p7mm1PmniarZLO4PSGuqJ7bpvm0TPQbkOnUdJpwLvvsexuwdfdaPiuOx3vvsNy+4xhKpKeSc1gCZ6MpdeNC6JxYTQ+4AfISk8zlXTKSmDnhUSLCg+DTNZ7ZrnEnuezcTk4574aaLcSbrpuJrgr1j654QeDOtWPCLJ8tN445y6BY6d6/Lufe4gzS9Lp1xrDVCfhf/vRV7Bne3N8dUVRlGseFUWKorwgllYyHtw/iha1mxF33Tx5niHWxSJKqP7jt6/+58GXnrLw+BI6E3YYBSq957P3n2T39glu3jtNPy8lulMbP27Y3nPggW4hRfv4zf/BdE5qcdLI04w9ceRpRR5rPRGe00+f4egjR4ZpdNYYfvh77+DW6y5tKlIlu3w91cuDM4ZGXNlfe2In12+cOIJGClHkScN5RFbmszOe5XVJpUsST6vlmZz0tJueuTloxJ5mQ4Rhqw1JAo2GPG53YDo7ganFXN70qu08vRbTSD0Tbc9ky7N7Bl6/1/CWmxz3Xme49zrLd95t+euvcLxym2E+lVTGhpWIUSV86tP5hNE4kw0zjKBU2qIsRRhVH4yFrueJRT909Bsv47n8yGfcBKOTNHHDPxCP/FAw/qGWaGp4suG12pNzPwpDDh5d49//wkOsrA+Gy7bPNvnXP3o322eSDesqiqJc62z2faEoivKcFCX8xWePDZ87Z3jnW/diX8TwceP4LPzGX/UZqlKAQlpQUXqS1NNqjcI3TzyzzBPPrvC1r7+RViPGANMTTXw1Qj5P5OBCZCUsDyQatdn40YZanEYCzcSTxiIwmpHYVjsDT3/hSdYXRz7Y0xMJ//MP7qPT2iy564VRPy8DrBchrdBIRM05TxxJRGiziJexYIzHWoNzIvaSRNZPE89kGzIPUQJxIvO0CVEEnamwLAUXg41kezYG66Dhe7T6p4f72jHfJJqaZrXwdFrQaXlm2p4b5w275sTJbroDs23DrmnD226x3LvHsKMFnViubSNEjeqGDJUI2jBtcsNnWhIVkmoiiaZUJhxZIULi40/n5KXc883u++Vgw6GHA2w2YuLYkcQuHFsQRuWYA11t2XB5LUpUnddzndtjB1f4qV96ZENU+PqdHf4/P3IPM51L9/lVFEW50qgoUhTlBXP/owsceGYZQgTkNXfOcvPezvhqL5CRCBqO6cK4zntpzrpze2NDfc6ff/IwjSTmbffegHXiwX39nqnRNsYGyNXTTcbNEJZ74Mllj/GGqvXRhnWMbDx2EDtxomvEIo7SWKyu80HBgx95nEE2ipa8at8sf+Pbbx71U3oRjIsBY2BpXeplKlEwHA97I9MY1ojAiVwwrzBBEDUgSeGG6+HwEYgaskMXiehxsYgjW1nDWTBBFJkqZONgdu0Z8HL+1hje+Lrr+MxhJ8K26ZnqwI3bYarlmWp5Og1xr2sn0IoNiTVMpbCzJamBqQvCKDjWnSOGqmsxfqKhJm34WQprVPe6KGG1D4+fGcmFK/FFOX7c1fPZyZRWM5GU0eEPBcF4ZEzhyLKN9UQjFbTJH8R5uP+xRf7zrz9Glo1+8Lj1+kn+5Q/fRaf2o4SiKMq1zJX4t15RlJcJ/YHn199/kKyQwVKaOn7gW27EPufvz+dn48BttHQ4pg9pQZOTEdfvaQ5T5x7cv8DnHzjF2197PXu2T5JEll7fMzvVwOAxRmpITBgK1oeD5+wuUA0kn12F9bxkszZDBkMSiXNZI5HUszSSVLOJxsimeu3kIg989hBFSF2zxvA977yRr3nN9vFNXhT186if29IAVgciAESciP10Eov4Gccaj7FIRCnxxLGXqFADbAJJA268Ax5/TCJCNpYpSsClMkWxRJisDaLJyOMohilzlon+8WEa4avvnOWEnadbQrMJrdYoBa/ZgHbD00yl19FEE+ba8PZbI77trojX77HsbEmN0VAYBae6Kjo0nMZPNET/Si+mCt5DiWFQGAY55Dk8fLKgm4/SEDe57S859X2a6n8epiebZDmkUfgrq4RPKfM6RTlyn6sLo9EPDc//zD59/2l+9ncfJ8vlb90YuPvWGX78b+2jkWx2lRVFUa4t9F8yRVFeFPc/epa//Jyk0VljeN0923j7vdvGV7soNgxEq1KJUn4R997jLLzxVbM0GvIr9Vo35zf+9Ekm2inf9847sUZcujyem/bOjYTD2BjwuYaE1fu6ORxZ9pv2KSpKjzEeV0WK4pIkgkYk9TjNyNOMYSKFI/cf5ImDIye2OLL8wx/Yx017LlV0bUQ3kxSxfiYDfbykUZU+ONCNYaxEiXwpQiZpBrETBYHjxETi5n3wyENgG+ASsKnMXSrLbEPS56yTybhRKt3u/ABRIY5m1hjuff0tfPpogzj2NFJIYs/EhNQqtVPPZBOmJzzGe+7Ybdg9DdsnDW+4wfJNt0W8frdlOpEeR0OHuuBS53wIXG0SDDFUqWWGfgb9zDPIPf0M1vvw+cMlJVfGinuc6vCr+Q27Jokii7V2KIgIkdO6JvKIO6MPRhLVH9Jm57LZss348GdP8CvvfWJoHGKN4fWvmOc7v27v+KqKoijXHJt8xSuKojx/Sg+//r6DPHlYGj7GkeWHv+82btz9Ah2qwggtZKVJRUT1K3eYv/4Vs9x6wyTWGIrS81vvf5Jnjqzyg+/ax85tLcATO0NZejqtlMhZKcmohYiez0DQh4FxAexf3PxN3gfXskLEUeQMURBIsRO3tzSSVLrtzZL3/tEjLK2NCtd3zjX5Jz+0j5mJF1e4vmHs76FfwJluibE+OOiNmraOp1kRfvk3IS0OA1kfyhy8CzVCkaTKNRO48SY4/CSYOKTKVfMoiKDwmLBNY+X4Gr7Hrt7jFIXUp+zd2YFdt3Nk3ZE0PFEkRg5p05OmEkHKcs+2adg+Jf2gOk3PZMuwa8rw6j2Wr7/ZcuMkNMbS6SIb6oxqF2ZpZcDCUp9+LrVDeSnXop/BIIde37P/TMnBJU/hr2ykaHivass8nqmpJqWHOJLQURUlKsZrisLf5sYl8mx4/895/bn5048d5Xc/+AxF2Ig1hsnOi/vsKoqiXA2oKFIU5UWzuJLzH3/lUU6elZ48U52Ef/737mb3thfeqLQajIoQkuGex3Pv3bO84807w6AQ3vfRQ3zkM0d44907+frX7cWEGgtjRATs3NahEUwXMGY4IKzpo+fEA0fWoDeqNR9SlvKLfOXyZa38al+UEFtP4iS1LglGB5O9VX79jw8M05AAXnXnHP/g+2+nmb7wf5KH16v2/MiSPDAhalAUEiGpW5hXGCNhERtqgeKmiKHeKiycgLX1EB1KYXI7lDGcPSuNgGw8iggRokJVdMjY2uDbwGx5gqmlJyjLEmPg1tt2cjC+ncxavBfXukYMzZYM+BspzE9BpyEpie0Ephqe2Qnpc3TTvOWdtzrevMfSjkKkKEzTEzHf+S03AbDey3nP7zzKyVNrbGtKmp8v5f4VBfQGsJ7BBw4UeA/5VeM6VxMuHq7fPYMzoe9WFSXynrwoQ0Ro9J6yLEd1RaGOqtpY/bNyMXgPv/Pnz/C+jz47FEaKoigvBzb5alQURbl4nj2+zr//7w9x+MQa1hiu39nmX/+De7jt+otPDZOxVqVeZETtLHzNa7fzfd98He1mROE97/3LZ/jdDxzk+h2TfP877yByFu/l53/vJWoz0W6wfaYtmwp+YxeLB3oFPHp64yDQhGJ2ERsy4SENLnRJaIIaWUgjQ+QM++YtH/v0Yf74L54mD7VY1hje+ZY9/PD33k4SX/w/y3WBJ/ED+d+xVTiy5MlKEZV2PHQSiJyRcwjvq2zMnYX2NEztFkH40ANw8jSQwPW3wZkjUEYj6zdfhM0boBJKIXok+xbRdUPyDMXx/WRZgbOGbTdez6N2H64VSzPeWGqbssIzPw3NhqfdglZLmsk2G9Iod7oDMw2Yn4B7rzN88+2O+VQc6u64cYIf/0ev5i1v2M3KesZ//fWH+cKDp9gWldw2LZGiwkM/l2l9AJ85VLLQvbRC6JIYaYQwXqedcP3OKbnG3uN9iS9lyovyHMEvKXWSMunD35WnehI2/gJ0TVHCr7z3Kf7yc8dUGCmK8rLh4r99FUVRzsOBQ6v82/d8lQcfX8Aaw3W72vzkP34V3/o1u8Qe+iLwSC8ZPEx2Yn7w227kh779BjrNmG4v51f/+AC//f4n2Tbd5Lu+7laaqaMsymHBuS897UaEt4a5meZo7FczW6gtuqBYqsaQT/U2OhRsm21QekMvM0P7ZgwkzoS6GEMSGeLIYIxEr9LIcNeM4dff+wR/+KGDw4iRs4Z3f931/Oj33U7jeTbBtbVjN7XnNqStDTw8fNxzcsnTG0C3Z8gLyF26YTvX726TlbWNMNqo91Kfs20H3H6PmCzsfwCOHoWdd8PR/RIt8rGk0Q23UU1OXqdKrbMQ4XlV+xnWn3mI5ZUezhrS7dexfvNrWXWTuAi667BtThrQJmnoo5RAkpphOmLioNWAZmyYbBr2bTe85dYGf+97buHH/+m97LttlmMn1/kP//0BvvTVU9zW8SRZyaPHPIPcUHjo5Yb1gWFhDe47NpJD1eFf6HOxGRPteEMd03U728SbFaM9TwwiigzQbiakaSqf66GznKfwJXkhUSOAVjOi1XAUlSOdD5HWaj6+kxdAXsDP/94BPvuVU0PzDEVRlGsZNz8//2+o/rEcm7rd9fH1FUVRLsjKes7nHjzF6tqA22+YZLId85o7Z3nVHTOsrGecWugRAiTnpYo2zE+lvO11O/jh77mFV+6bIXaWR586y//1a4/w+QdPs326xdfeex275lu00ph2IyZJIlwUYazFOMPqesmxk4t8df9JCP/WvRAia/jB77iV22+aGi7bNtvgsUdPcPdMjjPS1yeJJPISBXtqG35ZH+SGQSamDVOJ4b7jBQ88vsji6oDbbpykmUY4a7jtxklu2NXm8YNLrK5vkq8XGBdDlf6wSE1NbGEuldqiEyuybKoBrZYjue0WbGfUPHayE/P44yf5hltzMVWoojs2mCWEqI+10GrCzG6Jspw5BPkqTF5X9UQKUzQSE8bWUuuKmtBysLu5ypNPn+Hg2YTZ2Tau0WKlsYMeDRq2T8MOhrVl+JE48EH4WQvWGuII0uk2M7ftYd/b93HDndtxzvGxLx7jZ3/zMQ4dWWVnVPCtN8Cr9ziOrMITp0sMhoYz9AvPI6dKHl3w5H5ksPAcH9NN+f5vvpHX3TM/dEWcn2nwuQdOcXJBUkufL8Prh0QSMYZbr5vhHW+9g+mJhMhCmRfkWU6WZfTyAWlL+kw1U8cTz66wuJRTlJ689BReGh6XoUavHGmoF0xewFceXeD2GyfYOS81hP9/9u473rLrru/+Z+29T7ttep+RNJouybZsyUVyLxgb4wLG2MYFk0CCaYY8BAMJ7SGFh4SShEASSmIglEBsWgi9gzHGFav3kWY07fZ7T9ltPX/81j5n3zt3pBnVke73/dLR6efsU+be/b2/tX7rf//B/diSRpcaJ0VkPRkbGyeKbPH1+uHppFAkIk+4LC+57d4FPnXLOfCevTvH2bdznJuu38bLb9jO3u1jjHUiOu2EViOi3YqZGEvYvKHJlbvGef6RTbztNft495dcyctesJ2Nk00eOLHEL/32PfzS79zHmZk+O7aMc9WejWyeajE51mKslTDeadBqJsRJTBTHuDhmfjknouBPP34v3jl8beLFxf743TzV4l1v2s+bX3sFcW1CzvhYwpZtkzT7XeJ8QLsxaq4QxY5GZAkvLxxZDmmoKAF87lRJr/Dccf88n75lGu8927eMMdZOuGL3BDc9fzvNJGZ+OWW5l6/Yga3vMNdDke1AWwDqJHDNFnjxXse2KcepRTjRb3HFCw6y4erdK375TI43mNo4xuZ4mfFkMGyOEDdDGApD5Fx4sggYG4ep3dbl7o5PwrbDkHjbCFdfUTVcRpjbFPbvcdVQuo0p5eJZ/vxzyyznDTZvGqdob6Q3tZNueytF0sQlCT6KiZKIqBHjmk3odIgmNxBv307r4NWMH7qK9o6tuDjh779wjp/5tTv4g78+wQaX8aYrPVnf87lTnskmHN4asbHtuOtsye1nSwYZ/O2pkm5mQaioVQcvNjeMjyW89VX7eN9bDtJsjCp9ceQ4vH8DD5/tcma6v2LezyOpPluHBT/nHK+48Qquv3YvmyabOO8pi5wiy0iLlKiVDYfqJXHEwSsmOTPTZ3ouJc2tEUNZ2vyjslrU9SK35ZGkueezt83wvCOb2LyhxW/9yQP00upDFxFZ2+UYitzRo0c91YTM2qEoCqanz66+vYjIJfA0IsfOLU1ecGwz11+zhSP7NzA53sAD/UFBlpXkpS2hGUeOVium1bBJ9yfPdLn17lk+8bmz3PnAAt1+QasZs2GyzYaxFpunWuzdMc7+XVPs2jrOzi3jbNnQodXp0Gg3iRst7j+1TL/b5Wu/5zdY7mbkZTXEbuVO71r7h/v3TvCKG3eyaarJpqkmRW5/MKpEkVWBfJazrZFy3YZlxudP0QyhyDlIM5hbcswuO+aWHDNd6Kaen/tsztl0NKG/3XDs2DrGgX2T7N87wZYNLRpJxFIvp9cvuPXeef7q06eHz706EFWHBlYlasdwZCO8cK/jygMb2H7lNhaKBnmzyYnFckW1zjmrHMRlxuEtKTfuXmRTcYYotNomNF/wsT2H/c/OE8PCaTh+C+y5BjZtC1WhML/Kp6NQVJVgPLXk4azZwewi/PrHm9yyOMnmHdu45uAmrtozYXOsfEnkq4lb2NBKF8pYOAZ5yX0PLvK5O2b428+e4eEzXTY3S166x3PjDkcjcnT7cOvpkr97sMBFjmu3O3aOwVwf/vx4yYnuqEJ0KU0Wtm9u8/qX7WbTZIutm1oUuX2rqq9JFN7bflowOz/gxNkef/Txk2RrLXq1SvX5xkmEA77nG17Fi67fzxU7xsnTHovLsxR5zlKvz+33zzAz38d7+zy9hzQrmV/M6GeeT986w6npvjVkGIajql3347d3R4fv++Bz+Fc/9VkeOD1QKBKRR7RlyzbiOCaKbImB6vB0UigSkaeA7SiOtSIm2zHbNrfYsXWMLZtabBhv0EgiSg+9Qc78YsqZ6T4nz3RZWMro9ovQgjim2UpoJTGtZsxYO2HTRJPd28bZv3uKPdvG2LF5nG2bxuiMtWm02sSNFidnByQUfNMP/CZ3PzhHUXqKolwRhi60X+gcNBNHM4lHFQ5gLIEtHRe6uHliZ/Nato55DmwsePfzbIHUOIJB5lhYgrmuY2YxYrbnmV32/MxnCubL0Q54JYqgETuSOCKuTU4pS0+al6S1nenVoSiuQpGzULR3DF52lc1reqAL03nEoITUO1zkSTNY6tncnLyAyQnYthG2TnhuuKrkq272uFbYya51lxuGHMITlpB5uP2vgQ5c91JwRUgX2XBzLXXkdv+qKQXOLvMOzj4IWRv++s6IP7+nwcmFBq41xtZNHTZtaDHejokiR5aXdPsFM3MDzsz0OXW2S6+f03Y5V2zwvGIfHN4EnciRe08/tYVZl/sw1/PcebbkH055+h4mG3CuD9MD27Tq8yhqm/1omomj2bC/eEaszAP1twpvjTlsTaRHj1wOGzqXxBHjnQY/8b1vZuf2jeze0qbIUu554Cy/9ntfYG5xwJnZLku9jDQrSbOCvLThctVzFyX4sICvdUcMDRgu9OV/DA5dMcHCfI/T89koOYuIrEGhSEQk7KY5PNHw9Bqcw7mIKII4jkjCoZFEwyF3G8db7Nwyxv7dk+zdPsGOzWPs2DzG2HiHZrtN3Giy2C8ZZAU/8ZG/5Lf+7C6bmL5G++KL2Td0oWfAljZ80wsiJprQbECnYd3mxpow1vKMtRytpgWcvHQsdR3zy44zC46zi56/OZ7ztyegGzLDo+8er211IIrC9jVDpWhzE/ZOwnN3OQ7vcmwY80yOWfOCiQ54PA+ctkB09W6YW7Cd5x17YNdeaHfCULjQOW7YSKE6VKEmDu9hAnd9HMplOPpae3GuWujJh+504Y22BgDh/mG9oIfuhB17IWnYOkknZ+D4OccXHnTcdw7OLjmWU6ssJRG0E+s+t2cKDm0p6XjY2HKMd5w1Uigcg9yz1INeah3nlgaw1PMMcrj9XMnHT3gGBfTDukSXUiV6sjkgjiKiyHFw30Z+9LvfzMapFhvGGhTpgH5vwNLiEtNzPU5N9zg1s8x9Dy/w8Lkuc4sDlvs5aVaSFZ4sL8iLVcPonuBQBOCo/uDw9O7ciMjl7XIMRZpTJCJPsdFetcWiiHKNA87ZJH3ncJEdImfVGeciksgCUrMRM9VpMDHWYKyV0Ok0aSUxUWI/bF0UM7+cgS/4s0/ePxxbVAWxNQPZBVRFkryAneOwfdzRTqyjXCPxxMMx0Y4ocpTekeeOrLAOZ2cX4e8fKPn8GdshzWsLhF6qalvqwahatLQRGi1MNODanY4rt0ZMdRxTYzDWdoy3HTYtx7F3u2OsA6em4dprYOdO6PbhgXuhjGFiQ9i9jdeYK1SlsFBFcsDWfRY+jn8atlxtociF4EO4zfD1Vi8iXPDgQzC5FRpNq7JtGId9m+AFV3pec8jzxUfgTUdK3nItvPGo5/WHPTdf4blmO+yZciQ42s3wnXE2fLEswXtH5Oxz894+n6yEThJxarFkOR9VhuqfxWP5XJ4Io38hNqQU53j5jVfwgudcwcbxFrHzlHlBWWSURc5yL2OpnzG3ZIvTLnYz+mlOXoQmC6VVqM5rsvCkvMBqy0VELuxynFP09EYyEZFHsqqqUE0O99WClWVJlhf00oI0KxnkJVlWUIa1W7wvaSVWCT969XbGO03bD3du9NgrnvCRVcOqCg+fOGnDz5YzzyD39DNHP7dFQK39tbXAHqTQHcD8kufvH8j53JmSdgyTTcsTVS64lF8F9dtWwah6DHt9NpdlsgkTTXsDS++JHDRiT5J4khiSyBPHnu2b4ehBuO1eGHjYuw+ec4Nt312fhXMLIfxQK0lVrbarjXGj63YdgU1XwS2/A0UHfGRrGzkXOtM1bf2iqlU3LaANS11wbWvsEHUgakHcsYYPUQsaLU+742i2rJlFHFlVqZF4Gk1Po+EZ60Cr4Wk1PElsa0QlkSeO7PbV5tpcH/v0q+9AlRMu5TvxZFnxnfCe5x3diXMuzLcrKX2JL0qy3JNmBWlWMBjkDLKCLC/DosL2b2f078b+7Vwer1BE5PKiUCQily1f/c8zbI5QVofSkxeeLC/pZ2FnMCsYZCVFCEVgLc+aScymDePs2jphO+YXiCBrX7qSD8Ho+CI8tOBtnkrX5uYMUshLO+6lsNz3LHThrhMlH/1szv3znuu3wdEtju1tGA+tqx/rD+Jqx7keiGJnBwekOSz2bbgUYVFW52wIm3MWFBwWFibH4TnXWoVooWtD7Hbuhf3PgflpuOt2yIaJ4vxw5KpFXENFafc1MLYfPv27kPZsTpLPwmfaDIu7NsL9Ihj0YXMnDLFrjq5zkZ2PQqvwKPE454kib68jBBy8p5WExXLjURfARuxpJp449PaOXEkUWUAsqwV3GQ3rqzzdscET0q1zTIw1OHDFVhqRVb/wHh+GuqdZwSAvSbOSfmrhqCiq4XG10R92t9qDP/2vUUTkcvJYfxeLiDypqkBU/V3b/tptu3HVjl5RhlA0KOgPCtJQKSpyqxaVpe08TowlFN7xvKPb8aN9TVgVhC52J7HEhr79zQlPXsAgg0Funeb6KSz0YLnnmF6EP76j5M/uK7l+b8RbjkYc3h6xY8Kxa8J2cOuB5mKtDkOE+1ftuBMH4zHsnLDLzy54Hp4tuedkyalp6KfehiHGECeQhPlPrRiuvR5OHof5eQskrTZc/RwbFnffZ2BubjRkjtjeDDfciV85lO7QDbBtMyw9AOdug/kB+Ga4cfUY4T6Ds7D1GlhasLlJPqyVRKgqVQHJl6PPL4otvCWJxzloNcPisAnEsbfMVoWjBDpNG4Jpa6l6XGSfeLX99cPTzcKeDfvbu2sDE+MdJscSq4CGQ1HafLksK+hnBb0sJ83t8qIY/QHBhz8qVC/ucnh9IiKXm0v5PSwi8tQZ7sOt/Eu3/fXbGgIUhScr7C/kvTB0qJ9ZOCoLG17kS0+nFZPmnle+8GqSyHY268GINULGI6l2nO9dgIcXPWnhSAvHcuZYHjiml+Hj93v+9+dKnIN3XB9zYJsjiiKywhFHcHrZ0ytCmLmE574QFypEkYOpBK7d7njO7ojn7ot4yeGIFx52PPegY/MGz5kZuPc4LC6GxVnDWkQutvlIR14Ap8/AUm4VncjBpi2w/yWwNAMnvwBl1UAhChWIauNDp7pqaN3eG6ExBZueA8sLcP/HYf445AtQpnbfbAHGtsHUJhgsWSc6GL0x1efkfeiA56zleZRYqGs2Hf2eozNuc86iyC6PQuhzYRujyBpj5KXN93JUHQRXBoXH8zk8HvXvoCNsN56XXr+XRiOh005s6FzpKcuSPA/D5sIfBnp9GzqXl96G14WhcvbvJ/wb4jJJfSIilxmFIhG5LA3328IJmxsxqhJVw4Oy3P5a3h3k9AcFg9QOZVHiywLvC5LIEUWeq/ZuZuPUmAWiyNZ+qao1davPr+ZDl7J+AR+7x/PZUyWffKjkD+8q+LXPl3z8Ps9YA958LOLmqxxFWVWTbI7LqUU41bXhc+PxaCTaowWz83aawyEOjRU6Mewagxv3wvP3OXZvhO0brCNeuwntBmzfCs+9Bg7sh4UFOPFgWH8oDFFzCTQdXP1cmL7bXqcPwaKRwJ7rYGI3nL0Dcge+YdWbchnyc5CdhPxhyE+B70GjHYpCTRtSt++lYV2iB62NNw6SDjQ32vygVgtKF6pESQhEIQxFIejYIcwZiq1iGIc5RlFYU8nmT9n72kysYlRpRHZddXsfvgfVe1w/fqqsfl4XWWiLneM5R3ZZxSuy+US+LCkLm0fXTwvStKA3yOinBXleUubWXMH+naz6t1OFIwUjEZEVFIpE5LK14i/bYZK4TRYP3bTCeitpVg4rRVlekOYFeVk1XLD7TY01aDSbPPfw9idshzAH5lL41GnP4sDTcXBgA9y413HlJkerBYPCurmdW7KFQj9zuuRsr+T52x0v2enY3rIQUlWMHs3qQOTC/RoOJhM4ug0ObY3YPObYOgXtJnRatvZRqxnm3wAT43DoCGzYAvfdacP+CIGC2NYu2vkcOHdrqPqEDXQRTG2HTUdg5vOQzYJfDFWcSYi3QrwN4h3gJuy+yXabT+QcJC3YdBTGroTjn4cz52xInQ9Vpw1TtRcatsWFqlNUDc0LAcmFVuDdZRvm50K4iULQjaJQVSwsiFWNFaIwn6oIzQioDWN8uqz+SlZdmHZvn2Tvrs1MdhrDQOTLgqKwPwakoTraHdjprPAU4R+JFYo0n0hE5GJczO9gEZGnzxrziqpuWmXpKXKrFvUGBb2+VYv6A5tnMawWlSXjnZhB7nn1i6+2nd81SkSXslPsa+vZTKewfcJxdIfjii2wMCh5aK7kjtMld54uueNsyelFz0K/5PBWxyuvirl6S8R407Ft3DHRHP0wXr0Nq89Xl1UhKgohIHawoQVXbIwYbznGmjaXptWwl9pshOpKI7S8bljI2LwDrrrWFk5Ns9AEoWXD5loT0NkBvZlRQKnSQ6MFW26A9CT4TRBvgngcokYIVj4Mg3MQTwL9sABsmEs0vhmuugkGPfjMp2C6a+9pYyP0p2uJ+AJzYKJQWiu9HTcbdrvIYXOF7EMmdvY++BIibI6Orz5+Z3PDqkqK3ePpVw9oN163m0YzYbxjQ+d84SmLkrwIVdHMho72+pkt2lqUtkBxqBJZpUjziUREHo1CkYhcvlbPKwrnq7/6FyXkpbUk7qU5y72cQZbTT3MGqS1CXRYF+IJGHBE7z3OP7Wbn9gkLE2EI3WNVBaPcw1+c8Cxnjrx07N0UcWCb44YrIl683/H8PY6D2+CFV0ZctRkm2zDRdnSajsmmDaFLQrWo2iGu7xhXAagKQ/Xrq6wCsG3c0W6AC4Ok2k1Ps+lpJtaMIKkNR4NRR7dmE3ZeC2dPgG+HpgYh3ExdDfkJ8OMrg5GLbEja2HMgvc2G0dU70g0bI4Q3qshWvZDEmiTsOwKHngN33AK33gLFOKRzkOfhRYXqENGo4UJUde2LoL8MkxPgQvs4F5o8WEtq61TnnKfTtuNeakMZs9wz1/MsVh3xajns8XwnHqv6501Yr6PVjHjdTQdJYkcjtmRXlgVlWZBlZfieF3R7uVWK8tIWJi4tEIEPXRtHw+YIIVBERFZSKBKRy1a1k1rttXofWnPjbR5LGEKXFyWDtGB5kI0aLqQ5eWHVIqsYeabGG7RaTV7ynD1g+57D4VbVsLLHogAe7sLfn/Is9OHskme+B0sDmF12eGD7lKOZwEQrotWwCsZUy9GK7YmjEIrqqh3lah/2QqEoCnOKppqe2FkXuSQMD8tzWFjyLCx4itwur4ah4UIwCnN5tlwFyydWdpeLgM5uKM7VNqw2PyeKoP18KO4J6xHVu8qFoW6uaUPdnAspshKKdVPjcNPLYHISPv1H0M+he8YqTd4y7WhuUficXAJ5Bu2OvR7vrfmDBebRcVE15SgtaHRa0G5aM4y7pkuKsD31nPBUZ4b6V88xagRy5Z6N7Nm9mamxZqgSFfiipMitGtpPc/qDnG7fjtPMqkTWddHbe1D9u/GMgpGIiJxn9e9gEZHLjq/t2FVrFHmqOUUleWHzirr9sIPYtx1GW8g1BKOyZLyd0EtLXvPi/TSjMG/DhfFUj3Fv0dcWdf37s567ZkpOL3hOzcPpOc+5RbtdNdTPe08SnjbNrW10O165Y1xtSvXY1enqfH1zfS0oRcBS33N2yXNq3nN6GnoDmBiDqSkY69iwubhlh6gZgklk6/S0JyDvQVaOAg0Okj2Qn7UFVoe/Nap5Rth94/2Q32FNGYjOrxoN71vrTEcISQ6IPFxxBTzvuVAsw+1/DbMnIBvYi/RpCEdhZFyRhiCZWBWqWqy0KKDIHHluIcl7R28wqi56bw0vmjHEWPiomhHU3+fH+HV4TFY/lwsJ/WXX78MRDYfOWcC3eXP9LKefFnTTnOV+xiArbehcmFPkPZS1CiurXqOIiKykUCQil7f6X7lXzSfy1RC6wpPm1mxhqZfTS/Ph/KIizCuiLEhiRzOGQ1fvYP++zbZfXs3Kf5xKrCrxlw/DvbPw8ILn3JJd189sIVVP6CgWuqO1E8dky7GpbcPnqIWbKjPUA8/qg8PmEiXOmjWcXISsgP3b4dq9jqt3erZv9Ix3bIhcFOYRVVlwGHxqzQbG9kH33lXNFRw0tlmHuWGwqTYwHJyD+Eoojq9xm9xCWP03znAYXzTaS3fA2FbYddjWRuqdgrv+Du75LCwuhLDiws59WK+oWrcID0XpyXPIcquQDTJIU8hzZ5WiMKcILAilhVWR6gHz6eacwwHjnQavfPEBmo2IJLKVZsuipCit61yvb6FouZux3LO5RdV8ouG/l6qqWr22y+EFiohcphSKROSyNtyPq/21uwpH1V//qzVb+mnBUi+z9txpQT/NyPKcMswtKouSTVNN0gLe+IpDABZTat3HVh8ulgvZIi3gb07Brec8c13P8gB6KXRT6KaevLBD5DythmeqYwGpKM8PPasPVfGlOiShwUIjgk1tOLrNcWg7tBN7j9pNaIU5Q62mzeGp1u+p5hMNH7hqxz0J/XkbCufd6EmjzVCcCrerXnC08jgas5BVLo6CFqES5fNwWbitr+5bBbQQkFxk7bs37YF2Cw6/EDbtguN3w52fg9lZCzRRVW0KFaIsVJJ8YUMsS2+BCWxOlcUEqyQRqkWDwi6rPuv6e3spn/3jsfq7FoXUduN1u5jaMMHGKRs6VxZW9cyL0H57kNPtWyDqpRlZbkMBbT6RVVGH7bhrQ+eqapGIiKwUrb5ARORyVP21ezSEznb0qrbcWW7zipZ6OcvdlF6a0+0XpIOCIrdQ5MuCVhJRenj1iw+waUM7dCuzVFTfOb1UoXhBBqTAfctwogsPzcPpRZhdhqUeLPagl1k1I81gtud5cMnu70ZTec47VNklrlWHEmcFnUZo1HBm0XPXGc/cknWdSxoWHpIQhlwCrmUHmiH0RLXhbCHwbDgIg5O1alGYgxRPgg9d5IbpoRGOwxsQ7wbmaskirGVEaPkN4fIQgohqQ+6q9zKDeMJaec88CBt3wHUvgSuPwdICfPrv4fNfgHPTVp1zoV23JwSs8FkOwuKwhbdKXVnaHKhWA8YaNterygg+jKKkdtlTzYUGC1EEb3nNMZI4otOMh8PmyqIgz2w+US/N6fZylnop/TQs2lqU1nVuOJdo1Ja7elFP12sTEbncxVu3bv1+hj88Vx56ve7q24uIPG2qYV8u/EXduTApHUccR8RxRDNxtFsJ4+0G7WZEs5HQbsfEcUwUx7g4Jooc3kUszC9z2z3nbMc9/An9idhp9Ni8nDNdeGjRc3LZhrbN9GFmAMdn4a45z+fPeO6Y9vTzEB5WVQ6qIFSFpWZootAMw+Uaka0nNBHDsW2wf7Nj66QjKz3TC7BhHDZuhHY7tOBOIGpB1La22y4Jwad28JG1105PQnN3mCwVW2hwk1A+CG7HKHxAbWOdDZVzU8As+KkwB8iBK2vhq/ZG+XD/4cVleIwmtMZgcR6KgTVUiCObG7Vju93v3gfhljvhlH2ENiwxdsSxBecsd6QZDHLIS0fpHVlplbveAB6Yg7nMXmI9ENXD0pOtet0REMcRUeS45sBWvuKN17NpqkkrifFlRpHn5GnG0nLG3OKAuaUB5+b6nJvrs9jN6Ke5dZ8rR80Wzq8WiYhcHsbGxq0DbPhjUHV4OqlSJCKXveFOajjh/WiIVFlC4a0DXZYX9AYFi92U5V7Gct/WcEnT0RA6XxZMdBr0M8+XvOoorWZkc00eT/u5Gl9rvJCVcPUEPH+r48gmx64Jx2QCm1tw5ZhjQ8MCzcYmbGnZ4qudGFrOFmOtH8Yiu34qgW0t2NaGdmT3O7YV9m10XL0dDu6AF1wNNxyy+TS33AknTlu1BGcb5nNwRa1SVAs4Lg7d7LZAMRvSGKPbFeH9h1piq1eAmuFN2Abl/bXHboTbVG9QeAznbVtWpJHcjh2w4xD4gc0Rct4OUQQ7tsFLboA3vAKuOQjdHG5/ED51p+eW++HUrLVrjyLrPJcXFob6KfRSz9zAs5iNhpR5b5v1dHBUIdM+hDe8/BDOxUx0mviqUUhuDRZ6A2s5b1WibLhoa15UXecs4FdNJbz31nAhvE4REVmbKkUi8oxQ7VvbX5OqipGFmSh0koudI44dzSSi04oZaye0mjGtRkyrkdhf4uOIOE4oS89Yp819x8/ywMMLo2FGazzvpaoVTZgfQC90neunMNt33DNTcrbr2T7uOLY94uBWx84x2NSyoNPNLBRU03IiBxsbcHijhaZBAUc2w45xGE/gpfsdmzqwdRLGWjY8DA/79sDeHRZ+TpyweTftTZC07HF9FjaytO5w1dpCLrY5RMxDNBWaMYQOedEYMG1Vo3rlrgoszoXjBPKudZKLO7XbhU53jlUBqXZfcqATbltCaxLyOZtrRAhHeJs/VOY2fHD7RtizBXZttfdraRnuPQ23n4BzS7DQhYdmSo7Pwok5z2dOeaZ7kJYWYKvNKFdmtidV9Z0GiOKIyDn27pjga7/yxWycbDHeTijLnCLLybOUbi9jbrHP3NKA6fk+Z2Z6LCyndAc5aV6Q5568hLwsrT15rUrEU/SaREQuxuVYKVIoEpFnBFf9L4QhsDBka7o4ImedxaIoIkkczSRmrN2g3YppNmLarZgkjomiGBdHNBoJs0sZh/Zt5Pf/6i7bgaw93+PZgfSrdnjTAmb7trM90YBrd0a8YE/EVZtgouUgtKXePuHY0omY73v6hVVlImcFmYkmjCX2OMe2wnU7HVvHHJvHHDumYLLjmezA5ISj2YBmYpWiqQ0wMQk799rQudMnYW7B2m8nE9aRzidAH4qe3YawcCtutO5QFYDoQHkCop2jZgrDkFK96NzuE2+A7DYLWFFVTQrNEGCUQHwZhtd5u75Ygmh89FjO25woqvWKnLXbpqrwWHNB8sKCXyOytYh2bHTs2WzvRy+Fub5jtus5ueCZTaFfQBbmqK3KZ0+J6u2qvreRg69+6/UcunonWze0cHjKPKdIU9I0Y2FxwPxin7mllDOzPabnBzZ0LitDowVPESpGha+Gzo2G0ImIXC4UikREHo+q2oCFIAihKKoCkR3HUUQSOzrthE4rptGIaTcSmg2rFFlwSkizks0bx7nvgbM8+PCC7dSX3o5HT3nJqjwRA2MxvHA77J9yHNnq2Dvl2D7hiJynl1p42TDmmGg6FvqeArhme8TOjufssu3gXzkBN+91XLHB0U3h6HbHpjHHWBP2b3WMtaHdgCSGyTELAePjFhJw0Jmw+UTtcdi8E8Y2w8wJWJq24NKYgGjCqkA+A5eGFzAOrg+Mjd57PPhz4LaH8y684PoQuq7NWaKEeBekn4VkZwhPYc7QUEgiLgSisoDsLCSbwhhEPwpGHjvt8xCsqkBVtenGuvg5HB5HiaP0EDtHsxGxoe0Yazh6meP0sif1K0PRUx2IquMoiogjx65t43zje29mvNNkw3iDssisSpTm9Popc0sDZpcGTM8POD3bZW4xZTksVpwVJUUBpS/DfKKw0HGoOD5Vr0tE5GJcjqFIc4pE5JmjGg7EaM6EzSuyncAitLsepLaQ68JyOmzRvTzISPOcoqjmF5Vsmmyy2C9439ueb4Epcri4qkONdlwvdYey2vcvgV4BC6k1AVjsW1OFmWXPUh8mWtBKHEu9krz0HNjqOLo9YkMbDm6N6CRwcAM8Zzvs3QiLKVy/23Fgm2PnBti7BTaO22H7RkcvdFuLYxtiuGkTLC/B6WpOUbVIawx7DsH2I9B9GKY/B+m8bbcbAyZDdSirvaAQfpy3+UL+7GjIHNVwOEIlJx29F5G3xV/7D1mA8SEQldMh9IQFWauq02AOmKhVNmpdEFwIXx677TDIhO1zYd2ifmrd/YYVpLBmkfeeJIYk8hThu0MtNKw+PJmG3zFn3Q89nrd/0bXESYNNUy3KsqTMS8o8Iysyur2MpX5Gt5+x0E1Z6lnb+apCVP0xc7hIbf29ERGRR6VQJCLPGMOd1eov+z6sUxTaLhfeU5QlaVHQHRQsLGUsdW1HcrmX2WKueUmZ5/gypxE72s2IK/du40XP3YPzHuei4c7qY1VtZxWM7pqHuYGnm9laRQ5PpwFpYTuyGzuOreOeVuKJ8Uy27XZb2nDjbsfhHY4NbWg6z5Fdjg1jnvGWp5142g1PM7a0uH8XLCx7XNj5jx3s2mMd287cDzNnIa9eV2kNHLYdhM3XWQvupVstQPhqZ70BbqI2ByjsyUebgdPhfD0QhRfvQ3MGV1qoaWyF9DiU6ejN8QlkZ0LoCXwDZo5DXFWoqtuXYf5TCFtRmPtUtRtvNO18WmvQUJaeooBu337TNRM/rChlhTXBqFdQVh8/FRwQOxs2t3vrBK+56SCdVkwzdqHBQk5RFKRpznJ/1FxhYSml2w/ziAprSW9ziMIaRWHYXLU20VP6okREnqEUikTkmaWqFoWKkfc+DBOyuRR54clzzyArWOpnzC2lLHdth3K5l5FlOWVYt6gsCjZPNlns57zvrc+nmdgOalVpGf41f/U2XKQqGC1mcP885CX0C8/SwNNLPXG1aGvkhy3GGzGMNeH2M54X7XXs2wwb2o5WDFsnHFsmYKIN421rqBBFEMfWHKEsYe92W5+nn4Zg52GsA7sOQlTCw7fD3LRtSzXOL/YweQDGDsDgdujfD2W4rw9D1KyrWQhMLchmLfxU4bT+ueT9sPirD4up5hDvgPRMtaCqrXlUzIW5QWGY3/JpWzw2SWoNIFYNlcv79jopR3OTXGzhqNUMTSJCRakAWi0XqiXWhCAtYG6wcthc9Vk9VcFo+L2KbOinw/P2119DtKJKVFDmOXleDL+73X7GwlLGQmjBnWXWgrssrcNc1Yp75b+RJ//1iIg8GygUicgzju3j1obPeW87kiUU5cr23AvLmbXo7mcs91J6/Zw8z0O1qKAROyY7CXt2b+GNrzgUFnONRo0F6juxq7bj0VShqARO9GyNohJH4R3LmWO6awu5Lg0cgxxKb2vsDDJYymDfZke75Zgat8fauQHiyDPWcSQNR7PpaDUhTqzrnnO2IOnmLbbt09M2r8gDPoUNm2HPEWiNw/xxWHwAsnkLMDgLE2PXQLIVBp+F/HR4r0NAqoa4UYbLq8lTVbgIp10xaqtdte0em7Bu3dar3A7RDlh6AMoMBl3bns1XhechBLEQfHwYNuciKNIw9C00XCjzUWhzkc0j8t7hS3sv09zu2Msc89XnUEK+Rmh4KgOEzYeDA1ds4TU3H2ZqPAlVIvt+FnnBILVAtNTPWOplzC0N6PYz0qwgC40VfAhD3v5Z2L8H7N/HU/qCRESewRSKROQZpdrPG/4lfBiKqmOrFqWZpzfIWeymzC2mLHZtCN1yP7W5RSEYlUXOpokm/bTkfW99AVNjjWE3sCoY1QPRYwlGBbYDfu8CLA48S6m13e4XMLNsO/hZ4YgjaDUdd57zHNtmjRTGW9ZAwePYOOFoN63rXuygkYRKU9jOKA6VmtyqQ1u2w+ICpP2wMZGFlXYCW66Csd02LK2YtqFpDptH1GhA+3rb+OLzo3lAwzc/tQ51VQVneAjX+6g2F6iActG62EWd0ZA6PDQ7kPZs/s/i7bDlIMRlaKpQux2MtmHYFQ/IU8gyyDMLOWXoROewgJjEdsMSR3dgc7pme3B22Q8z21OZGap+FBHY3LXIEXn4wNuux8UJGydaVsHMC1ustchZ7loYsnbcKQvL1dpEJXkROs5Vw+ZCY4V6GHoqX5+IyDOZQpGIPPOEv/Bbs4WwiGvYKbRqke0wZnlBd5Azt5wOmy4sdTN6PQtFRZ7jiwKHZ8tUg9ZYh/e85XkAwzbfdmbF0UUHo/rtPDCbwrkeDApPmtu2ZqVnqe9JIo+LYaHn+cxxz96N0G5Cu+FJInB4Nk94ksSTOE8ce+IYmo0QiICysPcCLCQ4D5s2Q7NlYcGnoyoMhQWQ5iQkU7X0Vu1QDyDeBPERyP8OfLd2XWnrGpWLo/u4qq12qAKVg9GwuHLG1i2ydFh7YzLYcAiO/xVMXWlDB30VrqLwPHmYTxSFdYlSC4HV7eIqsdYTjvNkqWeQjposVIfj8yVZGRahXSM01APwE8XVftlWjx25iAi46fl7ee41+9g61cQ5jy9DYC9y+oOc5V7KUi9lqZsxvzRguZ+RprnNJQrtt8vSU5Sh4QiEYaUhHImIyEVRKBKRZ5z6vt6wWkTYQVxVLeoPilAtsjVdlvspS/2UNKuGKNkO6Hi7QV6UvOV113Fg3yZiZ3/NrwoTj2VHudrOsG9P4eG2WXhwHmb7nrkuzPds2FyvsHWF/vYBz4GtsGXCMTlmwceHeUFJYttRhDbUZWFd7cDO168fzgEKIShqhGDCqAucDxvpfe1F1sNR9bg3QHE3lD27jBKiNpS1oDRsk40NmfODEGh6tngrRVjzKAyJ85nd9fTnIG/YcEFCgwbPaGheNWzOZ9XnDMUgzC3C1kYqw3uXF1Z1SjPwOApvDRWK3NYpmu7CmWVPHoZd1oPRWgHpiTYMRHFkQxXHGnzdO18IwESngS8KijCXKMtzlroZiz2rcM4uDZhftk6KaT6qEpXeKkVV+21fmyj1ZL8eEZFnE4UiEXlGqoeheivi0tuE86paNMgKuv2c+aWUhSX7i/tSN2O5N5pbVBYF+JIdmzt0U8/Xv+uFoTrjiGJnAekxDqOrdrarYNQv4aGeTfTPvQ2X6xfQSx0PLzocjufvi4gTyHJHP3PkJWyadJTeUZSOKLItiUKjA+fC0LHSNtQ5CwVlCEVVCCqr4FIdp3a5C3NyqA+Hy61aRN+G1CVHwS2Cn7bnjMeBpXC7rPYiy9rQuhyYBTe5cg/d5RZI7v80bLgCDr0STtxlnfFcNfQuVJkgPFYUHiOc9kCRjYbQlWFtIgcU3pGGuURLfVjow9IAZrqwFJ67Kkj5NYLRkxEmqu9OFDli54jwvP2LjrFxwxQ7tnSAkrKw72Oe5/T6BUu9lOVuyvxyxuzCgKVexiAtyELr+apKVJbhjwKgKpGIyGOkUCQiz0jDndeqi1g1hC60ubZqUUmWlza3qJcyvdhnYdnWeVnspvTT2jC6MqcZO8Y7DZ5zbB9vePlhIueJogiqpgtrBKNHCkf166rMUAALGdw5B8uZJ8thUMBcDz59ouSKjVb9ceHJGjEkUVg7KbLtqNbgyTJHFnpsD+c/OcgzRxHW5ykKm3NTVIGn9r6BbZCvB5qqShRuW92GQQg3BXDKqk7O17rE1e7vI8hnasP1wnpHPrTEzj3c95ewYz9MTEGSwva9cO6hsFnVG1fabymXjIKRS0KHuaR6Lxx54chSmzuVFW4YkvqpNbXIPbY+VN8zqJpEBPXTj/RZPhb17wkh8EWRI4o8V+3dxNu/+HlMjCW0kmhYJSqynDSz7+tSN2Wpb4FoYTmlN8htLlFYm2hFlagcVYmqwCciIhdPoUhEnrlCGKpac1dzi2y9omox15I0K1ju5cwtpswuDljqhgUwu7aga5lZp6+yyNk83mCpX/DB997Erq0TJBHEcUzsbP6Kc6GxQS0UrQ5Jqy+rVKcL4EwP7p2H6YFt661nPJ0Izi47upnDu7CDXzj6OQxSR6/vGGThkFslCAhDxSwcpPmoolQWztpXhw0admqrdWsjtMymGm4XNtKXoaIUqkpVZcm1LRx5D/kghNPChsv5UDFKYmh0oFwCWuG5bEPJlmFwHxx4KXTCIrHew/ZdMH3cqju+tMcq87B9IXCV4XSZW8DIQyD03pHnFhDTzN4DHzrRNRJ78Yt9z+IgfGdqoaH++VTn65/fpVr9HYjD9yXCuhpGkaORRHzX170c7yI2h+YKRV5QZtZcodvLWVwesNjLmF3MmFscsNTLGaT5cLHWFVWiUCGtqkRKRCIil06hSESesYb7flU4CqHIF4SQZGsWZbmnnxYs9zJmFgYsLNnwuYXuqEW3VYsKnPNs39iinzu+/R+9zHZuq2509bCzxl5ztT+61oF6QcVbMDo7gIcW4bOnbN2is11wWLjr9W0eTC+FfgZENpSuG4IIWEvnaoNcqETE4aKy8GSFzacpslrlp5pyUs3t8eE6P6oSVU0MfGigUA1nq27rq6etmiEU4XZVW2zgvr8F37GhdMR227wLyw9B51C4fxyet7TAtXkPnH0gBDM3uh+EYXVYICoKR55aM4misOP+AKsMhRbkaehWt9iF6UUbOjc38FQFMwvTo6d39e/TE2D4PakOkTXucMA7v+Q57Ni+he2b2kTO48uCosgpipxB6Ji43MtYXM6YWejZ93SQk+WePAwNXT2XCGqfrYiIXDKFIhF5RhuGodVzi0JHrmrdojQrWO4XzC0NmFnos7A8YGk5ZXHZmi4UeU6R2c5ppxUz3o655ugeXv/ygzjCnn6VhGpJpx56Hkl9B7wKRv0cHlj0zA48Z3qetPDkhS2+2s2hN7Chcr6EpW5JWXhi50MwsLCXpRYAI+w6R0nkbIvK3IbQVaFm2Lrbh5dSWDVoOAzOg0tDyPHhchc2OB8Fn+rxinDbeqpwpQWYBQ9xMzR3iGDuIVg8DlMHQ2BwYThcFX4S2LkDph+yRgquDOsdlWExVuwyX0Le9/R7VgVzQL/nyTJIU2uukaZQFiX9tCQtSgZ5yenlkkHhbT5RrXJVqWXGi/5M17L6/lX4sm6GsH/PRr7ijdcz3okZa8UUhbXfLjNbWHixm7GwnLLQzZhdHDC7mLLczxlkBWleLdYaOs3VqkTVENJqG0RE5NIoFInIM9pwB3A4lC4MoRu2KrZJ6VleMshylns5Mwt9ZsPaRfPLdpxnOUWeURYFvsjZNNVkuVfwrR94OVft3mST48PcnmEZ4CKs2EGuhaKQKyiBudQaACSRhbhuWrLY9Sz2oJtaK+k4cUSxhTMXeVxoruDc6LT3IUCEhVid8+ShG9tgYFUjX44WVK1y3rApQlXpKWsbHlp7u2rjMwsrZWod4FwxWqy1Ck1FCpPj9hw+hpk7YWkaJg+MutK5qroUFnt1Yf7R1j1w9szoDfM5lH17zCJUvqowUOSeXt/T7cP84mih1rSwdaAGuXWkm+/bfKI8BKIqlA6rRmuEmcdj9dcjiiLiyNFuxvzAt7yG0js2T7XwpTVXKLKcPLNFWheWbXjn/NKA6fm+tZDv27C5vCgpiqqRiH2/qz8K4EeLt4qIyKVTKBKRZ7w1q0Wlp6yGGZUlWeFJ05LuIGe+mzE932Nu2SazLywP6PZSiiynyDLKPIfSs3d7h/luyb/6ttfRacbEkSNpRMN5IsOhUbXDxah2vqtglBGqJhH0CugVjoWB7cz3q538PhRVd7nITnsP3jl8aVUTj3Vec1XoiWxBVwiBpwjPX68q1NNAahvja8c+rDs07EZX2O3KZej3RvORqgDlB5D1YGwr5Gdg8TMwvhX2XBOCT6gM+bA9Rd8CVhm2cecemD89mltUphaIyrBeUTU/qVrQNoocYx0YH7NqydyyY2YBphcciz04twgnFkoWq+eofVhrfV5rXXYpqoevRv7FcegW6D3/zz96KZ3xCfZu74D3lEUWGn1kDNKMxWVrALKwPGB6bsDs4mBYJcryUSAqvX2vq3l09Y5zykQiIo9NvHXr1u8H8OEHbP3Q63VX315E5PI03MkN/4+wAOE8jlEHOYe1rHbYhPdWIyaJIpIkotlwxJHDOZsQH8cxzYa1PNu3c4K//PsHwDn8GjvP1fkLhaP69dVxdbAwA01gY9vRThxjTWxbsG50sbOqhw0lc8SxHTscJTZnxdlLhtCuG2ctxV3o+kaoIFWNC2BlacQ7qwj5UG0iCocwnM47q+r40jra9ZdhYlMtFIWhev0edO+BziYY32cBBm/BpnpoX2vl7cKbUG2X89Cbh07HLityyPqhyhMO1lwhvHeFoyitrXleOHqpXX58xnPbOc8Dc7BchDWLqm6Ftbeg/las9dldrPpnGjmsnXuYS/QlrzjEm1/3XLZtatNuxLZIa5qRZxlpmjG/mDKz0GduccCZ2R6nZ3rMLtncojQrbD5RFYoKqyhaddACUfURiIg8E4yNjdtcXedWHJ5OqhSJyLNDfRhR2MEuww5k6Utr0Z170rykHyazT8/3rfFCWNx1YTkjy3PyPKPIqkVdE6IIXvGSQ3zJKw5aToichZCqYhR+jtd/nNd3kNf6MV8VZ0o32qGdz2Gmb0Pmupn9gvBYc4W8tEcqvK1bNMgcZWlhwJcO7600lBdhjZ6BVZCsmYI9TtW5LevbvJ0yjB/zYT5RtSGu2rgsVIaqUFWlhwIGPdv2atjdcL5RCQszEG+D1qYwtC4MkStTCySEihVhqhZFqE7lVmnaMAlZd9RpzocW5IO+I0vtfXDOuuwNBo4sh6KIaDYszCaJBd5dG+0Xbq/05OXKIYuV1UFi9fmLNfysq/DtwppEkWP/no3803ffRLMZMdFpWLe5rDZsLlSHFnsZc0sp5+b7zIdhc2lmVc6quUI1JLQKRFYdfRwbLiIioEqRiDwbrf5jk+2kWikp1FPsP+eIImg1YhqJDY9rxBGNJHQKC1Wj8U6Ds3MDXn7DlXz+9pOcnelaGnqcO6LVZoaiFoWHooSNTUcSuWEAazeg2QghLLKuc1E02hF2ztNIbFidx4bVYfkQby8UIlvc1YUnLodVp9qGOFsDqApGVeUIP6oYEYa9Lc1BHEOnHVJGCFa5g1N/D3uOhgqRGy0Qm2dhrlN4TB/C0HBh2apTXg5pGm6LXTcYWGc5nFWGSu/JMwuARQG9gaOfQukcWQFp7jg9D184WzI3GFWJiqpKVF/ANRzWCq+Pph58XVUhAqIkInKOTRs6/Lt//gaSZos9W8fCPKLMqkRpRq9vbeJnFy2gnz7X48xcn/mllO4gI8uroXNQlLV23GHoXPUdeJxfRRGRp5QqRSIiT6Jqx7A+v6LEutBV3bqyoiQrCgZpwVIvY3Z+wLm5PvNLtkDm/HJKv2/Dmmx+kY3x2rN9jOXU833f/Dq2bugQE/aAH0F9h7t+qK6rdspLsOpPYZWik0sl3aykm5ekuVW5ytI6yxVlGRbptPPVHKost0qYL0uc8ySxLehJ6ckzTz7wlLknz2x9obJaeyh0cHMhALlaE4RhO24f5huFCVAuh2wRmondNqqaLRTwwCfg6peBXwovtIAoDIkru3a6GmbHAHw/nC7CnKGw0OvYJMzN2OVlBlH1mgpPkXnSHgwG4UN2nkZS0ml5nC+JopLSl8z0Sub7oUq0YpHf8z+T+mfzWHlCRS10u4jiiO/8Jy9nfGKcvdvHcHh8aKxQZDmDzBp9zC8OmF9MmZ7rM73QZ7Gb0R/kZFlJllfrEZWh6jmqhA6roo93w0VERJUiEXl2qnbyweHw4a9QVh2yeUWhahL+32hENJKYKLKd2WZiQ7FsfhHEcUSrmdAdwKtffBW/95d3UFr7NyitA9ylqu5S36ctgX4B7QTGEkcjzEux9YusehSHxYh8aDgANt+oyG3+kXOjttPejy6LYrt93LDTztmfxnwIRlVAqm+Qq8aahbBSjT07dxy27LSOeYSd9PnTkDRhcgPk83a6qiL5FNI+JI0QfkJ1qMzCPKHq8X2oKAELC5AkYS2i0DkuTa3JhM0tchThI4gT+9Ct+5xjehFuOw0PLXrSEvLQbS48xRMShKrPb0WVKA7fGzzf+XUv57nXXMH2zW2aiRsGojxLSdOMhVAhmluyYH5qpsf0grWK76cWiPPCqkNWIbKKUbVQaxXyHs9rEBF5OlyOlSKFIhF51nEu7O1WwWd4bKGIMIzOEybLhOsbsTVciCJHEkU0GjaMjjCUrpEkxLGjJObgvo184jMP2A6pczjvV+wkrz6uDhcy3LENw+jmB1jDhUZV4XA0EyixIWNRbOveeG9DxcJmknsH3uYY2TAzC0xlaa/F44ZVovo2OUJnNx/OhDKWVSTs4LAw4z089CDs2h2G04XL7r0N9l1tIShbDgWTwhZt9RkMli04VB3l8oE9d7XAbFFYIEoH0O9DhGNuztFI7HxZOMrC0U1tCF1WWEiy+VT2etPUMduF4zPwmVMlizlkF6gOVR5LqFj92VaByBorwDvfcC2vf+W1bNnQYryd4AubP5RnKXlmneZmFvvMLg6YnutzarbL2bk+i0sp3TQPzRVCCCrLsGirBaKqWsRj3HYRkaebQpGIyFPAgko9hIyCkHPeyiPV9aGi5MM8nWYckcQRLrJ5PY0wN6SqMLWaDUoPe3Zu4sDeKT7x2eMUpe0V+2pPNTzxWj/eVweRSpVFqtOlh8UM2hF0Yqv25IVVQqpudDYvyBovxM7mIzks+PlQWYliu00SW0e+Mvc2tyiy66vKT1UtGg7FCsfDZgzVbQtrsHD6Idi5C8owFO/0Q7BtFzRC5WiwFEYXhiqQL2HQt8pSno7Oe28LzBa5LVqbh/lEVUe52QXbfrxjkNrrB2uu0OuHYIsFpG7fMd+Dh6Ydd571PLjk6RVWJaoaWlQZr3qJjyVU1D+/aFUgcg7e/vpr+JqveCHjY002jrdsLaK8oEhtSOZyN2U2BKKZhT5nZrqcnhnNI0rTkiysSZSH6lARhkn6sNEaNiciz2QKRSIiT5HVwcNqQd6OnVUh7L+QjsJOZhSCUBzZ+jJJ7GjYSqjDrnOdVkIvLdi9cxNj7ZhP33IypCsr3VgwGQWdtX7M1y+rb6sLO9k+hJx+DhMNRytxlDgasbXqjqOqoUAISVEIP4kjDk0VyhK6PUdvAP2+NSpoJJA0LDRZ2/JQIQrhqKo4hYLaaDtDIAKr6izOwaaNdllWwP3HYe/uMC8phsUZaI2FeUvO7l81WigLqwpVO/jVzn5V3cpzRxaG07Wbjn7qyELVqygjW4spstfnnK3jNMisgjS9aGs8nV70nFi2BVvrbbhZFYrqxxejek9CDwkLRGHIZQS89Pn7+JYPvIxGM7YFWouCMs/JQ/vtXn/A7FKf2YUBswt9zs72ODXTC2sSZQyGw+ZGi7Ta0DnwocFCFYguZbtFRC4nCkUiIk+h6uerH56uglDtyioYhTO+hCSOaMSjClEjiUgi2x12zvpwT3SadAc5h/Zvp9tLufP+s5RhMVHvq17TK55mGJKq47r6+bLKER4GJfRSmEgcjcgaMhSF7Q5noYOcNSGwSlJZQj+Dxa7tQHdajslxmBizdX+iECbAwkea2lA7x6jyUA2ZK8OwuOoy7y3kLCza6Ykxey23fB6uvhISZ4HIe1ichWYrvI4wXC+vOtTloTpUQpY78tBSPMsgTR2DzN7rtHAUpaM/sNdWeAtzRWFDAnuZ3X+p7xiE47kunJzz3HLWs5xj84mqClEIEiH/ETLZRbEtGh0iZ6HSxRFxHOGAaw5u47u//jV0Og22bewMO81Z046UwWDAzGLK7LzNIzo72+fh6S4zC9aOuzcoycI8IhsuF7rNhSFzJaMkdLHbLSJyOVIoEhF5CnlC6Kn9nB2edDbMzG5YHY+O4siRJDHOQeysQhNFIVSFH94TYy3mljJe9oIrmVvscfd950ZPWHrb6V61E1vfmXXhfLVN9euGO+4hGC2lnsmmt8pEGB6XFzDWsmpRpxFuHxJVM4GxVtWe26pXPswRqo6LAqLYHpNaO1JfjrrADTvDEYbRAcuLMD5m233qBCzPw759o+YNZQGzs9BshIYKqVWDsszuk+ej+UNVpa4IQSnLLbRVoSlNbTOyzCpFaebJCxtKtzxwLPZgsQtLfZjreR6eh1tOl5zsega5teKuqkTV0LnquDpcrNXByEWjIXPXHdzGD337G4gbDXZtGaMsCso8I09z8ixjMEhXLNB6dn7AqXPLTC9Y18NeWtg8oqIMc8DK2hyi8Du61jxDROSZTKFIRORp4LC9X+cAZzuxzlmrhSqSVD+L64thxokNUyPsADdiR+zCELFQOZocazK9mPLyGy0Y3XXfWbw9gTVfqO3A1gPQavXL6/u81Y57r4DlFCYS6DRsMn8cFo+NwhyjOLZ8F4XThKFpRTkatlaG4WR5Uc1BsuqYr+b2lOE+RZizVC3c6kOHuBIWF2yDZ89Bs2Nd5saa9h760HhhccG2v7p/UUKW2nEVyizwWNgpvYWm3Nv5LIfS27yiNHfkRaiSlY6shOWBY7kP/RRSD2kG00tw76znvgWbS5R6m09UD0CXGoTqXAiOzkGcRMSxfZeuObCNH/rnb4AoYffmDt6XlHlqc4jSjDRNmV9KmV3oM7cw4NzigFPTXc7M9plfzmweUQhERViotVqXyLrshWAUAtFj3X4RkcuFQpGIyNOl9rN29fyiFT+Iw068BQFPEsfWAttbhabRsBbdEIJV5JgabzK9MOAF1+1j26YOn/7CCdtxjWpd6cKwveoQLlpxvm51SPLe5s4sZ9CKIQltucvSglDprbtc4R0+bFfpbR6Sc5CXEXlpt0szG5bmwxNVzQqqYW1lGJ42bIUd2mcXhTVD6HUtGG6YhHsfgD077DrC8Lo8w6o0fWg0wnC5MB/JRY48s7DjvW1bdToLFaDS2xC6vLT22nlhbcp7mV3ezxy9FLqZYzmFxT42bG4J7p3zzPZt2Fy1xBJrVIcuNhxVn08U5hFVTRWSyL5Fb371YT70gZfRaDTYvXUMfLU4q1WI0ixlYckaKswtpUwv9jk13ePMbI/55ZRuP2OQleTDeURVC+4QiMLQOTSPSESeRRSKRESeRhaFqsARztUqR1ANN7PbFWFqkLXptgpBhDUziMIP7+oH+dREk0FWcOjK7ezbMc4nPvugPUg1Ni0YPf/KQFS/fC3VTnzmYZDBeGLD+gpGoSJJalWe0iorFvBsSJovLUzYznbVMc9ec5bDIA3BKszlyXPboiIM2yo9PHwKNm0K3fA8nJmGjRMWfKod9qK0+Tanp214X1lNksIaQFg1yo7tckdZevLSkWYRaW7vjFWILNhlhc0xygoYhHlI/cyqZ/N9OLXkOT5f8nDXMwjVsGLVsLn66UdTfTbVoaoQDQOR87z1tcf4p+++ibFOkx2bbQ6RLzKKQRbWIkpZWFrZae70dJfTMz3mllKW+zlpaKyQrWiqYJWhYSC6hO0WEXkmUCgSEXk6hWrNKJWEmlHt57DD9j49Hkprhezx1qYbGzs3DEbhgeyHecREp8VyP+OKPdvYtX2Cz93+MHlmLdJssF6Y27NGAKrm86y+fIVqXaJQMbJiUegk56yaZWHOhqBBCEDYIqiLvRCQvG17UdTeEG8BJGmMqjrDpw3vU39gw9TGxuxx5xdtmGAjCZ3gwiKyYK23Hz4Lm6dCJ7wiVK7CUDqbH2OBNGnY+znIrBV3Feaywio+WVhnKS0gC626s3B+qW8NF+Z7cN+Cp5uHFtz28a0IuZVHChf1IDT8mhAaWoS220kMX/66a/m6d76EJI7ZtmnUVKFIq0CUsRiGzA0D0WyXUzPWZGG5l9HPbB5RXh82V3prv615RCLyLKZQJCLyNHNrpJIqFzjnhgHJeUeJD/NabI80jiMr/IRmB1Yxqh7EdvAnxpv005ydOzbyyhuu4K8+9QCDNF8xz8iH7ajv59Z3wNdS3bYMvQ/6BXTDULpW4kgiC0jWmtuGyZVYE4aytPDgw9wiY+GjLG0x2EFqjRLKEI58mM9TlHa7vHA8fM6xa6uFGoD7H4atG214W1mO7gd2v1Mzjk2TYT5QaKntIqtkWUtuG+pHKKgNUkd/YNtTFNDLHVkeqkRhCF6aWzDqZZ5eBosDmO157pkrmRt40hC6ylDZWmvY3CNZ/TlEhIVyI/vsW82E/+drXsaXvvY6mq2YbRvboalCSp7mFKFCtLhkTRVmF/vMzPc5PdPj1HSPucUBS92MflrWGitU84hClWiNeUQiIs8mCkUiIpeDEIxsxJyFmeri6v+2H+rCujCeMrTBrtovwxoVo3A83mlag4G4wZe+6jCfu+1hZue69oTO4au93SBszkWpbuc9DApYTKEVeZLIushVjRL6mS3SmpewPIDuwO7pvXXWK0qPC7fPc89iz6o7WVhotQzd4vLSOsOdPOOZ7ECrYXOO4gjuPQGbJgmtva0alWV2X+fh5FlnQ+sKbxWkkEq8hzT3oyGJzpoupLkN47NW2zZMMAv3zXKrGPVyWE49S30bOrfQ8zy8WHJiyds8ojCXqApElxKK6r+OXThEsf3Sjh1smmrzw//8izl6aDebplpsmmxR5rm13Q4Lsw6HzC3Y2kPnFvqcme1xerrL7MKApV4IRHlBnldBqGqsUA9EPgx9fORtFhF5JlIoEhG5XKz42VvFmeryqhWD8aW3OSqljWWKYkfkbTgc3hZEtYqRt/tG0GwktFsJ3YHn9TcfYG6px33HZ2o//EfPVzv5iKrr6zv3eQnzqVVWGmFPPgsNCtLCW4e23FOU9pw2LMvuN8g8vQF0BzYkr9WwUJFm9vhZEbq6LVq3t33b7bI8tMx+6CxMdaCX2sKwHgtiRWnzeRaWQlvu0obF+ciqPdYJz4bcRbEFnyy3OULdgWOQW6OGqtnCIHNkYdjgIIPlMGSul3kW+p775zwLmc23yi9QIapb/T5XAag6HYXKVRyGy8XOcd2hbfzgt76eHds2sWNzm/FWTFnkFHkehsxlDFJrqlDNIZqet0B06lyXmcUBS72c/iC3OUS5tdxeu9OcGiuIyLObQpGIyGUr/DB2o1bdw1CELchqrayt3VsU26603caGr8W1n+cOWwR2fCxhqV9y8/OvZOeWcW69+zRZXuAim2fkhr3fzt85X32oP3a1s19i824WMhtSV8256RfWpa1beJZTa3Xdy6261EsdaemY74En4tyiZ7Lt6KYRvTR0gSusKcPsUsRtpzzH9trlWe7oDhxn56GbOuIkYqlvz+W9NUAovGO5bwvZzixC6SP6oWlCHtY88mFx1mrx1t4gYrHr6GWw3Hf0Mke/GjpX2vC55RT6mWM5tzlVc324e7bk3MDabxe16tCFGhNc6P2NqmMHceyGgajZcLzltcf4Zx94OWPjbXZt7dCII8oip8ytw1yRZvTTlIWwDtHswoCZ+R6nZ62xwsxiylI3ozcoGFSBqPA2lygEI2t+YfOJqIU6EZFnI4UiEZHLTBUw7HRYhMg7nKvaIhgffk6WpbchT94TRzZwzpcWopLIhlkR/sLvHMRRxIaJJt20YN/uLbz4eXu5456zzC/2h62z8TaUzYX7rP61sPp8dVkVikqsucBCDvMDG4bmq7V/crtt1a2tCBWIQQ79HM4teeLI0W7YfKJBbvfv53B2AW592HPFZmsykZV2XTeFEzPQiG0NofkuLPRto7qpVYXSsA7SQhd8ZBWfrLCJVL2BzXcaZI7+AHoDC2rLqWOp71geWIe5rLDtSAuGnea6OSwOPOe68MB8yemeLW6b10LRKMyuDBb1ELT6vKtXh2KbK7ZpqsOHvvpm3vza59Bu2aKskfeURU6e5RRZqBANUuYWqjlEoanCTI9TMzaEbqmb0a1XiIaByFOEYHRepzklIhF5FlMoEhG5zAxDSPWzODQKcKEzWqUKSKW3IU7WKMCPfpCHLmFRZPNt6iGHsMircxAlDV5/80FmlwacODlj7aqjMC/J1apGq8JRfee9Ol+JagEgK2ExzMtpRC7M27HXUt0mDUPgllMLM7s2RpTesTiAQeFYGjhOLcI952DPRkcSW8hJi4i8gOVBxD3nYKId0U0d55bh3rP2uovQCa/0jjSPmF22re2lVlXzOEpszaQ0d/RzWOpbhWqhb+EHZyFuObXuf0VhgS4t7XXN9eChxZLTPc+gvh5R7TUSjuvvWaW6rF4dcpEbdpeLnOP6Y7v4lx98NYeu3sXGyQabJ1v4osCXtUCUZvT7KTOLoy5z0wsDTk93OTVrXeaWuhn9QUGW21pE1mXu/Nbb9ns3DJlTIBKRZzmFIhGRy4yvgku1B12/nPMvqyowZelJC09ZlMMZSB772QmOOPK4MBSqCjitZsJYO2FpUPCyG67iyFWbufPeMyz1Mvtl4BxR2CGufjesFYIe6ddGFQp6JcwMLGR4sEVcQ4tuj1WKzix7No05GrENT1tKrZvb8bmShxc9G9rV4D6bC9QdWCg5t+S5/XTJZMuxMIBTi/DgvCfNHa3YhflXVvGZ61lYGoSmDZ4QhlJY6ltYmu9Vc4RsKF1eWlhaTj1lAb3QYGGmC8fnS+6eKzlbLdAaqnJVhahc1dWvUgWh+vvpQpOHqrtcHMGGiTZf/WXP55+88yWMjbfZublDp5Xgq+Fyqc0hytKMbi8dVobmFgdMzw84NdPj9GxvFIjSkiwvSGuBKC9KC9bh4IctuBWIRGR9uBxDkTt69KgHKMtyxaEoCqanz66+vYjIs1JkmSTsKFu1IIrCkLgwx8RORzSTiFYzYqzdYGqsweYNLXZsHmPrhjabplpsGG+xcaLF5ESDVqNJ0mgQNxrEjQQXxURJzNm5Pv20pMwyfvrXPsmf/vXdpHlBgRt2JKM20X718SNxVbOAcEgcTCQw2YBODBNNC0UbO9BJrEFDiWN+4Jnp2WNsaMF4Eyabo4VVPZ6F1MJJv4Ad4xak0rCeUOJgSwc6DZhsODpNSMLzTbZsSNpE2+bslGFx2X5m6x+VwyqbY5B7SqAXHntp4Jntex5a9MwOrBqWrdFdrgyv/5Heq2FHciCKHC6KiJ0NIXzukR1803tvZvu2DbSaEds2dkJ1qKCo5g9lGWmWsbScMb/UZ34pZW7JAtGZmS5n5+2ybn/UZa4aMlcFoqpKtFYgWmubRUSebbZs2UYcx7bcQe3wdFIoEhEJRsHIduCrYGQLdlo1IYkhiWOaiaPZiBlrJUyMNdg02WLHpg7bNnfYMNG0YDTZYsN4k3arQdJskCQWjKIkIYpj+mnJqdk+Y82IT3/hQT7y0U9zz/Fpcm9tu0vv8aUNq6p2+Fljp9/qVCOrKyJVOIqxqk0DaITGENV9faiCVUP/GhE0w4Pk3m6bhZbXWaj4uPAEZXgA5+x2UXjcKJwfj2HzOOwad2wcC88dWXOK+b41fxhua2RrEGWFZzG1ZgrTfc98Gp7fh/lD9e2uHSrD7VvFEYbKheDrgK2bOrzzS57DF7/iKAWOnZvatJuxrT9UdZjLMvIst5bbyylziwMWuilziynn5vucne5ybqHPwnJGb5DTT606lOdhHSJfzR8aDZ2rhswNQ9HqjRUReZZSKBIRucytXTGyhglVMIpjaEQRSagYtRsWjDZOtNixsc3WzR02Tlgg2jDZZMNEm/FOg0YjsYpR0iBuxFY1imOm5wcs9woicn7zj2/lo39wKwsLPcqwplEZGjywaud59XGlHgZWh6MqrFSXV+2n60GqerzIWZCqrhhWM6oktcZzDx8r3GfY3hpoJlaxmmjCWMMx1rAucnZb65rXyz39HBYzz3KYR5SH5y3CNgyHyoXnrAei1UFoxXsRWci1+WKeTjPh1S/Zz1e95QVMTo4x3o7ZsqFt1SFfUGQFRW7VoSzL6Q8y5pcGzC8OmF9Kme+mnJ3tcWa2x+zCgMVeTneQkaalBaKiqhCNwpACkYiIQpGIyGWv2qFfOxhVrZpt/kk1lM6G08VMdBpMjTfZuqHFto0dNk21h8FoarzF1HiDZq1iFCdWNXJxQpaXnJrpkUQR8wvL/MJvfoa//OS99Ac5ZVgTqbRZ+RYCqupRbW96rR3rCwWk1adXz2GqTke1OTrO24VldRoLSN6v8Zi1xxsGpCqMhceprhuGg1rYqV5fGZ6nfn21PfXXGx7yvNMOC0NWHbLnS6KI6w5t52u/8kb27dkKOHZuaYdW2wW+yCnyUSAaZDnL3YyF5QELiwPmuymzCwPOzfU5O2cNFRZ7Gf00J01LsqIKRNU6RJ582FhBQ+ZERC7HUKRGCyIiqwx3qut71/Xd7CodACW2V1t6QotlT1rY5HqLL6FbXdghdjhcaMLgvT2JoySOIjZOtnCRNRq4+flX8sLrdjO70GN6dhlflOCqSannbdHwuDpU6qcrq0NFfWhedfmKQ9hxH87hqapFtdsTLieEKEc4XdvpD5kOz6g1eMloflAR2moP1xuqPW/9eVafZtXrdlUAG3aUi4giaCQRR/Zv4evf/WLe9aUvYGpqnM0bWmzb2LbPo8hGc4fSlCzNrDq0OGAmLMg6uzjg3FyPh2e6nA6BqOowl2YFWV7NHbI/NuZhLlEViCwUKRCJyPp2OTZaUCgSEVmDJ1Q4qj18D2AVm9H4MUsAo+AQhkoVniz3pKl1GQMLTHmtgULkIGK0d2y/CjzNRszGyRZ5URI3W7z+5oPccM0u5hf7nJ1dpixLnItwUQS1YXBrHa/+9XKhUFGd9hc4UIWh8LJ9dX6NwFLdpgpQ9SBVnS6qgBSCUP2y6jlLRp3kVm9LdVxXvdao1k3ODiEMXbWFD777xbz/y25k29aNbJhssHPLGI3Ehc5yNmeoyFJbeyjNWO5ad7npResuN7Mw4Mxsj9MzPc7O91lYSlmqN1QYDpcLh2FTBWu7vaI6pEAkIuuYQpGIyDOIv0AwsgVeq7Mhzvjwc7S0ylBeWJWg6j5WXZ+HhTursGSPX+J96F7g7fJOq8GGcVv0tdFu80U3H+QF1+5idq7HubmutQJ3o+e3cWgrg8NaO931y+phY/X9qvNV6KkfX6jJwTAArfEY1X3q168ITWtcvvrxq8ej9nEMQ2CoDLkoInIRkYNmI+bwlVv4+ne9iK9++wvZunUDY+2EXVvHGGslNlQuzyhCGCqylCzL6fWtgcLs4oCZ+QFzyzZUbrgg68KAheWU7iBnEOYPZUVJGYbJ2Rwi+x6MApF9NzwKRCIiCkUiIs8w9Z3X6rSvl2jChcNaT9jhrYbSZYUny0oGWUFR2IC60vvQlczCkQuLttpes/38dZQ45xjvWAOH3qCg0Wrz6psO8oobr8AD52a6ZGkODqLa0DpXqxTVD9SOV1srcKy+rh5MVoel6roLHdYKOWtd5muPV6lve/21RK7eVjsiCvOGJsabvPC6XXzofTfz5W+8np3bN9JpJ+zeOsZEJ8H7gjLPKLMstNm2MDRIUxaXBswuDYaLsc4u9Tkz2+X0TDfMH0pZXM7oDQoGWWmLsg7bbVsgKkvrNleWWKMMFIhEROoux1CkRgsiIhfBhWrEqDuddTKLnBs2XYhD++4ociRxRCNxNJOYdjNmvJ0wMd5k82STLRs6bJpoMjneZGKswdRYk4mxJuOdhGajQZIkREkcGjFYlzo7OBaWM6YXBtYUIM/53T+/jT/5+D0cf3iBIi9C0LDJPMOW3iG51HfGV59eHYTqqutW365+Olrj/tWvt9UBp35+rfutZRiGwntPaKcdTpJEjq2bxrn5hit52+uuYXJyHA9snmoyNd4Mrc1LfJlT5gVlXjVTyEnznF4vY6mXsrCcsdRNWexmzC2lzCz0mV4YsLicslQ1U8isOlSEaqBVhUZD58rQFKMsGQYiGDWNEBFZ7y7HRgsKRSIiF6m+E24BadSZLqo60kVWsbB1eBxJ4mgkEa1GTKeVMN6xYXGbp1psmmyzYaLBxFiDyTELSBOdJp12QqvqTheHgBTHuHgUjnqDnDOzA3COhvPcdf8Z/vRv7+WTn3/QhtcN1zdyw+o/3ioXVCFnjZ30RwowrHF+teo+l/L3vtW3rZ93WEmoCqL2h0R7lgjHxEST5x/bxatfsp9rDu+i2Wzjfcn2TW06rQRfluFQ2LpDeU5RWBjK8px+v2Cplw6D0HIvG3aXm5kfWCOFXkavnzPIbO2hajHWqiJkc4es01zpbdicvechCFWdAkVEBBSKRESe+YbBCHARRIR2z5GFpDh2xC6sZ1QtUhqqRo0kptUcLfi6caLJpsk2myebTEw0GG83mOxYOBrvNOm0Y5pJgziJh+EoimOiOMK5GBdH5IVnZmHAwnJGp5WQZxmfv+0h/vTj93HbPaeZXxyQFSUeC0hUQ7l8aO1d2tC9KiBdKPSsvrwKPtXl9TC0+rhSv339svPOVyEIe6OjsK6QC8PlJttN9u/bxMtfdBUvfN6VTE2OMchKJscSNk+1SOJoGIQsDJVWRStyyioMDQqWQ3VouZux2MtY6o2qQ7MLFpRs3lA+HCpXFJ4sVIXqw+Tsd2dt/pAaKoiIXJBCkYjIs0A9GFEFo7DDbsPp6tUjG16XRJFVjeKYZtPRajYYb8VMjDXYNNFi02SLDZNNJscsHI13LBhNtBu02gnNJLZwFKpHcRwRxRG4GBdZN7pBWjA936eXlrQaMREFd993hj/92/u45e5TnDrXpT/IbKcd8N6aM5TYTjy14xWljVVpxq8KPPVgVLf68tWhyFVvJKEKNHxfLQTZHRyNZsy2qTaHr97Gq150Fdce3U3SaJAX0G44Nm9o027GVg0rS5szVFgYKkMYKvKCrCgYDHKWe1YRWu6lFoz6GfOLGbNLA+YWByx0M5b7tljrcN5Qbe5Q1V69LKpQFDrLaf6QiMhFUSgSEXkWicLe/op5RtVwujDnyALSyqpREtuQumYjptOKGWs3mOw02DjZZONki43jTcY6DcbbNtxuvNNgrN2g00pohLlGcW1IXRRHuCi2dYwih3MR/bRgZr5Pt1fQaMU0Y0e32+PWu07xqS+c5At3nub09DL9LMcX3hZhHc49cmFnvgpJYee+Ck7D0ytODHnccK7QaLibteseBqSqElTdw1lTv8g5Go2YLZNtjhzYyguu3c1zj+1k04ZJCheRZQVjrXgYhGzuVGlhqCwpixJfFBSFBaOiyMnygkE/Z7mf0e1nLPfs9HI/Y2E5ZW4hZXZp1FGu1y8Y5AVZZs0wqo6B9fWGqnlEVh0C723o3PD9UiASEbkghSIRkWeZYXWjmmeEw0VVQLLq0TAYOUcUh6pR7EiSaBSOQjOGybEGGyZaw0YMYyEYjbUajHcSOu0GY62YZjMhCaFoGI6imCi2bmy20KtVkPKiYHE5Z345JS+g2YhoJo7FpS4PnZzlljvPcMu9Zzh3bolzsz2W0gLvPWVubb9t5z6sxDoMTKEaUnsfqstcdQKs4uPDkDhCWsDOR5GjlcRMjjfZvWOSo/u3cezAFq7cs4XNmyYoiUnzgjiCDeNNpsYbJHFkQchauw3nDJVlGapDdshzO/QGRQhCGb0QhLr9nIWuLco6v5Qy301DZSinn1VhyDoEVu21q+qQDZsLc4dCm3UNlxMRuTQKRSIiz0K1UWCrqka2dk4cKkhxHKpHtSpSklhAaoZw1G4ljLUTJjsJU+NNNk60rAHDWINO064bbzfotBp02gnNZkwjieyXS/gFUwUkm+tkAYkoIgrJrShK5pczlro2PCyJI1rNGHxJHJUcPzFPWeR84Y7T9Ac5t95zhn5q83Aeenh+FIxCAPBVFagKQgDOU/162755jPGJNlHkuPbgNjqtBtcd2k6j2WDfro0URDQaMYPUQkgziZgYa7BhokkcOatOhe5xoyDkbXhcWeDDcVEU5HlJmuX0+jm9QU63n9MbVGGoYLGbsbA4YL6bstC1gNQb5AxSC0NpEbrKhapQVR2qV4mquUM+DD2kDKMNFYhERC6KQpGIyLPY+VWjUBEZVo1sUdH6kLoodKmL44jGcFhdQrsVM9aMmeg0mJywjnWTY03Gq3DUSoYBqt202zcbCUmYaxRF1oghimxoXbWej4si29Iw1C5yFnAGWUF/ULDUy8hyzyArQ6vxmMhBp2VzdpaXBySNiIlOAvXBc8MS0ei9WOrl5FlJu90gSWJ6aYEvIS8LigJaDWtAMdFJaLcatJqRTSMK4cP5URAqqyBUlsMQVIWioizJ0oJ+WtBPLRDZMLicfmpziJa6GfPLKfOhtXa3n9NPCwahMmRhqOokZ8HH5gvZELmqUuRrc4cYVosUhkRELoVCkYjIs9wwGK0ISLVGDIRwVDViGLb0diSxhaMksnk1zTii3bJW3mPthKlOwuS4rbsz3k6sdXczodNM6ISQ1G7EtFoxjUZEEtl8oygKFaRwsNPWNc/ZWD/rGFEt/ursOmqj3Za6qXWv8540K+mlxSMutOc9dJoRzYb9koscTIw1YVhVc5SldSSwduFVzcnCj60p5IdD41YOkyvJy5I8KxjUwlB/YCGoN8jpDUq6/YzFZWucsLicsRwqR/20IM0KsrwkKy0IVQvpjgJQSVlYRaio2puH1uYltvKsD69TgUhE5NIoFImIrBMrwlFUnbfKjKuqRWGOUeRsaFs9HCVRRBzmHTWTmFYjsspQK2GikzDRaTAx3mCiE4bSNW3oXbNhi8W2m9b+u9VIaDYi4iQidlZFcmEV8WFQcqGKFFLccGVx52rln+r8KNQMX+hqtfJRFaqGFw7DT7V2UjU0bjREbnQ8qhAVZWHzfDKr7vSHgSgnTW3uUD8Mm+v2cxa7GYvdlOXeqGo0yErS3MJQnpcU3g87ylVrC503VC6EIRsit3Lu0IqXKiIiF02hSERknVlZMbJGDFTd6YbVo7XD0ahbXUQcQzOOaTQj2lXwaTWY7CSMt23do7G2VY1azYRWw+YJNZsJ7WY8nLPUTKyKFIUhe5Gz01ThyFn1qB6QRschA4X/rSwUuRURwULDKDlU50cLya4MQtX5UQgKc3vykqwoSdOCNLcwlIZKT38wCkjL/Ty02M5Z6uZ0B1moINWqQsO22qNOckVYs2kYhuottr211x62LK8WY1UYEhF5XBSKRETWoareUhVeqnBkw9dsaJmFE0I77/PDkc09qrrWhYVgk5hmM6LdtCF2452Esba18u60YjrNhGYrphlbpanRGIWjRiOiEUc0EmvUkMRWOYrCkLqqKYMdW5Xr/EpRLSgFwyzkvXVeqIaXhfk49WBUzR0a/t4p/bCKk4YQk4bW2FlmbbLTrLQglFrr7O7A5gct9ex8P80ZZAWDrCSv2mqXVUXInsNCUFhodVUYGg2TC2EJDZUTEXmiKRSJiKxjw6pROGOd6kbzeCwcWQCKVjRoqOYkVesdjapHjThaMcSuGj431o4ZazXotGM6rYYNp2vENBt231Y4boS24NYFLwpzmkYhyTrm2XZVwSgahiOrDo3WGzJWVAmByIeFYqtGBSGEFLW5PEVp6wDlIQhZRackzaxKlOWlVYbSgu4gpx8aKXT7Ob2sIB1YCErz3AJU6cnzWkWoGiIXwpAPbbRXh6FRIKq2WWFIROTJoFAkIrLOVYGoqh4RhapRLSANw1GoFtn8HwslVUCxNY+sihRHEUliXeySOKJZW/+oGeYXdZpWOWq3LBy1mnZ9MqwUhSpUeLy4euxaBWlYvaqG2Q1fy8paURUiPGH4WTUkrRaIyhCGqvbXtkCqJxu21bagU80b6qcFvTSnPwjXpcWwmpTnofFCYesI1YfHVUGoqv6MtgVKXw6Dz7A6VBsqp0AkIvLkUCgSERFYo2pkp6tQZFdUlaTI2YKwcegKN5yDFIbgRQ6r7IT5QTYXydppV0PjqopQsxFCURLRbCW0E+sQV801qqpHcTyqSg0rV8NAFALcsFpkr6MKD8NhcjAMJvVwlJfW2a2oQlDhrS12npPmJYPU1hoaZKVVgGpzgqoqUl6FqdwqO8OwVQtDFoLC77dVoWhlZWgUhmzbFYZERJ5MCkUiIrLCinBUnV4VPKLIrqiG0w2DUQhEVZCyy6t1kEKVJ1SUqrWQbOhd6HAXAlCSRDSHw/CqqlNMozHqghdHkT1uaAhRDferNnwYikKSKEOZpfClVWXCELbCl2S5pwhND7K8sCFyWUlaepsHlIfhdEVV/RkNs7PgEx7PlysaJZTDytRoGNyKpgneTrMqDK2oCikMiYg86RSKRERkTVU4qk4PK0XhRMhFob13GEo3nG9UC0y1qtOowmMhqlos1kWjluA2VK6qCjmisE7ScPhcqBQNg1Z4TvvdFQ0DnYtGc3AsZIyCSllYxajwJUUR1gEqrSV2kXvyamhdEapItaF2VagpCo/HLrP5SaO5QVVFaBR8LDgNr68HHg2TExF52ikUiYjIIxoOp6sHpdrQutGwtVqFKAyvi2pD2qrQtOI24f7VMLhqnlBVjXKRzVVyoamDHVugGj5+rZJVbVf911jIGaPwEULJaMjaqLlB6UMDhhCgqiqPLz3FsNJj9ylCcimpmjbYs5VlOK5uG+YHEc5DaKldnh+EUBgSEXlaKBSJiMhFCUWjFdWjehWIKASgUKVxVMPZVoah6jzh+pXBauV9hnOZ7H+jEBQ2oHruUSCqtrPaWmM1nXoVxk4MKzK1qk3pLZKsCE0h+NTDVbU+0DDwVIErPG79cmytVVg1RG7FGkMKQyIiTxuFIhERuWTDQFSdH4aSKqCsrB5VgaceYtwwRI2qPSH7rHy88AQ2dG/lY1fP7apEdBGqoDM8HU6MAlI4HVJKdZvR8dohyI5LOw4VoXqIYnXjhPrzi4jI00qhSEREHjMLKSH0VJetEWjOq+6EM1FINlY5qgelUYiqHnn4GPVAVDszvOlaKSNcXr8q1I4swLgQVmq3qYeZchiGVoekUUCy+1SPM3z0YaXIztVuF06LiMjTT6FIRESeEMPQUzs/Ckh2SRVyVoSkYa6pKkbh9Ir7r6wOjR6repzhFY9iNIyOEE6qM8OgE0o551d0LPFU56vb2EOEwFQ9QxWOFIRERJ4RFIpEROQJtyLwhGBgQciB81UNaRho6rdnGIxWXj/KQ9W9h2fXVj3xWmoBZRiJhqGmdn4Yeka3HQapEJRGl628HQpCIiLPGApFIiLypFs99M372mX1ADQcchdO1+638nYXPl87UbMqrVQnV19cDz+M0s7qihLeEpf39nRrhScREXnmuBxD0dP77CIi8oTzodNa6Rm2qa4u86VdVpbWsa30YT0gX1KUJXlpx0XhRwuuhjWEbI2hcCiqQ7hueJtwu9pt8zLcrlp7aHif8FzDP8iFhVlDO21bmLXaztHrsaYLtTAlIiLyOCkUiYg8i9UDUemhCIGiChbDgFGODvXAZAEqnA7BaRRiqiBjQWd4uhpxUL+tr65b/dghuIWwU9ZacHtvwajadoUgERF5sigUiYisM1W4GFZf6odw+ShIhSpNLbyMglMt4Kw4rHHbFbcPQaweflZthwKQiIg8lRSKRERkGEKqYWnnhaW1wks98Kw+hNusVZkaHmrPKyIi8nRSKBIRkYtShZdhgLqIw+r7iYiIXI4UikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIREXnCxWy9/k18xz9/M4fj1deJiMjlRqFIRETkCdNkz4u/gn/18x/lE7/5r/nWF22g51ffRkRELjcKRSIiIk8EN8EN73g/b7niDH/yfz/H2bLg9N13cbpcfUMREbncuKNHj3qAsixXHIqiYHr67Orbi4hcJpq87gd+nh/+0l1MtVztck9/8Sz/5/u+ig//QWoXNa7nO375B3n/4Q20638Kypf4zH/9Nt7xU3fULpTHxjG2ZSdbx+qfRV3JYHmZ2blF0nUQEtzu9/Cxv/wW8u9/E+/4hXOoWCQiMrJlyzbiOCaKohWHp5NCkYg8s8UbePF3/Bc+9g3HcA/9IR/+2h/kf96yQLH6dji2v/M/8Df/+lru/T//i5/55d/jDz/1ALPZ6tuBcw7vtRt7aRrc/K0/wnd90dUcPbaHjQ0LRz5b5OF7H+CB6S5F1Gbj1o20+yf41J/+Ib/0i7/D35wMwfVZpvWq7+WTP3cDv/mut/M9f5evvvpR6TsoIs9ml2MoenqfXUTk8Srm+YdbTzDwGZ/9hZ/gF9cMRNA8+FZ+4Mv7/PA73sYXf+i/8r/+dq1A1OSGD/13brv7E3zuZ97OAU2QvwQZf/Pj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UygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdcUikREREREZF1TKBIRERERkXVNoUhERERERNY1hSIREREREVnXFIpERERERGRdUygSEREREZF1TaFIRERERETWNYUiERERERFZ1xSKRERERERkXVMoEhERERGRdU2hSERERERE1jWFIhERERERWdfc0aNHPUBZlisORVEwPX129e1FRORp8s/ef3T1RXIJfvTnb199kYiIPA22bNlGHMdEUbTi8HRSKBIRERERkafM5RiKnt5nFxEREREReZopFImIiIiIyLqmUCQiIiIiIuuaQpGIiIiIiKxrCkUiIiIiIrKuKRSJiIiIiMi6plAkIiIiIiLrmkKRiIiIiIisawpFIiIiIiKyrikUiYiIiIjIuqZQJCIiIiIi65pCkYiIiIiIrGsKRSIiIiIisq4pFImIiIiIyLqmUCQiIiIiIuuaQpGIiIiIiKxrCkUiIiIiIrKuKRSJiIiIiMi6plAkIiIiIiLrmkKRiIiIiIisawpFIiIiIiKyrikUiYiIiIjIuqZQJCIiIiIi65pCkYiIiIiIrGsKRSIiIiIisq4pFImIiIiIyLqmUCQiIiIiIuuaQpGIiIiIiKxrCkUiIiIiIrKuKRSJiIiIiMi6plAkIiIiIiLrmkKRiIiIiIisawpFIiIiIiKyrikUiYiIiIjIuqZQJCIiIiIi65pCkYiIiIiIrGsKRSIiIiIisq4pFImIiIiIyLqmUCQiIiIiIuuaQpGIiIiIiKxrCkUiIiIiIrKuKRSJiIiIiMi6plAkIiIiIiLrmkKRiIiIiIisawpFIiIiIiKyrikUiYiIiIjIuqZQJCIiIiIi65pCkYiIiIiIrGsKRSLPJI3NXH3F5OpLRWSdamy9gis3rL70sXuiH09E5JlCoUjkmaKxletuvAJmF1dfIyLrUGP7EV50FczMr77msXmiH09E5JlEoUjkIiRJsvoiwK2+wJx38XkXAODWuthFa986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"

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
  <p class="cover-eyebrow">{cover_eyebrow}</p>
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
