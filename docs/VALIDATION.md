# Validation locale — 22 octobre 2026

Environnement : Python 3.12.14, Flask 3.0.3, Gunicorn 22.0.0, WeasyPrint 70.0.

| Vérification exécutée | Résultat |
| --- | --- |
| Installation `requirements-demo.txt` avec les contraintes de la machine | Réussie, dépendances de production inchangées |
| `pip check` | Aucune dépendance incompatible |
| `python -m unittest discover -s tests -v` | **19 tests exécutés, 19 réussis**, réseau bloqué dans la suite |
| Serveur `app:app`, port local 5000, `/health` | HTTP 200 sans clés |
| Serveur `app:app`, `/ready` | HTTP 503 attendu : Anthropic, Brevo et EMAIL_DEST absents ; aucune disponibilité distante présumée |
| Serveur `demo:app`, port local 5050, `/health` et `/ready` | HTTP 200, mode demo explicitement annoncé |
| Génération Solo et Couple dans la suite | HTML et vrais PDF produits, deux réponses Claude simulées par livret, email intercepté |
| Formulaire de démonstration | Page de résultat HTTP 201, liens vers les artefacts |
| Requête HTTP réelle vers la démo Couple | HTTP 201, quatre artefacts récupérés en HTTP 200 |
| Extraction du PDF Couple avec `pdftotext` | 35 pages, mention DÉMONSTRATION et prénoms Camille/Alex présents |
| Contrôle des pièces jointes | Empreinte SHA-256 du PDF identique à celle de la boîte simulée |
| Diff du code existant | Seul le contrôle de santé de `app.py` est modifié ; fins de ligne CRLF conservées |

La suite vérifie aussi les limitations HTTP 429, les erreurs HTTP 503, les
timeouts Claude, les réponses tronquées ou sans JSON exploitable, le rejet Brevo
HTTP 401, les pièces jointes simples et bundle, les entrées invalides et les
destinations interdites. Les temporisations de reprise sont simulées.

Les sorties de la requête Couple sont conservées dans la machine courante sous :

```text
/tmp/origin-revolution-demo/63325e9f-c5de-4dd6-a4e7-b395f0a6d530/
  livret.html
  livret.pdf
  email.json
  manifest.json
```

Les processus locaux et ces sorties temporaires ne sont pas garantis dans une
nouvelle tâche. Les commandes de reprise figurent dans le README.

Non exécutés : appels Claude réels, livraison Brevo, Stripe, Google Sheets et
parcours des autres offres. La qualité d'une narration générée n'est pas établie
par des textes préécrits. Les sources d'ORIGIN VIVANT et du Miroir des Liens
restent nécessaires pour tester leur intégration réelle.

Aucun push, déploiement ou changement sur le site public n'a été effectué.
