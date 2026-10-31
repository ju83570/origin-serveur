"""Comportement actuel : /health, codes cadeau, accès administrateur."""
import re

from conftest import FAKE


def test_health_degrade_sans_configuration(boot):
    b = boot()
    r = b.client.get("/health")
    assert r.status_code == 503
    body = r.get_json()
    assert body["status"] == "degraded"
    assert set(body["missing"]) == {"ANTHROPIC_API_KEY", "BREVO_SMTP_KEY", "EMAIL_DEST"}


def test_health_ok_quand_tout_est_configure(boot):
    b = boot({"ANTHROPIC_API_KEY": "x", "BREVO_SMTP_KEY": "x", "EMAIL_DEST": "a@example.invalid"})
    r = b.client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["missing"] == []


def test_code_cadeau_aller_retour_pour_chaque_offre(boot):
    b = boot({"CODES_SECRET": FAKE["CODES_SECRET"]})
    m = b.module
    for offre in ("solo", "couple", "famille", "prestige", "naissance", "vocation", "bundle"):
        code = m.code_creer(offre)
        assert re.fullmatch(r"ORG-[A-Z]-[A-Z2-9]{6}-[A-Z2-9]{8}", code)
        ok, offre_lue, msg = m.code_verifier(code)
        assert (ok, offre_lue, msg) == (True, offre, "")


def test_code_modifie_ou_invalide_est_refuse(boot):
    b = boot({"CODES_SECRET": FAKE["CODES_SECRET"]})
    m = b.module
    code = m.code_creer("solo")
    corps, sig = code[:-8], code[-8:]
    falsifie = corps + ("AAAAAAAA" if sig != "AAAAAAAA" else "BBBBBBBB")
    for mauvais in (falsifie, "", "ORG-S-ABC", "ORG-Z-ABCDEF-GHJKMNPQ", None):
        ok, _, msg = m.code_verifier(mauvais)
        assert ok is False and msg == "Code inconnu."


def test_code_signe_avec_un_autre_secret_est_refuse(boot):
    b1 = boot({"CODES_SECRET": "premier-secret"})
    code = b1.module.code_creer("famille")
    b2 = boot({"CODES_SECRET": "second-secret"})
    assert b2.module.code_verifier(code)[0] is False


def test_code_utilise_ne_peut_plus_servir(boot):
    b = boot({"CODES_SECRET": FAKE["CODES_SECRET"]})
    m = b.module
    code = m.code_creer("solo")
    assert m._code_marquer(code, True) is True
    assert m._code_marquer(code, True) is False
    ok, offre, msg = m.code_verifier(code)
    assert (ok, offre, msg) == (False, "solo", "Ce code a déjà été utilisé.")


def test_code_check_http(boot):
    b = boot({"CODES_SECRET": FAKE["CODES_SECRET"], "OWNER_CODE": FAKE["OWNER_CODE"]})
    code = b.module.code_creer("couple")
    assert b.client.get(f"/code/check?code={code}").get_json() == {"valid": True, "offre": "couple", "message": ""}
    assert b.client.get("/code/check?code=nimporte").get_json()["valid"] is False
    proprio = b.client.get(f"/code/check?code={FAKE['OWNER_CODE']}").get_json()
    assert proprio == {"valid": True, "offre": "libre", "message": ""}


def test_admin_codes_refuse_sans_cle(boot):
    b = boot({"ADMIN_KEY": FAKE["ADMIN_KEY"]})
    assert b.client.get("/admin/codes").status_code == 403
    assert b.client.get("/admin/codes?key=mauvaise").status_code == 403


def test_admin_codes_refuse_si_cle_admin_non_definie(boot):
    b = boot()
    assert b.client.get("/admin/codes?key=").status_code == 403


def test_admin_codes_genere_des_codes_valides(boot):
    b = boot({"ADMIN_KEY": FAKE["ADMIN_KEY"], "CODES_SECRET": FAKE["CODES_SECRET"]})
    r = b.client.get(f"/admin/codes?key={FAKE['ADMIN_KEY']}&offre=solo&n=2")
    assert r.status_code == 200
    codes = re.findall(r"ORG-S-[A-Z2-9]{6}-[A-Z2-9]{8}", r.get_data(as_text=True))
    assert len(set(codes)) == 2
    assert all(b.module.code_verifier(c)[0] for c in set(codes))
