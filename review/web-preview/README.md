# Aperçu web ORIGIN RÉVOLUTION

Cette démonstration de test est séparée du site public et de ses comptes.
URL prévue : https://ju83570.github.io/origin-serveur/

Le bundle `web-preview/` est construit depuis les sources actuelles de
`hostinger/vivant/` par `tools/vivant/build_web_preview.py` ; les fonctions du
Miroir, de l’Arbre, du Carnet et de la Constellation sont réutilisées. Il n’inclut
aucune source Python/PHP, configuration privée ou base. Aucune nouvelle
fonctionnalité n’est fusionnée dans `main` ou installée chez Hostinger.

## Périmètre de la démonstration

- Cinq adultes, liens familiaux, dates et récits entièrement fictifs et nommés
  « Démo ». Une page de Carnet et le Miroir sont préremplis pour commencer.
- Comptes, sauvegarde distante, paiement, API Claude/Brevo et livraison absents.
  Le script commercial n’est pas inclus ; aucun backend n’est servi.
- Politique CSP `connect-src 'none'` : aucune requête API du navigateur.
  Les liens au site public sont remplacés par des retours dans la démonstration.
- Stockage local réservé aux clés `origin_web_preview_*`, distinctes des clés de
  l’application. Rechargement, export/import et réinitialisation de la démo possibles.
  Ne saisir que des exemples inventés ; aucun chiffrement local n’est annoncé.
- Pas de pixel de suivi ni service tiers d’analyse. L’hébergeur statique reçoit
  les requêtes de pages/ressources, pas le contenu du Carnet ou de l’Arbre.

Le site de test utilise uniquement le contenu de `web-preview/`, publié sur une
branche Git dédiée à ses fichiers statiques. Aucun CNAME, réglage DNS ou site
`origin-famille.fr` n’est modifié. `.nojekyll` évite de traiter le bundle comme
un site Ruby et `noindex` le marque comme démonstration non destinée aux recherches.

## Validation

Six tests navigateur réussis : quatre expériences disponibles, écriture et
persistance du Carnet, Arbre → Constellation → Miroir sans ressaisie, aucune
API/paiement/source serveur, réinitialisation limitée aux essais, largeurs
320/390/768/1440 px. L’ensemble est testé sous un préfixe `/origin-serveur/`,
comme le site GitHub Pages. Résultats dans `browser-tests.txt`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/vivant/build_web_preview.py
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python tests/browser/test_web_preview.py
```

`manifest.json` donne les empreintes des sources réutilisées et de chaque fichier
de l’aperçu. Les tests métier de l’issue #3 et les limites du moteur restent dans
`review/issue-3/` et `review/final-2026-10-23/`. Cet aperçu statique ne simule pas
une livraison de livret ou une connexion à un vrai compte.
