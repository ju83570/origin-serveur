"""Simulations explicites, utilisées uniquement par demo.py et les tests.

Le point d'entrée de production app:app n'importe jamais ce module.
"""

from copy import deepcopy
import importlib.util
import json as json_lib
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

import requests
from weasyprint import HTML
from weasyprint.urls import URLFetcher


ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "demo_narrative.json"
DEMO_NOTICE = "DÉMONSTRATION — texte préécrit, aucun email envoyé"


def load_engine():
    """Copie isolée du moteur : aucun remplacement des globals de app:app."""
    spec = importlib.util.spec_from_file_location("origin_demo_engine", ROOT / "app.py")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


def response(payload, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json_lib.dumps(payload, ensure_ascii=False).encode("utf-8")
    result.encoding = "utf-8"
    return result


def narrative_chunks(offer, clients, life_paths):
    narrative = json_lib.loads(FIXTURE.read_text(encoding="utf-8"))
    if offer == "couple":
        narrative["mantras"] = [
            {"prenom": client["prenom"], "texte": text, "note": f"Exemple de démonstration : chemin de vie {life_path}."}
            for client, life_path in zip(clients, life_paths)
            for text in ("Je prends le temps d'écouter.", "Je formule une demande claire.")
        ] + [{"prenom": "Ensemble", "texte": "Un échange, une étape à la fois.", "note": "Exemple de démonstration."}]
    else:
        narrative["mantra"] = {"texte": "Je choisis un premier pas à ma mesure.", "note": f"Exemple de démonstration : chemin de vie {life_paths[0]}."}
    first = {"lettre": narrative["lettre"], "sections": narrative["sections"][:3]}
    second = {**narrative, "sections": narrative["sections"][3:]}
    return [first, second]


class SimulatedServices:
    """Transport fermé : les seules réponses possibles sont locales."""

    def __init__(self, chunks):
        self.chunks = iter(deepcopy(chunks))
        self.claude_calls = 0
        self.emails = []

    def post(self, url, *, json, headers=None, timeout=None):
        if url == "https://api.anthropic.com/v1/messages":
            self.claude_calls += 1
            return response({
                "content": [{"type": "text", "text": json_lib.dumps(next(self.chunks))}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 0, "output_tokens": 0},
            })
        if url == "https://api.brevo.com/v3/smtp/email":
            self.emails.append(deepcopy(json))
            print("[DÉMONSTRATION] Envoi Brevo intercepté localement ; aucun email livré.")
            return response({"messageId": "local-simulation", "simulated": True}, 201)
        raise RuntimeError("Destination interdite dans la démonstration")

    def get(self, *args, **kwargs):
        raise RuntimeError("Accès réseau interdit dans la démonstration")


class OfflineFetcher(URLFetcher):
    def __init__(self):
        super().__init__(allowed_protocols={"data", "file"}, allow_redirects=False)

    def fetch(self, url, headers=None):
        parsed = urlparse(url)
        if parsed.scheme == "data":
            return super().fetch(url, headers)
        if parsed.scheme == "file" and parsed.netloc in ("", "localhost"):
            path = Path(unquote(parsed.path)).resolve()
            if path.is_relative_to(ROOT / "static"):
                return super().fetch(url, headers)
        raise ValueError("Ressource externe interdite dans la démonstration")


def demo_document(document, *, pdf=False):
    # Les polices de secours sont locales ; aucun chargement Google Fonts.
    document = re.sub(r"@import\s+url\([^)]*\)\s*;", "", document)
    document = re.sub(r"<link\b[^>]*>", "", document, flags=re.I)
    if pdf:
        marker = "<style>@page { @bottom-center { content: '" + DEMO_NOTICE + "'; font-size: 8pt; } }</style>"
    else:
        marker = "<style>.demo-notice{position:fixed;top:0;left:0;right:0;z-index:9999;background:#fff4cf;color:#302415;text-align:center;padding:8px;font:14px sans-serif}</style>"
    document = document.replace("</head>", marker + "</head>", 1)
    if not pdf:
        document = re.sub(r"(<body\b[^>]*>)", r'\1<div class="demo-notice">' + DEMO_NOTICE + "</div>", document, count=1)
    return document


class OfflineHTML(HTML):
    def __init__(self, *args, **kwargs):
        if "string" in kwargs:
            kwargs["string"] = demo_document(kwargs["string"], pdf=True)
        kwargs["url_fetcher"] = OfflineFetcher()
        super().__init__(*args, **kwargs)


def configure_demo_engine(engine, transport):
    engine.requests = transport
    engine.ANTHROPIC_API_KEY = ""
    engine.BREVO_SMTP_KEY = ""
    engine.EMAIL_DEST = "demonstration@example.invalid"
    engine.WeasyprintHTML = OfflineHTML

    def local_coords(city):
        # Pas de fallback Nominatim : la ville doit être dans la table existante.
        if city not in engine.VILLES_FR:
            raise ValueError("Ville non disponible hors ligne")
        return engine.VILLES_FR[city]

    engine.get_coords = local_coords
