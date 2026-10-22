"""Contrôles d'accès seulement : aucun calcul ni contenu de livret.

Le catalogue est une configuration approuvée, jamais une valeur du formulaire.
Exemple de structure (sans tarif implicite) :
{"solo": {"price_id": "price_…", "amount": <centimes>, "currency": "eur"}}.
"""
import json
import os


def strong_secret(value):
    return isinstance(value, (str, bytes)) and len(value) >= 32


def payment_matches(session, offer, catalog, mode):
    """Refuse les abonnements, gratuités, remises et offres inconnues.

    Les réductions et la fiscalité demandent un contrat de commande explicite ;
    elles ne sont pas déduites de métadonnées contrôlables par le client.
    """
    if mode not in ("test", "production") or not isinstance(catalog, dict):
        return False
    expected = catalog.get(offer)
    if not isinstance(expected, dict) or not isinstance(session, dict):
        return False
    amount = expected.get("amount")
    price_id = expected.get("price_id")
    currency = expected.get("currency")
    if type(amount) is not int or amount <= 0 or not isinstance(price_id, str) or not price_id.startswith("price_"):
        return False
    if not isinstance(currency, str) or len(currency) != 3 or currency != currency.lower():
        return False
    if (session.get("livemode") is not (mode == "production")
            or session.get("mode") != "payment"
            or session.get("status") != "complete"
            or session.get("payment_status") != "paid"
            or session.get("currency") != currency
            or type(session.get("amount_total")) is not int
            or session["amount_total"] != amount):
        return False
    items = session.get("line_items", {})
    if not isinstance(items, dict) or items.get("has_more") is not False:
        return False
    lines = items.get("data")
    if not isinstance(lines, list) or len(lines) != 1 or not isinstance(lines[0], dict):
        return False
    line = lines[0]
    price = line.get("price", {})
    return (type(line.get("quantity")) is int and line["quantity"] == 1
            and isinstance(price, dict) and price.get("id") == price_id
            and price.get("currency") == currency
            and type(price.get("unit_amount")) is int and price["unit_amount"] == amount
            and type(line.get("amount_total")) is int and line["amount_total"] == amount)


def configured_payment_matches(session, offer):
    try:
        catalog = json.loads(os.environ.get("STRIPE_PRICE_CATALOG", "{}"))
    except (TypeError, ValueError):
        return False
    return payment_matches(session, offer, catalog, os.environ.get("STRIPE_MODE", ""))
