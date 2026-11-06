"""
cdv_analyse.py : analyse gratuite du chemin de vie contre email.

Module facultatif, jamais bloquant (meme principe que photos_racine_route.py).
Ne touche pas au moteur des livrets.
Utilise la cle Brevo deja en place (BREVO_SMTP_KEY).
La liste Brevo "Chemin de vie" est retrouvee par son nom, ou creee au premier usage.
CORS : deja gere par add_cors dans app.py.
"""
import json
import os
import re
import time
from datetime import date
from html import escape
from pathlib import Path

import requests
from flask import Blueprint, jsonify, request

cdv_bp = Blueprint("cdv", __name__)


def register_cdv(app):
    app.register_blueprint(cdv_bp)

DATA = json.loads((Path(__file__).parent / "cdv_data.json").read_text(encoding="utf-8"))
MAITRES = {11, 22, 33, 44}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_hits = {}  # ip -> [timestamps], limiteur simple en memoire


# ---------- calcul ----------
def chemin_de_vie(jour: int, mois: int, annee: int) -> int:
    """Somme de tous les chiffres de la date, reduite, 11/22/33/44 conserves."""
    total = sum(int(c) for c in f"{jour:02d}{mois:02d}{annee:04d}")
    while total > 9 and total not in MAITRES:
        total = sum(int(c) for c in str(total))
    return total


def parse_date(txt: str):
    try:
        a, m, j = (int(x) for x in txt.split("-"))
        d = date(a, m, j)
    except Exception:
        return None
    if d > date.today() or a < 1900:
        return None
    return j, m, a


# ---------- contenu ----------
def analyse(n: int) -> dict:
    return DATA[str(n)]


def email_html(n: int, a: dict) -> str:
    t, e, o, c = (escape(a[k]) for k in ("titre", "essence", "ombre", "conseil"))
    return f"""<div style="background:#0d0b08;padding:32px 16px;font-family:Georgia,serif;color:#e9e1cf">
<div style="max-width:560px;margin:0 auto;background:#15110c;border:1px solid #b8975a55;padding:32px">
<p style="letter-spacing:4px;color:#b8975a;font-size:13px;margin:0 0 24px">ORIGIN</p>
<h1 style="font-weight:normal;font-size:26px;margin:0 0 6px;color:#e9c978">Chemin de vie {n}</h1>
<p style="margin:0 0 24px;color:#b8975a;font-style:italic">{t}</p>
<p style="line-height:1.7">{e}</p>
<h2 style="font-weight:normal;font-size:18px;color:#e9c978;margin:28px 0 8px">Ce qui te freine</h2>
<p style="line-height:1.7">{o}</p>
<h2 style="font-weight:normal;font-size:18px;color:#e9c978;margin:28px 0 8px">Un geste concret</h2>
<p style="line-height:1.7">{c}</p>
<p style="line-height:1.7;margin-top:28px">Ton chemin de vie n'est qu'un fil parmi d'autres. Croisé avec ton prénom, ton ciel de naissance et les années qui comptent pour toi, il raconte bien plus. C'est ce que fait un livret ORIGIN, écrit pour toi seul.</p>
<p style="text-align:center;margin:28px 0"><a href="https://www.origin-famille.fr/solo.html" style="background:#b8975a;color:#15110c;padding:12px 26px;text-decoration:none;letter-spacing:1px">Découvrir ORIGIN Solo</a></p>
<p style="font-size:12px;color:#8a7d63;line-height:1.5;margin-top:32px">Lecture symbolique, issue d'une tradition et non d'une démonstration scientifique.<br>
Tu reçois ce message parce que tu as demandé l'analyse de ton chemin de vie sur origin-famille.fr. Pour ne plus rien recevoir, <a href="mailto:contact@origin-famille.fr?subject=Désinscription" style="color:#b8975a">réponds simplement à ce mail</a>.</p>
</div></div>"""


# ---------- Brevo ----------
LISTE_NOM = "Chemin de vie"
_liste_id = None


def _cle():
    return os.environ.get("BREVO_SMTP_KEY") or os.environ.get("BREVO_API_KEY") or ""


def _brevo(methode: str, path: str, payload=None):
    return requests.request(
        methode,
        f"https://api.brevo.com/v3/{path}",
        headers={"api-key": _cle(), "content-type": "application/json"},
        json=payload,
        timeout=15,
    )


def _trouver_liste():
    """Id de la liste 'Chemin de vie' : variable d'env, sinon recherche par nom, sinon creation."""
    global _liste_id
    if _liste_id:
        return _liste_id
    if os.environ.get("BREVO_CDV_LIST_ID"):
        _liste_id = int(os.environ["BREVO_CDV_LIST_ID"])
        return _liste_id
    r = _brevo("GET", "contacts/lists?limit=50&offset=0")
    if r.ok:
        for l in r.json().get("lists", []):
            if l.get("name") == LISTE_NOM:
                _liste_id = l["id"]
                return _liste_id
    r = _brevo("POST", "contacts/lists", {"name": LISTE_NOM, "folderId": 1})
    if r.ok:
        _liste_id = r.json().get("id")
    return _liste_id


def ajouter_contact(email: str, n: int):
    base = {"email": email, "updateEnabled": True}
    try:
        liste = _trouver_liste()
        if liste:
            base["listIds"] = [liste]
    except Exception as exc:
        print("CDV liste", exc, flush=True)
    r = _brevo("POST", "contacts", {**base, "attributes": {"CHEMIN_DE_VIE": n, "SOURCE": "calculateur-chemin-de-vie"}})
    if r.status_code == 400:  # attributs pas encore crees dans Brevo : on garde au moins le contact
        r = _brevo("POST", "contacts", base)
    return r


def envoyer_analyse(email: str, n: int, a: dict):
    return _brevo("POST", "smtp/email", {
        "sender": {"name": "ORIGIN", "email": "contact@origin-famille.fr"},
        "to": [{"email": email}],
        "subject": f"Ton chemin de vie {n} : {a['titre'].lower()}",
        "htmlContent": email_html(n, a),
    })


# ---------- route ----------
@cdv_bp.route("/api/chemin-de-vie", methods=["POST", "OPTIONS"])
def api_cdv():
    if request.method == "OPTIONS":
        return ("", 204)

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    now = time.time()
    _hits[ip] = [t for t in _hits.get(ip, []) if now - t < 3600] + [now]
    if len(_hits[ip]) > 10:
        return jsonify(error="Trop de demandes, réessaie plus tard."), 429

    d = request.get_json(silent=True) or {}
    if d.get("site"):  # champ piege anti-robots
        return jsonify(ok=True)

    email = (d.get("email") or "").strip().lower()
    date_n = parse_date(d.get("date") or "")
    if not d.get("consent"):
        return jsonify(error="Coche la case pour recevoir l'analyse."), 400
    if not EMAIL_RE.match(email) or len(email) > 120:
        return jsonify(error="Adresse email invalide."), 400
    if not date_n:
        return jsonify(error="Date de naissance invalide."), 400

    n = chemin_de_vie(*date_n)
    a = analyse(n)

    sent = False
    try:
        r1 = ajouter_contact(email, n)
        r2 = envoyer_analyse(email, n, a)
        sent = r2.ok
        if not r1.ok or not r2.ok:
            print("CDV brevo", r1.status_code, r1.text[:200], r2.status_code, r2.text[:200], flush=True)
    except Exception as exc:
        print("CDV erreur", exc, flush=True)

    # l'analyse s'affiche a l'ecran dans tous les cas, le mail est un bonus
    return jsonify(ok=True, nombre=n, analyse=a, mail_envoye=sent)
