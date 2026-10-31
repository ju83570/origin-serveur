"""Outils de test d'ORIGIN : démarre une copie neuve de app.py, sans réseau ni secret réel.

Aucun test ne contacte Stripe, Brevo, Anthropic ou Google : tout appel sortant est simulé.
Toutes les valeurs de secret ci-dessous sont factices et n'existent que dans les tests.
"""
import importlib
import os
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Toutes les variables lues par app.py / photos_racine_route.py (noms seulement).
ENV_KEYS = [
    "ANTHROPIC_API_KEY", "BREVO_SMTP_LOGIN", "BREVO_SMTP_KEY", "BREVO_API_KEY",
    "EMAIL_DEST", "GSHEET_WEBHOOK", "WEBHOOK_SECRET", "ADMIN_KEY", "OWNER_CODE",
    "STRIPE_KEY", "ENFORCE_ACCESS", "CODES_SECRET", "PHOTOS_LIVRET",
    "PROFONDEUR_CHAPITRES", "TMPDIR", "PORT",
]

# Valeurs factices
FAKE = {
    "CODES_SECRET": "secret-de-test-codes",
    "ADMIN_KEY": "cle-admin-de-test",
    "OWNER_CODE": "ORG-PROPRIO-TEST",
    "STRIPE_KEY": "cle-stripe-factice",
    "WEBHOOK_SECRET": "secret-webhook-de-test",
}

PAYLOAD_SOLO = {
    "offre": "solo", "email": "client@example.invalid",
    "prenom1": "Test", "nom1": "Fictif", "genre1": "Femme",
    "jour1": 12, "mois1": 3, "annee1": 1980, "ville1": "Paris",
}


class FakeThread:
    """Remplace threading.Thread : enregistre les générations qui seraient lancées, sans les exécuter."""
    launched = []

    def __init__(self, target=None, daemon=None, **kw):
        self.target = target

    def start(self):
        FakeThread.launched.append(self.target)


class _FakeThreading(types.SimpleNamespace):
    pass


class Boot:
    """Une « mise en route » du serveur : module app neuf + disque temporaire donné."""

    def __init__(self, module, disk):
        self.module = module
        self.disk = disk
        self.client = module.app.test_client()

    @property
    def launched(self):
        return FakeThread.launched

    def post_webhook(self, payload=None, headers=None, **extra):
        data = dict(PAYLOAD_SOLO)
        data.update(payload or {})
        data.update(extra)
        return self.client.post("/webhook", json=data, headers=headers or {})


@pytest.fixture
def boot(monkeypatch, tmp_path):
    """boot(env=..., disk=...) -> Boot. Appeler deux fois simule un redémarrage.

    disk=None : disque neuf à chaque démarrage (cas de Render : disque éphémère).
    disk=<chemin> : disque conservé d'un démarrage à l'autre.
    """
    counter = {"n": 0}

    def _boot(env=None, disk=None):
        for key in ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        for key, val in (env or {}).items():
            monkeypatch.setenv(key, str(val))
        counter["n"] += 1
        if disk is None:
            disk = tmp_path / f"disque{counter['n']}"
        disk = pathlib.Path(disk)
        disk.mkdir(exist_ok=True)
        monkeypatch.setenv("TMPDIR", str(disk))
        if str(ROOT) not in sys.path:
            monkeypatch.syspath_prepend(str(ROOT))
        for name in ("app", "photos_racine_route"):
            sys.modules.pop(name, None)
        module = importlib.import_module("app")
        FakeThread.launched = []
        module.threading = _FakeThreading(Thread=FakeThread, Lock=__import__("threading").Lock)
        return Boot(module, disk)

    return _boot
