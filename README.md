# ORIGIN RÉVOLUTION — serveur et démonstration locale

## Correctifs après audit Claude

Le dossier courant commence dans
[review/audit-followup/LIRE_EN_PREMIER.md](review/audit-followup/LIRE_EN_PREMIER.md).
Il détaille les correctifs de sécurité, les tests, les limites et la migration
proposée. Aucune fusion ni mise en production n'est réalisée.

Une démonstration transportable est fournie dans `demo-visual/` : Miroir,
parcours gratuit, préparation consentie du dossier Premium et exemples PDF
Solo/Couple fictifs. Voir `demo-visual/LIRE_AVANT.txt`. Aucun compte, paiement
ou envoi réel dans cette page autonome.

Le moteur existant reste dans `app.py`. La démonstration utilise un point d'entrée
distinct, `demo:app`, sans clé API, sans requête externe et sans envoi d'email.
Aucun changement sur `origin-famille.fr` n'est nécessaire.

## Installation

Python 3.12 et les bibliothèques système Pango/HarfBuzz sont disponibles dans
l'environnement cloud préparé. Depuis le dépôt :

```bash
python3 -m venv /workspace/.venvs/origin-serveur
export XDG_CACHE_HOME=/workspace/.cache
export PIP_CACHE_DIR=/workspace/.cache/pip
mkdir -p "$XDG_CACHE_HOME"
/workspace/.venvs/origin-serveur/bin/pip install -r requirements-demo.txt
/workspace/.venvs/origin-serveur/bin/pip check
```

La démonstration fixe WeasyPrint à 70.0 pour son API de filtrage des ressources.
Les dépendances de production dans `requirements.txt` restent inchangées.
Dans la machine préparée, les versions installées sont également conservées
dans `/workspace/.setup/origin-serveur/constraints.txt` ; ajouter
`-c /workspace/.setup/origin-serveur/constraints.txt` à l'installation permet de
les réutiliser. Ce fichier local ne remplace pas un verrou de dépendances du dépôt.

## Démarrer la démonstration

Depuis le checkout existant `/workspace/origin-serveur` :

```bash
export XDG_CACHE_HOME=/workspace/.cache
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$XDG_CACHE_HOME"
/workspace/.venvs/origin-serveur/bin/python demo.py
```

Le serveur écoute uniquement sur l'interface locale, port 5050. Pour une session
Gunicorn locale persistante :

```bash
/workspace/.venvs/origin-serveur/bin/gunicorn \
  --bind 127.0.0.1:5050 --workers 1 --timeout 300 demo:app
```

L'interface à la racine propose Solo ou Couple, des profils fictifs préremplis et
huit villes disponibles hors ligne. Elle produit des liens locaux vers le HTML,
le PDF et le message simulé. Ces liens sont destinés à la machine locale ; l'UI
d'onboarding cloud ne fournit pas de prévisualisation web localhost.

Un contrôle fonctionnel peut également se faire par une requête locale :

```bash
curl --fail-with-body -sS http://127.0.0.1:5050/demo/generate \
  -H 'Content-Type: application/json' \
  --data '{"offre":"solo","clients":[{"prenom":"Camille","date_naissance":"1990-05-12","genre":"Femme","ville":"paris"}]}'
```

La réponse HTTP 201 contient les chemins des artefacts et `delivered: false`.
Les sorties se trouvent dans `/tmp/origin-revolution-demo/<uuid>/` ; le répertoire
peut être choisi avec `ORIGIN_DEMO_OUTPUT_DIR`. Elles sont temporaires et ne sont
pas un stockage client. Utiliser des profils fictifs. Le message JSON contient
les noms, tailles et empreintes des pièces jointes, sans identifiants API.

### Ce qui est réel et ce qui est simulé

| Élément | Comportement de la démo |
| --- | --- |
| Validation des entrées | Dates, noms, genre et villes contrôlés avant génération |
| Profils et calculs | `fmt_profil`, PyEphem et timezonefinder existants |
| Claude | Dispatch Solo/Couple et assemblage de deux réponses réels ; transport remplacé par `SimulatedServices` et texte préécrit |
| Validation narrative | `_valider_narratif_client` conservé, avec les valeurs calculées requises dans les notes |
| HTML et PDF | Générateurs existants, images locales, mention DÉMONSTRATION, polices locales de secours |
| Brevo | Construction réelle des pièces jointes ; requête interceptée en mémoire, boîte locale, aucun email livré |
| Réseau | Aucun appel HTTP sortant ; villes restreintes, ressources PDF limitées aux données embarquées et à `static/` |
| Enrichissement et qualité par IA | Non exécutés dans la démo ; les textes ne démontrent pas la qualité d'une génération Claude réelle |
| Stripe, Google Sheets, codes cadeaux | Non exposés par le serveur de démonstration |

`app:app` n'importe aucun module de simulation. Les remplacements sont effectués
sur une copie isolée du moteur pour chaque génération. Il n'existe pas de bascule
automatique en simulation lorsqu'une clé manque, ni de fausse clé enregistrée.

## Santé du serveur de production

| Route | Réponse | Signification |
| --- | --- | --- |
| `GET /health` | 200, `status: ok` | Flask répond ; aucun service externe nécessaire |
| `GET /ready` | 503, `status: degraded`, `missing` | Configuration externe incomplète |
| `GET /ready` | 200, `status: configured` | Les trois paramètres sont présents ; leur validité distante n'est pas testée |

`external_services_checked: false` rappelle que `/ready` n'appelle pas les API.
Un contrôle de supervision qui doit vérifier la configuration externe doit
maintenant utiliser `/ready`. Le serveur de démo annonce explicitement `mode: demo`
et des services simulés sur ses propres routes de santé.

Le point d'entrée de production reste `app:app` et son webhook est conservé.
Le webhook confirme le lancement d'un thread, pas la livraison du livret.
Ne pas interpréter son HTTP 200 comme une preuve de génération terminée.

## Tests sans clés

```bash
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests -v
```

La suite bloque les connexions socket, les résolutions DNS et les requêtes HTTP
réelles. Elle couvre la santé, la validation du webhook, la construction des
messages Claude, les réponses invalides/tronquées, les reprises après limitation,
les erreurs et timeouts, les pièces jointes Brevo et le rejet d'un envoi. Les
parcours Solo/Couple rendent de vrais HTML/PDF et vérifient leurs artefacts ainsi
que les empreintes des pièces jointes simulées.

Les tests complémentaires vérifient désormais les rendus des offres Famille,
Prestige, Naissance et Vocation avec des fixtures. Le parcours Stripe distant et
la qualité éditoriale des modèles restent à valider avec des accès de test.
Les résultats exécutés et les limites sont consignés dans le
[rapport de validation](docs/VALIDATION.md).

## Intégration dans l'écosystème

Le pack officiel est maintenant importé dans `hostinger/vivant/`. Son Miroir,
son arbre, son carnet, son parcours et ses comptes sont réutilisés.
Voir [l'audit complet](docs/AUDIT_PREMIUM.md),
[l'architecture et les accès nécessaires](docs/ARCHITECTURE_PREMIUM.md) et
[les résultats exécutés](docs/VALIDATION_PREMIUM.md).

La façade de test conserve le même domaine local pour le pack PHP et la démo
Python, afin de permettre un passage consenti des profils vers les livrets :

```bash
cd /workspace/origin-serveur
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python platform_demo.py
```

Elle écoute sur le port **5080**, uniquement en local. Le Miroir, l'arbre, le
carnet et le passage au livret de démonstration fonctionnent sans PHP configuré.
La façade refuse les adresses d'API externes et ne se connecte jamais au site
public. Les sources de ce dernier restent hors de ce dépôt.

### Espace client PHP/MySQL de test, facultatif

Docker est nécessaire pour ces seuls tests locaux. La base est dédiée et jetable,
sans port exposé. L'API PHP est liée au port local 8090. La configuration et ses
secrets aléatoires sont créés hors racine web sous `/tmp/origin-vivant-test/`.
Ne jamais utiliser cette stack pour des données de clients réels.

```bash
DOCKER_CONFIG=/workspace/.cache/docker docker build \
  -t origin-vivant-php-test -f tools/vivant/Dockerfile .
python3 tools/vivant/local_stack.py start
```

Puis lancer la façade avec l'API locale :

```bash
ORIGIN_VIVANT_API_URL=http://127.0.0.1:8090/vivant/api/ \
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python platform_demo.py
```

Les conteneurs sont des outils de développement. Sur Hostinger, utiliser le
PHP natif, une base dédiée et une configuration privée : voir
[la configuration de préproduction](pack-docs/CONFIGURATION_TEST.md).

### Suites complémentaires

```bash
node --test tests/js/storage.test.cjs
docker exec origin-vivant-api-test php /tests/policy.php
/workspace/.venvs/origin-serveur/bin/python tests/integration/test_vivant_api.py
```

Pour les tests navigateur, installer `requirements-browser.txt`. Les commandes
ci-dessous utilisent Chromium système (`/usr/bin/chromium`), présent dans cette
machine. La façade et la stack PHP de test doivent être démarrées.

```bash
/workspace/.venvs/origin-serveur/bin/pip install -r requirements-browser.txt
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python tests/browser/test_platform_browser.py
```

Les tests de comptes utilisent des utilisateurs fictifs vérifiés dans la base
locale : ils ne remplacent pas un test de délivrance SMTP. Stripe reste déconnecté.
Pour arrêter et supprimer uniquement cette stack jetable :

```bash
python3 tools/vivant/local_stack.py stop
```

La branche `feat/origin-vivant-integration-test` contient les modifications de
travail, sans merge, push ni déploiement.
