"""Comportement actuel de POST /photos-racine (l'envoi Brevo est simulé)."""
import io
import json

from PIL import Image


def _jpeg(taille=(120, 120)):
    buf = io.BytesIO()
    Image.new("RGB", taille, (200, 160, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _brevo_simule(monkeypatch, b, ok=True):
    envois = []

    class R:
        pass

    def faux_post(url, headers=None, json=None, timeout=None):
        envois.append(json)
        r = R()
        r.ok = ok
        return r

    monkeypatch.setattr(b.module.requests, "post", faux_post)
    return envois


def _form(n=1, email="client@example.invalid", meta=None, nom="photo{}.jpg", contenu=None):
    data = {"email": email, "offre": "famille", "meta": json.dumps(meta or [])}
    for i in range(n):
        data[f"photo{i}"] = (io.BytesIO(contenu or _jpeg()), nom.format(i))
    return data


ENV = {"BREVO_SMTP_KEY": "cle-brevo-factice", "EMAIL_DEST": "dest@example.invalid"}


def test_refuse_si_le_mail_n_est_pas_configure(boot):
    b = boot()
    r = b.client.post("/photos-racine", data=_form(), content_type="multipart/form-data")
    assert r.status_code == 500


def test_refuse_sans_email_valide(boot):
    b = boot(ENV)
    r = b.client.post("/photos-racine", data=_form(email="pas-un-mail"), content_type="multipart/form-data")
    assert r.status_code == 400


def test_refuse_sans_photo(boot):
    b = boot(ENV)
    r = b.client.post("/photos-racine", data=_form(n=0), content_type="multipart/form-data")
    assert r.status_code == 400


def test_refuse_un_fichier_qui_n_est_pas_un_jpeg(boot, monkeypatch):
    b = boot(ENV)
    envois = _brevo_simule(monkeypatch, b)
    r = b.client.post("/photos-racine", data=_form(contenu=b"%PDF-1.4 pas une image"), content_type="multipart/form-data")
    assert r.status_code == 400 and envois == []


def test_envoie_les_photos_valides_par_mail(boot, monkeypatch):
    b = boot(ENV)
    envois = _brevo_simule(monkeypatch, b)
    r = b.client.post("/photos-racine", data=_form(n=3), content_type="multipart/form-data")
    assert r.status_code == 200 and r.get_json() == {"ok": True}
    assert len(envois) == 1 and len(envois[0]["attachment"]) == 3
    assert envois[0]["to"] == [{"email": "dest@example.invalid"}]


def test_plafonne_a_vingt_fichiers(boot, monkeypatch):
    b = boot(ENV)
    envois = _brevo_simule(monkeypatch, b)
    r = b.client.post("/photos-racine", data=_form(n=25), content_type="multipart/form-data")
    assert r.status_code == 200
    assert len(envois[0]["attachment"]) == 20


def test_nettoie_le_nom_de_fichier_et_echappe_le_html(boot, monkeypatch):
    b = boot(ENV)
    envois = _brevo_simule(monkeypatch, b)
    meta = [{"i": 1, "prenom": "<script>alert(1)</script>", "vivant": False, "deces": "<b>1990</b>"}]
    data = _form(meta=meta, nom="../../etc/<passwd>.jpg")
    r = b.client.post("/photos-racine", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    nom = envois[0]["attachment"][0]["name"]
    assert "<" not in nom and ">" not in nom and "/" not in nom
    html = envois[0]["htmlContent"]
    assert "<script>" not in html and "<b>1990</b>" not in html


def test_signale_une_panne_du_fournisseur_de_mail(boot, monkeypatch):
    b = boot(ENV)
    _brevo_simule(monkeypatch, b, ok=False)
    r = b.client.post("/photos-racine", data=_form(), content_type="multipart/form-data")
    assert r.status_code == 502
