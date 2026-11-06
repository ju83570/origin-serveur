"""Critères d'acceptation de la mission #13, écrits AVANT les correctifs.

Chaque test ci-dessous décrit le comportement SOUHAITÉ et échoue aujourd'hui : il est marqué
`xfail(strict=True)`. Quand la PR J corrigera le défaut, le test passera, la CI le signalera
(« XPASS strict ») et il suffira de retirer le marqueur : la protection devient définitive.

Ces tests ne prouvent PAS que la production est touchée : ils décrivent le code. La configuration
réelle de Render (variables, disque, nombre de processus) reste à confirmer.
La façon exacte de « persister » (base, disque, autre) sera décidée dans la PR J : adapter alors
l'étape de redémarrage simulé de ces tests, pas leur exigence.
"""
import pytest

from conftest import FAKE

SESSION = "cs_test_" + "k9L8m7N6o5P4q3R2s1T0"
ENV_VENTES = {
    "CODES_SECRET": FAKE["CODES_SECRET"],
    "STRIPE_KEY": FAKE["STRIPE_KEY"],
    "ENFORCE_ACCESS": "1",
}


def _paiement_ok(monkeypatch, b):
    class R:
        status_code = 200

        def json(self):
            return {"payment_status": "paid"}

    monkeypatch.setattr(b.module.requests, "get", lambda *a, **k: R())


@pytest.mark.xfail(strict=True, reason="#13 : les codes utilisés sont dans /tmp (disque éphémère sur Render)")
def test_code_cadeau_utilise_reste_utilise_apres_redemarrage(boot):
    b1 = boot(ENV_VENTES)
    code = b1.module.code_creer("solo")
    assert b1.post_webhook(code_cadeau=code).status_code == 200
    b2 = boot(ENV_VENTES)  # nouveau démarrage, disque neuf
    assert b2.post_webhook(code_cadeau=code).status_code == 403


@pytest.mark.xfail(strict=True, reason="#13 : les usages d'un paiement sont en mémoire seulement")
def test_plafond_d_usage_d_un_paiement_survit_au_redemarrage(boot, monkeypatch):
    b1 = boot(ENV_VENTES)
    _paiement_ok(monkeypatch, b1)
    assert [b1.post_webhook(stripe_session=SESSION).status_code for _ in range(3)] == [200, 200, 200]
    b2 = boot(ENV_VENTES)
    _paiement_ok(monkeypatch, b2)
    assert b2.post_webhook(stripe_session=SESSION).status_code == 403


@pytest.mark.xfail(strict=True, reason="#13 : une même requête rejouée relance une génération payante")
def test_meme_requete_rejouee_ne_lance_qu_une_generation(boot, monkeypatch):
    b = boot(ENV_VENTES)
    _paiement_ok(monkeypatch, b)
    for _ in range(2):
        b.post_webhook(stripe_session=SESSION)
    assert len(b.launched) == 1


@pytest.mark.xfail(strict=True, reason="#13 : repli sur une valeur par défaut si aucun secret n'est défini")
def test_aucun_secret_par_defaut_previsible_pour_signer_les_codes(boot):
    b = boot()  # aucune variable : CODES_SECRET, WEBHOOK_SECRET et clé Anthropic absents
    assert b.module._CODES_SECRET not in (b"origin", b"")


@pytest.mark.xfail(strict=True, reason="#13 : pas de plafond de taille de requête sur /webhook")
def test_corps_de_requete_demesure_refuse_avant_traitement(boot):
    b = boot(ENV_VENTES)
    enorme = "x" * 30_000_000
    r = b.client.post("/webhook", json={"offre": "solo", "email": "client@example.invalid", "texte_libre": enorme})
    assert r.status_code == 413


@pytest.mark.xfail(strict=True, reason="#13 : /admin/codes accepte la clé dans l'adresse (journaux, historique)")
def test_cle_admin_refusee_dans_l_adresse(boot):
    b = boot({"ADMIN_KEY": FAKE["ADMIN_KEY"]})
    r = b.client.get(f"/admin/codes?key={FAKE['ADMIN_KEY']}&offre=solo")
    assert r.status_code in (400, 403, 405)
