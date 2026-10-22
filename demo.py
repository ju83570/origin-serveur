"""Démonstration locale et hors ligne. Lancer : python demo.py."""

import base64
from datetime import date
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template, request, send_file, url_for

from demo_support import (
    configure_demo_engine, demo_document, load_engine, narrative_chunks, SimulatedServices,
)


CITIES = ("paris", "marseille", "lyon", "lille", "nice", "toulouse", "bordeaux", "nantes")
ARTIFACTS = {"html": "livret.html", "pdf": "livret.pdf", "email": "email.json", "manifest": "manifest.json"}


def parse_clients(data, offer):
    clients = data.get("clients")
    count = 2 if offer == "couple" else 1
    if not isinstance(clients, list) or len(clients) != count:
        raise ValueError(f"{count} profil(s) requis pour cette offre")
    result = []
    for client in clients:
        if not isinstance(client, dict):
            raise ValueError("Profil invalide")
        name = client.get("prenom")
        if not isinstance(name, str) or not name.strip() or len(name) > 60:
            raise ValueError("Prénom requis (60 caractères maximum)")
        try:
            birth = date.fromisoformat(client.get("date_naissance", ""))
        except (ValueError, TypeError):
            raise ValueError("Date de naissance invalide") from None
        if birth > date.today() or birth.year < 1900:
            raise ValueError("Date de naissance hors limites (1900 à aujourd'hui)")
        if client.get("genre") not in ("Femme", "Homme"):
            raise ValueError("Sélectionne un genre disponible dans le moteur existant")
        if client.get("ville") not in CITIES:
            raise ValueError("Sélectionne une ville disponible hors ligne")
        result.append({
            "prenom": name.strip(), "nom": "", "genre": client["genre"],
            "jour": birth.day, "mois": birth.month, "annee": birth.year,
            "ville": client["ville"], "heure": None, "minute": 0,
        })
    return result


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=16 * 1024,
        DEMO_OUTPUT_DIR=os.environ.get("ORIGIN_DEMO_OUTPUT_DIR", "/tmp/origin-revolution-demo"),
    )
    if config:
        app.config.update(config)

    @app.after_request
    def local_headers(result):
        result.headers["Cache-Control"] = "no-store"
        result.headers["X-Content-Type-Options"] = "nosniff"
        result.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return result

    @app.get("/")
    def index():
        return render_template("demo.html", cities=CITIES)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="ORIGIN RÉVOLUTION", mode="demo")

    @app.get("/ready")
    def ready():
        return jsonify(status="ready", mode="demo", claude="simulated", brevo="simulated", network="disabled")

    @app.post("/demo/generate")
    def generate():
        if request.is_json:
            data = request.get_json()
        else:
            offer = request.form.get("offre", "solo")
            data = {"offre": offer, "clients": [
                {key: request.form.get(f"{key}{index}", "") for key in ("prenom", "date_naissance", "genre", "ville")}
                for index in range(1, 3 if offer == "couple" else 2)
            ]}
        try:
            if not isinstance(data, dict) or data.get("offre") not in ("solo", "couple"):
                raise ValueError("La démonstration propose les offres solo et couple")
            offer = data["offre"]
            clients = parse_clients(data, offer)
        except ValueError as error:
            return jsonify(status="invalid", message=str(error)), 400

        try:
            # Une instance par génération : aucun mélange de clients ou de simulations.
            engine = load_engine()
            life_paths = [engine.chemin_de_vie(c["jour"], c["mois"], c["annee"]) for c in clients]
            services = SimulatedServices(narrative_chunks(offer, clients, life_paths))
            configure_demo_engine(engine, services)
            profiles, astros = [], []
            for client in clients:
                profile, _, astro = engine.fmt_profil(client, avec_transits=True)
                profiles.append(profile)
                astros.append(astro)
            narrative = engine.appeler_claude(offer, "\n\n".join(profiles))
            engine._valider_narratif_client(offer, narrative, clients)
            document = demo_document(engine.generer_html(offer, clients, narrative, astros))
            pdf = engine.generer_pdf_imprimable(offer, clients, narrative, astros)
            if not pdf.startswith(b"%PDF-"):
                raise ValueError("PDF absent")
            engine.envoyer_email(document, pdf, clients, offer, "client@example.invalid")
            if len(services.emails) != 1:
                raise ValueError("Message simulé absent")

            run_id = uuid4()
            output = Path(app.config["DEMO_OUTPUT_DIR"]) / str(run_id)
            output.mkdir(parents=True, mode=0o700)
            (output / ARTIFACTS["html"]).write_text(document, encoding="utf-8")
            (output / ARTIFACTS["pdf"]).write_bytes(pdf)
            email = services.emails[0]
            # La boîte locale décrit les pièces jointes, sans dupliquer leur contenu.
            email["attachment"] = [
                {"name": item["name"], "bytes": len(base64.b64decode(item["content"])),
                 "sha256": hashlib.sha256(base64.b64decode(item["content"])).hexdigest()}
                for item in email["attachment"]
            ]
            email.update(simulated=True, delivered=False)
            (output / ARTIFACTS["email"]).write_text(json.dumps(email, ensure_ascii=False, indent=2), encoding="utf-8")
            result = {
                "status": "completed", "mode": "demo", "offre": offer, "run_id": str(run_id),
                "claude": "simulated", "claude_calls": services.claude_calls,
                "brevo": "simulated", "delivered": False,
                "artifacts": {kind: url_for("artifact", run_id=run_id, kind=kind) for kind in ARTIFACTS},
            }
            (output / ARTIFACTS["manifest"]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            app.logger.exception("Échec de la génération de démonstration")
            return jsonify(status="error", message="La démonstration a échoué. Consulte les journaux locaux."), 500

        if request.is_json:
            return jsonify(result), 201
        return render_template("demo_result.html", result=result), 201

    @app.get("/demo/runs/<uuid:run_id>/<kind>")
    def artifact(run_id, kind):
        if kind not in ARTIFACTS:
            abort(404)
        path = Path(app.config["DEMO_OUTPUT_DIR"]) / str(run_id) / ARTIFACTS[kind]
        if not path.is_file():
            abort(404)
        return send_file(path, mimetype={"html": "text/html", "pdf": "application/pdf"}.get(kind, "application/json"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
