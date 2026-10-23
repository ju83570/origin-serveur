# Aperçu web ORIGIN RÉVOLUTION

Cette démonstration de test est séparée du site public et de ses comptes.
Ouverture dans le navigateur :
[Aperçu web](https://stackblitz.com/github/ju83570/origin-serveur/tree/origin-preview-demo?view=preview&startScript=start).

StackBlitz importe la branche contenant uniquement les fichiers de la démo et
démarre le serveur statique dans le navigateur. Aucun package tiers à installer,
aucune clé API et aucun paiement. L’import et le démarrage automatique suivent
les paramètres documentés de StackBlitz (`dev`/`start`, `view=preview`).

Limite de vérification : le serveur Node et ses parcours sont testés localement
dans Chromium. Le proxy du cloud interdit `stackblitz.com`, donc l’ouverture
complète du service tiers n’a pas pu être vérifiée depuis cette machine. Le
navigateur du propriétaire utilise sa propre connexion. GitHub Pages n’a pas
été activé : l’API renvoie `Resource not accessible by integration` ; aucun site
Pages existant n’a été remplacé. Ne pas annoncer une URL GitHub Pages active.

Le bundle `web-preview/` est construit depuis les sources actuelles de
`hostinger/vivant/` par `tools/vivant/build_web_preview.py` ; les fonctions du
Miroir, de l’Arbre, du Carnet et de la Constellation sont réutilisées. Il n’inclut
aucune source Python/PHP, configuration privée ou base. Le petit serveur Node
sert uniquement une liste fermée de fichiers statiques. Aucune nouvelle
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

L’aperçu utilise uniquement le contenu de `web-preview/`, publié sur une
branche Git dédiée à ses fichiers statiques. Aucun CNAME, réglage DNS ou site
`origin-famille.fr` n’est modifié. `.nojekyll` évite de traiter le bundle comme
un site Ruby et `noindex` le marque comme démonstration non destinée aux recherches.

## Validation

Six tests navigateur réussis : quatre expériences disponibles, écriture et
persistance du Carnet, Arbre → Constellation → Miroir sans ressaisie, aucune
API/paiement/source serveur, réinitialisation limitée aux essais, largeurs
320/390/768/1440 px. L’ensemble est testé sous un préfixe `/origin-serveur/`,
comme un éventuel site de projet. Résultats dans `browser-tests.txt`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/vivant/build_web_preview.py
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python tests/browser/test_web_preview.py
```

`manifest.json` donne les empreintes des sources réutilisées et de chaque fichier
de l’aperçu. Les tests métier de l’issue #3 et les limites du moteur restent dans
`review/issue-3/` et `review/final-2026-10-23/`. Cet aperçu statique ne simule pas
une livraison de livret ou une connexion à un vrai compte.
