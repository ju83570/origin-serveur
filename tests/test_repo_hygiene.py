"""Garde-fou simple : aucun motif de clé ou de jeton connu dans les fichiers versionnés.

Complète (ne remplace pas) l'analyse de l'historique complet faite en CI par gitleaks.
"""
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

MOTIFS = [
    r"sk-ant-[A-Za-z0-9_-]{20,}",
    r"sk_live_[A-Za-z0-9]{10,}",
    r"rk_live_[A-Za-z0-9]{10,}",
    r"whsec_[A-Za-z0-9]{10,}",
    r"xkeysib-[A-Za-z0-9]{20,}",
    r"xsmtpsib-[A-Za-z0-9-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]
EXTENSIONS = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".toml", ".html", ".js", ".css", ".ini", ".cfg"}


def _fichiers_versionnes():
    try:
        sortie = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("pas de dépôt git disponible")
    return [ROOT / p for p in sortie.splitlines() if (ROOT / p).suffix.lower() in EXTENSIONS and (ROOT / p).is_file()]


def test_aucun_motif_de_secret_dans_les_fichiers_versionnes():
    trouves = []
    for chemin in _fichiers_versionnes():
        texte = chemin.read_text(encoding="utf-8", errors="ignore")
        for motif in MOTIFS:
            if re.search(motif, texte):
                trouves.append(f"{chemin.relative_to(ROOT)} (motif {motif.split('[')[0]}…)")
    assert not trouves, "Secret possible dans : " + ", ".join(trouves)


def test_gitignore_protege_les_secrets_et_les_donnees_clients():
    contenu = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for attendu in (".env", "*.pem", "*.key", "/clients/", "*_imprimable.pdf"):
        assert attendu in contenu
