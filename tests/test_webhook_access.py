"""Comportement actuel du contrôle d'accès de /webhook (aucune génération n'est exécutée : le thread est simulé)."""
import pytest

from conftest import FAKE

SESSION = "cs_test_" + "a1B2c3D4e5F6g7H8i9J0"


def _stripe_reponse(monkeypatch, boot_obj, payment_status="paid", status=200):
    class R:
        status_code = status

        def json(self):
            return {"payment_status": payment_status}

    appels = []

    def faux_get(url, headers=None, timeout=None):
        appels.append(url)
        return R()

    monkeypatch.setattr(boot_obj.module.requests, "get", faux_get)
    return appels


def test_acces_ferme_sans_code_ni_paiement(boot):
    b = boot({"ENFORCE_ACCESS": "1"})
    r = b.post_webhook()
    assert r.status_code == 403
    assert b.launched == []


def test_email_invalide_refuse(boot):
    b = boot({"OWNER_CODE": FAKE["OWNER_CODE"]})
    r = b.post_webhook(code_cadeau=FAKE["OWNER_CODE"], email="pas-un-email")
    assert r.status_code == 400
    assert b.launched == []


def test_code_inconnu_refuse(boot):
    b = boot({"CODES_SECRET": FAKE["CODES_SECRET"]})
    r = b.post_webhook(code_cadeau="ORG-S-AAAAAA-BBBBBBBB")
    assert r.status_code == 403 and b.launched == []


def test_code_cadeau_accepte_une_fois_puis_refuse(boot):
    b = boot({"CODES_SECRET": FAKE["CODES_SECRET"]})
    code = b.module.code_creer("solo")
    assert b.post_webhook(code_cadeau=code).status_code == 200
    assert len(b.launched) == 1
    r2 = b.post_webhook(code_cadeau=code)
    assert r2.status_code == 403
    assert len(b.launched) == 1


def test_code_proprietaire_acces_libre_et_illimite(boot):
    b = boot({"OWNER_CODE": FAKE["OWNER_CODE"], "ENFORCE_ACCESS": "1"})
    for _ in range(3):
        assert b.post_webhook(code_cadeau=FAKE["OWNER_CODE"]).status_code == 200
    assert len(b.launched) == 3


def test_paiement_stripe_valide_ouvre_trois_envois_maximum(boot, monkeypatch):
    b = boot({"STRIPE_KEY": FAKE["STRIPE_KEY"], "ENFORCE_ACCESS": "1"})
    _stripe_reponse(monkeypatch, b)
    codes = [b.post_webhook(stripe_session=SESSION).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 403]
    assert len(b.launched) == 3


def test_paiement_non_confirme_refuse(boot, monkeypatch):
    b = boot({"STRIPE_KEY": FAKE["STRIPE_KEY"], "ENFORCE_ACCESS": "1"})
    _stripe_reponse(monkeypatch, b, payment_status="unpaid")
    assert b.post_webhook(stripe_session=SESSION).status_code == 403
    assert b.launched == []


def test_identifiant_de_session_mal_forme_refuse_sans_appel_stripe(boot, monkeypatch):
    b = boot({"STRIPE_KEY": FAKE["STRIPE_KEY"], "ENFORCE_ACCESS": "1"})
    appels = _stripe_reponse(monkeypatch, b)
    assert b.post_webhook(stripe_session="pas_une_session").status_code == 403
    assert appels == []


def test_stripe_indisponible_refuse_proprement(boot, monkeypatch):
    b = boot({"STRIPE_KEY": FAKE["STRIPE_KEY"], "ENFORCE_ACCESS": "1"})

    def panne(*a, **k):
        raise OSError("réseau coupé")

    monkeypatch.setattr(b.module.requests, "get", panne)
    r = b.post_webhook(stripe_session=SESSION)
    assert r.status_code == 403 and b.launched == []


def test_secret_webhook_exige_quand_il_est_defini(boot):
    b = boot({"WEBHOOK_SECRET": FAKE["WEBHOOK_SECRET"], "OWNER_CODE": FAKE["OWNER_CODE"]})
    assert b.post_webhook(code_cadeau=FAKE["OWNER_CODE"]).status_code == 401
    mauvais = {"X-ORIGIN-SECRET": "faux"}
    assert b.post_webhook(code_cadeau=FAKE["OWNER_CODE"], headers=mauvais).status_code == 401
    bon = {"X-ORIGIN-SECRET": FAKE["WEBHOOK_SECRET"]}
    assert b.post_webhook(code_cadeau=FAKE["OWNER_CODE"], headers=bon).status_code == 200


def test_caracterisation_sans_enforce_access_ni_stripe_le_webhook_est_ouvert(boot):
    """CONSTAT, pas une approbation : sans ENFORCE_ACCESS ni STRIPE_KEY, aucun contrôle d'accès n'est appliqué.

    La production est protégée seulement si ENFORCE_ACCESS=1 y est bien défini (à confirmer, mission #13).
    Si ce test échoue après une modification, c'est probablement une amélioration : mettre le test à jour.
    """
    b = boot()
    assert b.post_webhook().status_code == 200
    assert len(b.launched) == 1


def test_les_requetes_refusees_ne_lancent_aucune_generation(boot):
    b = boot({"ENFORCE_ACCESS": "1"})
    for _ in range(5):
        b.post_webhook()
        b.post_webhook(code_cadeau="ORG-S-AAAAAA-BBBBBBBB")
    assert b.launched == []


@pytest.mark.parametrize("vide", [{}, {"email": ""}])
def test_corps_incomplet_ne_plante_pas(boot, vide):
    b = boot({"OWNER_CODE": FAKE["OWNER_CODE"]})
    r = b.client.post("/webhook", json={"code_cadeau": FAKE["OWNER_CODE"], **vide})
    assert r.status_code in (400, 500)
    assert b.launched == []
