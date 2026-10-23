# Validation exécutée le 23 octobre 2026

Les preuves normalisées dans `evidence/` donnent les noms et résultats des tests,
sans journaux d'exécution client ni valeur de secret. Environnement : Python 3.12,
PHP 8.3, MariaDB 11.4/InnoDB dans Docker isolé, Chromium/Playwright, Node local.

| Suite | Développé | Testé automatiquement | Contrôle ponctuel par commande | Non testé | Déployé |
| --- | --- | --- | --- | --- | --- |
| Moteur Python, démo, préservation | Oui | **38/38** ; AST, 70 ressources, sécurité, adaptateurs Claude/Brevo, vrais PDF, façade avec réseau serveur interdit | Diff minimal `app.py` | Vrais modèles et délivrance Brevo | Non |
| API PHP/MySQL et migration | Oui | **40/40** : 39 cas API/services + 1 migration existante | Schéma complet sur base vide, 20 tables | Base réelle Hostinger, historiques clients | Non |
| Navigateur | Existant conservé | **10/10** : mobile, Miroir, arbre, sauvegardes, passage Premium et démo portable | Aucune recette visuelle humaine indépendante dans cette phase | Appareils physiques, navigateur réel du propriétaire | Non |
| Stockage JavaScript | Existant conservé | **10/10** | — | Quotas d'un navigateur client réel | Non |
| Politique PHP/crypto | Oui | **42/42 assertions**, pas 42 parcours complets | Sodium/PDO/curl/mbstring présents | Gestion des clés chez l'hébergeur | Non |
| Syntaxe PHP | Oui | 11 fichiers sans erreur (`php -l`, API + CLI) | — | Apache réel et chemins Hostinger | Non |
| Worker privé | Oui | Baux, crash, retry, concurrence et transaction couverts dans les tests API | `--status`, `--retry` inconnu avec HTTPS requis : OK dans le conteneur de test | Cron distant, vraies lectures Stripe | Non |
| Dépendances Python | Conservées | `pip check` : aucune incompatibilité | — | Image Python de production | Non |

**Total : 98 cas de test, 98 réussis, aucun échec/skip final ; 42 assertions PHP
supplémentaires.** Les sous-cas d'un test ne sont pas ajoutés au total. Les
11 vérifications de syntaxe et les contrôles ponctuels ne sont pas comptés comme
des parcours supplémentaires. Les anciens chiffres « 40 tests et 13 fichiers PHP »
appartenaient à la première intégration ; les dossiers historiques sont conservés
sans leur attribuer une portée nouvelle. Ce total n'établit pas une absence de
tout défaut possible ni une recette indépendante par Claude.

## Reproduction

Dans un environnement jetable sans clés ni clients, suivre d'abord le README
pour installer les dépendances, démarrer la stack Docker et la façade locale.
Les tests API suppriment leurs seules données fictives et ne doivent jamais
pointer vers une base commerciale. Le test de migration crée un nom de base
aléatoire dédié puis le supprime, après vérification du label Docker `test`.

```bash
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests/integration -v
node --test tests/js/storage.test.cjs
docker exec origin-vivant-api-test php /tests/policy.php
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests/browser -v
/workspace/.venvs/origin-serveur/bin/python -m pip check
```

Les chemins absolus sont ceux de la machine cloud ; les adapter après extraction.
Le test de concurrence Checkout utilise deux processus PHP CLI et une réponse
Stripe fictive ralentie : il vérifie le contrat serveur/SQL, pas la fiabilité du
réseau Stripe. Le test de concurrence worker utilise aussi deux processus réels.
Les sauvegardes concurrentes utilisent le serveur local et des onglets simulés,
sans test de charge ou de panne de disque.

La génération Solo/Couple à travers la façade est désormais exécutée avec
interdiction effective des sockets, DNS et HTTP côté serveur. Les tests
navigateur interdisent aussi le réseau navigateur externe. Aucun appel Claude,
Brevo ou Stripe réel et aucun email livré dans ces suites.

## Échecs rencontrés et traitement

- Une erreur de quoting SQL PHP pendant l'implémentation a été détectée par la
  validation locale puis corrigée avant les exécutions finales.
- Une première exécution navigateur a eu un échec d'import : un worker Gunicorn
  local avait gardé en mémoire l'ancienne version de `premium_security`. Son
  rechargement local a rétabli l'import. La suite complète a ensuite passé 10/10.
  Toute future mise à jour du service devra redémarrer ses workers après accord.
- Le bootstrap HTTPS bloquait le worker CLI : condition limitée aux requêtes
  web, HTTPS conservé pour HTTP. Le vrai script CLI a été testé avec
  `https_required=true` sans exposer sa configuration.

Aucun échec ne reste dans les dernières suites. Les traces de certaines images
Naissance/Vocation absentes apparaissent toujours lors des rendus : ce sont des
ressources déjà absentes de la base, avec repli du moteur conservé. Les empreintes
historiques et les tests ne détectent aucune nouvelle régression ; la qualité
éditoriale et graphique de vrais livrets commerciaux n'est pas validée par les
narratives fictives des tests.

## Contrôles distants encore nécessaires

Stripe TEST : signature réelle, API/version, conflits d'idempotence, Checkout,
paiements différés, factures et litiges ; SMTP et reset/confirmation réels ; TLS,
cookies, CSP et refus d'accès aux sources privées sur Hostinger ; sauvegarde et
restauration de la base/chiffrement ; consommation durable et crash de génération
Python ; état Brevo incertain sans double envoi. Aucune de ces recettes n'est
présentée comme effectuée. Aucun test de pénétration externe n'a été conduit.
