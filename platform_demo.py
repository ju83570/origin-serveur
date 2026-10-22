"""Façade locale du pack Hostinger et de la démo Python, jamais du site public."""

import os
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, redirect, request, send_from_directory
import requests
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from demo import create_app as create_booklet_demo


ROOT = Path(__file__).resolve().parent
ASSETS = {"index.html", "arbre-vivant.html", "confidentialite.html", "logo-origin-officiel.png",
          "origin-vivant.js", "origin-commercial.js", "origin-vivant.css", "origin-integration.js", "origin-storage.js"}


def create_app(api_url=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    if api_url:
        parsed = urlparse(api_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("La façade de test accepte uniquement une API PHP locale")

    @app.get("/")
    def home():
        return redirect("/vivant/")

    @app.route("/vivant/api/", methods=["GET", "POST"])
    def api():
        if not api_url:
            return jsonify(ok=False, code="not_configured", error="API PHP locale non configurée ; les expériences locales restent disponibles."), 503
        try:
            # Destination fixe de confiance, pas d'URL fournie par le navigateur.
            headers = {name: request.headers[name] for name in ("Content-Type", "Cookie", "X-CSRF-Token", "Stripe-Signature") if name in request.headers}
            upstream = requests.request(request.method, api_url, params=request.args,
                                        data=request.get_data(), headers=headers, timeout=25, allow_redirects=False)
        except requests.RequestException:
            return jsonify(ok=False, error="API PHP locale indisponible"), 503
        result = Response(upstream.content, status=upstream.status_code)
        for name in ("Content-Type", "Set-Cookie", "Location", "Cache-Control"):
            if name in upstream.headers:
                result.headers[name] = upstream.headers[name]
        return result

    @app.get("/vivant/")
    @app.get("/vivant/<path:filename>")
    def vivant(filename="index.html"):
        if filename not in ASSETS:
            return jsonify(error="Ressource indisponible"), 404
        if filename == "index.html":
            page = (ROOT / "hostinger/vivant/index.html").read_text(encoding="utf-8")
            # Cette capacité n'est proposée que par la façade de démonstration.
            page = page.replace("</head>", '<meta name="origin-demo-premium" content="/premium-demo/">\n</head>')
            return Response(page, mimetype="text/html")
        return send_from_directory(ROOT / "hostinger/vivant", filename)

    @app.after_request
    def headers(result):
        result.headers["X-Content-Type-Options"] = "nosniff"
        result.headers["Referrer-Policy"] = "same-origin"
        result.headers["Cache-Control"] = "no-store"
        result.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return result

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/premium-demo": create_booklet_demo()})
    return app


app = create_app(os.environ.get("ORIGIN_VIVANT_API_URL"))

if __name__ == "__main__":
    run_simple("127.0.0.1", 5080, app, use_reloader=False, use_debugger=False)
