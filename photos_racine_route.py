"""
Route OPTIONNELLE pour recevoir les photos Racine (Famille / Lignée).
Branchée dans app.py (bloc protégé : si ce fichier a un souci, l'app démarre quand même).

Ce que ça fait : reçoit les photos envoyées par merci.html après le formulaire,
et te les envoie par e-mail sur contact@origin-famille.fr (Brevo, API), avec
la liste des personnes (en vie / disparu(e), année du décès).
Utilise les variables Render déjà en place : BREVO_SMTP_KEY et EMAIL_DEST.
Si l'envoi échoue, merci.html propose au client d'écrire à contact@origin-famille.fr
(rien ne casse, rien ne bloque le formulaire).
"""
import base64
import html as _h
import json
import os

import requests
from flask import Blueprint, jsonify, request

bp = Blueprint("photos_racine", __name__)
DEST = os.environ.get("EMAIL_DEST") or "contact@origin-famille.fr"
MAX_FILES = 20
MAX_BYTES = 2_500_000  # par photo (le navigateur les réduit déjà à ~900 px)


@bp.route("/photos-racine", methods=["POST", "OPTIONS"])
def photos_racine():
    if request.method == "OPTIONS":
        return ("", 204)
    key = os.environ.get("BREVO_SMTP_KEY") or os.environ.get("BREVO_API_KEY")
    if not key:
        return jsonify(ok=False, error="mail non configuré"), 500
    if (request.content_length or 0) > 20_000_000:
        return jsonify(ok=False, error="trop volumineux"), 413
    email = (request.form.get("email") or "").strip()[:200]
    if "@" not in email:
        return jsonify(ok=False, error="email manquant"), 400
    offre = (request.form.get("offre") or "").strip()[:30]
    try:
        meta = json.loads(request.form.get("meta") or "[]")
    except ValueError:
        meta = []
    files = list(request.files.items())[:MAX_FILES]
    if not files:
        return jsonify(ok=False, error="aucune photo"), 400

    attachments = []
    for field, f in files:
        data = f.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES or not data.startswith(b"\xff\xd8"):  # JPEG uniquement
            continue
        name = "".join(c for c in (f.filename or field) if c.isalnum() or c in "-_.") or field + ".jpg"
        attachments.append({"name": name, "content": base64.b64encode(data).decode()})
    if not attachments:
        return jsonify(ok=False, error="photos invalides"), 400

    lignes = []
    for p in meta:
        statut = "en vie" if p.get("vivant") else "disparu(e)" + (f" ({p.get('deces')})" if p.get("deces") else "")
        lignes.append(f"<li>#{_h.escape(str(p.get('i')))} {_h.escape(str(p.get('prenom')))} : {_h.escape(statut)}</li>")
    html = f"<p>Photos Racine · offre <b>{_h.escape(offre)}</b> · client <b>{_h.escape(email)}</b></p><ul>{''.join(lignes)}</ul>"
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": key, "accept": "application/json", "content-type": "application/json"},
        json={
            "sender": {"email": "contact@origin-famille.fr", "name": "ORIGIN"},
            "to": [{"email": DEST}],
            "subject": f"Photos Racine · {offre} · {email}",
            "htmlContent": html,
            "attachment": attachments,
        },
        timeout=30,
    )
    return (jsonify(ok=True), 200) if r.ok else (jsonify(ok=False), 502)


def register_photos_racine(app):
    app.register_blueprint(bp)
