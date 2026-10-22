# Résultats exécutés — intégration premium

22 octobre 2026, branche `feat/origin-vivant-integration-test`.
Environnement local : Python 3.12, WeasyPrint 70, Chromium système, PHP 8.3.36,
PDO MySQL et MariaDB 11.4. Aucun service du site public n'a été sollicité.

## Résultats finaux

| Suite ou contrôle | Résultat exécuté |
| --- | --- |
| `python -m unittest discover -s tests -v` | **26 tests réussis**, aucun échec, aucun ignoré |
| `node --test tests/js/storage.test.cjs` | **4 tests réussis**, aucun échec |
| `docker exec origin-vivant-api-test php /tests/policy.php` | **13 vérifications réussies**, sans appel Stripe |
| `python tests/integration/test_vivant_api.py` | **5 tests HTTP/PHP/MariaDB réussis** |
| `python tests/browser/test_platform_browser.py` | **5 tests Chromium réussis**, requêtes hors origine locale interdites |
| Syntaxe PHP | Les trois fichiers de l'API adaptés passent `php -l` |
| Syntaxe JavaScript | Scripts nouveaux/adaptés et script intégré de l'arbre acceptés par Node |
| `pip check` | Aucune incompatibilité détectée |
| Diff Git | Fins de ligne historiques préservées ; contrôle avec `core.whitespace=cr-at-eol` |
| Recréation de la stack | Arrêt/suppression des seules ressources de test, nouvelle base et nouvelle configuration aléatoire ; suites API et navigateur repassées |

Soit **40 tests automatisés réussis**, plus les 13 vérifications PHP distinctes.
Aucun échec final inexpliqué. Les tests ne sont pas remplacés par des checks de
syntaxe : les services et rendus sont effectivement exécutés.

## Comportements vérifiés

- Les calculs, constantes, prompts et traitements Python sont identiques à la
  base commerciale hors fonctions de santé ; les 70 fichiers historiques restants
  sont identiques octet pour octet.
- Solo/Couple : profils, dispatch narratif à réponses simulées, validations,
  HTML/PDF et message avec pièces jointes. Famille, Prestige, Naissance et Vocation :
  validation de narratifs fixtures et rendus HTML/PDF personnalisés réels.
- Claude : réponses, JSON invalide, troncature, limitation, timeout et reprises
  testés sans connexions sortantes. Brevo : construction des pièces jointes,
  bundle et rejet d'envoi simulés. Ces tests n'envoient aucun email.
- PHP/MySQL : connexion avec un compte de test, cookies Secure/HttpOnly, CSRF,
  sauvegarde chiffrée, restitution des objets JSON, refus d'un accès anonyme,
  limite de taille et rejet d'une sauvegarde altérée.
- Récupération : consommation d'un jeton de test, second usage rejeté et ancienne
  session invalidée. L'email qui apporte normalement ce jeton n'a pas été envoyé.
- Stripe : garde-fous test/live, checkout désactivé sans configuration, signature,
  horodatage et mode du webhook, doublon, transaction annulée sur échec et rejeu
  ensuite possible. Les événements sont des fixtures de test signées localement.
- Navigateur : Miroir personnel sans inventer la réponse du proche, texte injecté
  affiché sans exécution, carnet, bilan, export, arbre personnel et reprise
  consentie vers une génération de livret de démonstration.
- Compte dans Chromium : connexion, sauvegarde volontaire du carnet et de l'arbre,
  restauration et déconnexion sur la vraie API PHP locale.
- Mobile : six vues parcourues aux largeurs **320, 390, 768 et 1440 px**, sans
  débordement horizontal de la page. Cela ne garantit pas tous les appareils,
  lecteurs d'écran ou navigateurs ; ces essais restent à compléter.

Les comptes de test sont créés dans la base jetable avec une adresse fictive,
un mot de passe aléatoire et une vérification d'email préparée par la fixture.
Cela valide les sessions et données, pas l'inscription avec délivrance SMTP.

## Échecs rencontrés et résolus

- Le port initial 5060 est refusé par Chromium : façade déplacée au port 5080.
- L'API PHP placée uniquement sur un réseau Docker interne n'exposait pas le port
  attendu : réseau frontal distinct, publication **127.0.0.1** et base privée.
- La sauvegarde PHP transformait `{}` en `[]` : type JSON désormais préservé.
- Chargement redondant de la politique PHP pendant un test : `require_once`.

Les suites affectées ont été relancées après correction. Ces échecs ne sont pas
présentés comme des validations réussies du pack initial.

## Non exécuté et limites commerciales

Pas de paiement Stripe distant, de test du portail réel ou de cycle complet
d'abonnement ; pas d'email SMTP, Brevo ou de génération Claude réels. Aucune
installation Hostinger, validation Apache/.htaccess/TLS distante, mesure de charge
ou revue de sécurité indépendante. Aucun merge, push, déploiement ou changement
sur `origin-famille.fr`.

Les illustrations féminines optionnelles absentes sur Solo/Naissance/Vocation
utilisent leurs replis existants. Ce constat historique n'a pas été corrigé par
un remplacement d'asset. Aucune autre régression détectée dans le périmètre testé.

Le circuit commande payée → travail Python durable → validation → livraison et
les services familiaux inter-comptes restent à développer et vérifier. Le projet
est une intégration de test fonctionnelle, pas une version déclarée prête à vendre.

## Artefacts locaux

Captures : `/tmp/origin-vivant-screenshots/mobile-premium.png`.
Les HTML/PDF de démonstration restent sous `/tmp/origin-revolution-demo/`.
Les journaux de suites sont sous `/tmp/origin-all-tests.log`,
`/tmp/origin-api-tests.log` et `/tmp/origin-browser-tests.log`.
Ces sorties sont temporaires et ne remplacent pas un stockage client.

Les commandes reproductibles et l'arrêt de la stack figurent dans le README.
