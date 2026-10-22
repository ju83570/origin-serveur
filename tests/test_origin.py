"""Tests sans réseau ni identifiants. Exécution : python -m unittest discover -s tests -v."""

import base64
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import requests

import app as origin
from demo import create_app
from demo_support import OfflineFetcher, SimulatedServices, response


CLIENT = {"prenom": "Camille", "date_naissance": "1990-05-12", "genre": "Femme", "ville": "paris"}
SECOND = {"prenom": "Alex", "date_naissance": "1988-09-23", "genre": "Homme", "ville": "lyon"}


def claude_response(data=None, stop_reason="end_turn"):
    return response({
        "content": [{"type": "text", "text": json.dumps(data or {"sections": []})}],
        "stop_reason": stop_reason, "usage": {},
    })


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Un appel oublié doit faire échouer les tests, même avec Internet disponible.
        self.stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("Réseau interdit")))
        self.stack.enter_context(patch("socket.getaddrinfo", side_effect=AssertionError("DNS interdit")))
        self.stack.enter_context(patch("requests.sessions.Session.request", side_effect=AssertionError("HTTP réel interdit")))
        for name in ("ANTHROPIC_API_KEY", "BREVO_SMTP_KEY", "EMAIL_DEST", "WEBHOOK_SECRET", "STRIPE_KEY"):
            self.stack.enter_context(patch.object(origin, name, ""))
        self.stack.enter_context(patch.object(origin, "ENFORCE_ACCESS", False))


class HealthTests(OfflineTest):
    def test_server_alive_without_credentials(self):
        client = origin.app.test_client()
        self.assertEqual(client.get("/health").status_code, 200)
        result = client.get("/ready")
        self.assertEqual(result.status_code, 503)
        self.assertEqual(set(result.json["missing"]), {"ANTHROPIC_API_KEY", "BREVO_SMTP_KEY", "EMAIL_DEST"})
        self.assertFalse(result.json["external_services_checked"])

    def test_configuration_is_not_reported_as_remote_availability(self):
        # Sentinelles en mémoire : aucune chaîne de clé fictive injectée.
        with patch.object(origin, "ANTHROPIC_API_KEY", object()), patch.object(origin, "BREVO_SMTP_KEY", object()), patch.object(origin, "EMAIL_DEST", object()):
            result = origin.app.test_client().get("/ready")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["status"], "configured")
        self.assertEqual(result.json["missing"], [])
        self.assertFalse(result.json["external_services_checked"])

    def test_invalid_webhook_does_not_start_generation(self):
        with patch.object(origin.threading, "Thread") as thread, patch.object(origin, "WEBHOOK_SECRET", "unit-fixture-only-" * 3):
            client = origin.app.test_client()
            for data in ({}, {"email": "invalid"}, {"email": "client@example.invalid"}):
                with self.subTest(data=data):
                    self.assertEqual(client.post("/webhook", json=data, headers={"X-ORIGIN-SECRET": "unit-fixture-only-" * 3}).status_code, 400)
            thread.assert_not_called()


class ClaudeTests(OfflineTest):
    def test_existing_adapter_builds_and_parses_messages(self):
        expected = {"sections": [{"titre": "Exemple", "contenu": "<p>Exemple</p>"}]}
        with patch.object(origin.requests, "post", return_value=claude_response(expected)) as post:
            self.assertEqual(origin._appel_claude_chunk("Profil fictif", max_tokens=42), expected)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.anthropic.com/v1/messages")
        self.assertEqual(kwargs["json"]["max_tokens"], 42)
        self.assertEqual(kwargs["json"]["model"], "claude-opus-4-6")
        self.assertIn("Profil fictif", kwargs["json"]["messages"][0]["content"])
        self.assertEqual(kwargs["headers"]["x-api-key"], "")

    def test_rate_limit_then_success(self):
        with patch.object(origin.requests, "post", side_effect=[response({}, 429), claude_response({"ok": True})]) as post, patch("time.sleep") as wait:
            self.assertEqual(origin._appel_claude_chunk("Exemple"), {"ok": True})
        self.assertEqual(post.call_count, 2)
        wait.assert_called_once_with(15)

    def test_remote_error_propagates_after_three_attempts(self):
        with patch.object(origin.requests, "post", return_value=response({}, 503)) as post, patch("time.sleep"):
            with self.assertRaises(requests.HTTPError):
                origin._appel_claude_chunk("Exemple")
        self.assertEqual(post.call_count, 3)

    def test_timeout_propagates_without_real_wait(self):
        with patch.object(origin.requests, "post", side_effect=requests.Timeout("timeout simulé")) as post, patch("time.sleep"):
            with self.assertRaises(requests.Timeout):
                origin._appel_claude_chunk("Exemple")
        self.assertEqual(post.call_count, 3)

    def test_truncated_response_is_rejected(self):
        with patch.object(origin.requests, "post", return_value=claude_response(stop_reason="max_tokens")) as post, patch("time.sleep"):
            with self.assertRaisesRegex(ValueError, "invalide ou tronquée"):
                origin._appel_claude_chunk("Exemple")
        self.assertEqual(post.call_count, 3)

    def test_invalid_json_is_rejected(self):
        bad = response({"content": [{"text": "réponse invalide"}], "stop_reason": "end_turn"})
        with patch.object(origin.requests, "post", return_value=bad), patch("time.sleep"):
            with self.assertRaises(ValueError):
                origin._appel_claude_chunk("Exemple")


class BrevoTests(OfflineTest):
    def test_existing_mail_builder_preserves_attachments(self):
        with patch.object(origin, "EMAIL_DEST", "review@example.invalid"), patch.object(origin.requests, "post", return_value=response({"messageId": "simulation"}, 201)) as post:
            origin.envoyer_email("<p>Livret</p>", b"%PDF-test", [{"prenom": "Camille"}], "solo", "client@example.invalid")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(kwargs["headers"]["api-key"], "")
        payload = kwargs["json"]
        self.assertEqual(payload["to"], [{"email": "review@example.invalid"}])
        self.assertEqual([base64.b64decode(x["content"]) for x in payload["attachment"]], [b"<p>Livret</p>", b"%PDF-test"])
        self.assertTrue(payload["attachment"][1]["name"].endswith(".pdf"))

    def test_brevo_rejection_is_not_reported_as_delivery(self):
        with patch.object(origin.requests, "post", return_value=response({"message": "unauthorized"}, 401)):
            with self.assertRaises(requests.HTTPError):
                origin.envoyer_email("html", b"pdf", [{"prenom": "Camille"}], "solo", "client@example.invalid")

    def test_bundle_has_four_attachments(self):
        with patch.object(origin.requests, "post", return_value=response({}, 201)) as post:
            origin.envoyer_email_bundle("solo", b"pdf-solo", "vocation", b"pdf-vocation", [{"prenom": "Camille"}], "client@example.invalid")
        self.assertEqual(len(post.call_args.kwargs["json"]["attachment"]), 4)


class DemoTests(OfflineTest):
    def setUp(self):
        super().setUp()
        output = self.stack.enter_context(TemporaryDirectory())
        self.output = Path(output)
        self.app = create_app({"TESTING": True, "DEMO_OUTPUT_DIR": output})
        self.client = self.app.test_client()

    def test_demo_does_not_expose_production_routes(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/health").json["mode"], "demo")
        self.assertEqual(self.client.get("/ready").status_code, 200)
        self.assertEqual(self.client.post("/webhook", json={}).status_code, 404)
        self.assertEqual(self.client.get("/admin/codes").status_code, 404)
        self.assertEqual(origin.app.test_client().get("/demo/generate").status_code, 404)

    def test_solo_and_couple_generate_real_artifacts_without_network(self):
        production_requests = origin.requests
        for offer, clients in (("solo", [CLIENT]), ("couple", [CLIENT, SECOND])):
            with self.subTest(offer=offer):
                result = self.client.post("/demo/generate", json={"offre": offer, "clients": clients})
                self.assertEqual(result.status_code, 201, result.json)
                metadata = result.json
                self.assertFalse(metadata["delivered"])
                self.assertEqual(metadata["claude_calls"], 2)
                with self.client.get(metadata["artifacts"]["html"]) as html:
                    document = html.text
                self.assertIn("DÉMONSTRATION", document)
                self.assertNotIn("fonts.googleapis.com", document)
                self.assertIn("Camille", document)
                if offer == "couple":
                    self.assertIn("Alex", document)
                with self.client.get(metadata["artifacts"]["pdf"]) as result:
                    pdf = result.data
                self.assertTrue(pdf.startswith(b"%PDF-"))
                self.assertGreater(len(pdf), 10000)
                with self.client.get(metadata["artifacts"]["email"]) as result:
                    email = result.json
                self.assertTrue(email["simulated"])
                self.assertFalse(email["delivered"])
                self.assertEqual(email["attachment"][1]["sha256"], hashlib.sha256(pdf).hexdigest())
                self.assertEqual(len(email["attachment"]), 2)
                with self.client.get(metadata["artifacts"]["manifest"]) as result:
                    self.assertEqual(result.json, metadata)
        self.assertIs(origin.requests, production_requests)
        self.assertEqual(origin.ANTHROPIC_API_KEY, "")

    def test_form_failure_does_not_disclose_internal_error(self):
        form = {f"{key}1": value for key, value in CLIENT.items()}
        form["offre"] = "solo"
        with patch("demo.load_engine", side_effect=RuntimeError("interruption simulée")) as engine, self.assertLogs("demo", level="ERROR"):
            result = self.client.post("/demo/generate", data=form)
        engine.assert_called_once()
        self.assertEqual(result.status_code, 500)
        self.assertNotIn("interruption simulée", result.text)

    def test_form_generates_result_page(self):
        form = {f"{key}1": value for key, value in CLIENT.items()}
        form["offre"] = "solo"
        result = self.client.post("/demo/generate", data=form)
        self.assertEqual(result.status_code, 201)
        self.assertIn("Ouvrir le PDF", result.text)
        self.assertIn("Aucun email envoyé", result.text)

    def test_invalid_inputs_never_start_engine(self):
        cases = [None, [], {}, {"offre": "inconnue", "clients": [CLIENT]},
                 {"offre": "couple", "clients": [CLIENT]}]
        for field, value in (("date_naissance", "2025-02-30"), ("date_naissance", "2999-01-01"), ("ville", "ville inconnue"), ("genre", ""), ("prenom", "")):
            client = deepcopy(CLIENT)
            client[field] = value
            cases.append({"offre": "solo", "clients": [client]})
        with patch("demo.load_engine") as engine:
            for data in cases:
                with self.subTest(data=data):
                    # JSON null explicitement, car json=None signifie sans corps dans Flask.
                    result = self.client.post("/demo/generate", data=json.dumps(data), content_type="application/json")
                    self.assertEqual(result.status_code, 400)
            engine.assert_not_called()

    def test_unknown_artifact_is_not_served(self):
        self.assertEqual(self.client.get("/demo/runs/00000000-0000-0000-0000-000000000000/pdf").status_code, 404)
        self.assertEqual(self.client.get("/demo/runs/00000000-0000-0000-0000-000000000000/secret").status_code, 404)

    def test_transports_reject_unexpected_destinations(self):
        services = SimulatedServices([])
        with self.assertRaises(RuntimeError):
            services.post("https://origin-famille.fr", json={})
        with self.assertRaises(RuntimeError):
            services.get("https://api.stripe.com")
        for url in ("https://fonts.googleapis.com/style.css", "file:///etc/passwd", "file:///workspace/origin-serveur/app.py"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                OfflineFetcher()(url)


if __name__ == "__main__":
    unittest.main()
