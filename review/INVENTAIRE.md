# Inventaire des fichiers à auditer

Comparaison de la base commerciale `b6231d1` au développement `f2b1500` :
**52 fichiers concernés : 51 ajouts et un fichier modifié (`app.py`)**.
Les 70 autres fichiers historiques, dont les dépendances et ressources des
livrets, sont inchangés. Les ajouts incluent les fichiers du pack importé :
un ajout Git ne signifie pas une réécriture de la fonctionnalité.

Dans cette mission de transmission, aucun de ces 122 fichiers source n’a été
modifié. Le seul ajout est le dossier `review/` et ses pièces d’audit.
Le JSON associé fournit tailles et empreintes de chaque fichier ci-dessous.

| Statut Git | Fichier | Fonction |
| --- | --- | --- |
| A | `.dockerignore` | Limite le contexte des builds Docker aux outils de test. |
| A | `.gitignore` | Exclut caches, environnements locaux et configurations secrètes. |
| A | `README.md` | Installation, démarrage et commandes de validation locales. |
| M | `app.py` | Seules fonctions changées avant le gel : health et readiness ; aucun calcul, prompt ou générateur changé. |
| A | `demo.py` | Serveur de démonstration : profils, calculs/rendus réels et livraison simulée. |
| A | `demo_support.py` | Copie isolée du moteur, transport Claude/Brevo simulé, ressources PDF locales et mention de démo. |
| A | `docs/ARCHITECTURE_PREMIUM.md` | Proposition initiale de raccordement et de commercialisation ; complétée par la revue actuelle. |
| A | `docs/AUDIT_PREMIUM.md` | Audit des 17 fichiers du pack et des onze fichiers initiaux. |
| A | `docs/INTEGRATION.md` | Index du dossier de raccordement actualisé. |
| A | `docs/VALIDATION.md` | Rapport historique de la première démonstration. |
| A | `docs/VALIDATION_PREMIUM.md` | Résultats historiques des 40 tests et 13 assertions PHP ; limites commerciales. |
| A | `fixtures/demo_narrative.json` | Textes fictifs réservés aux démos/tests. |
| A | `fixtures/engine-preservation.json` | Empreintes de la base commerciale et comparaison syntaxique hors santé. |
| A | `hostinger/vivant/.htaccess` | En-têtes et restrictions Apache fournis dans le pack. |
| A | `hostinger/vivant/CGV_A_COMPLETER_AVANT_LANCEMENT.txt` | Checklist contractuelle à compléter ; document non final. |
| A | `hostinger/vivant/INSTALLATION_HOSTINGER.txt` | Notice historique renvoyant à la documentation commerciale du pack. |
| A | `hostinger/vivant/api/.htaccess` | Protection des fichiers PHP internes et du schéma SQL. |
| A | `hostinger/vivant/api/bootstrap.php` | Configuration privée, PDO, sessions/CSRF, révocation, chiffrement, SMTP, Stripe et droits existants. |
| A | `hostinger/vivant/api/index.php` | API comptes, sauvegarde, checkout, portail et webhooks ; transaction/déduplication locales. |
| A | `hostinger/vivant/api/payment-policy.php` | Politique pure d’activation test/live ; pas un appel Stripe. |
| A | `hostinger/vivant/api/schema.sql` | Schéma structurel de la base dédiée, sans données clients. |
| A | `hostinger/vivant/arbre-vivant.html` | Arbre interactif réutilisé, fiches, photos, import/export, dates vérifiées et démo séparée. |
| A | `hostinger/vivant/confidentialite.html` | Modèle de confidentialité du pack, à finaliser. |
| A | `hostinger/vivant/index.html` | Interface du pack et vue Mes livrets, consentement et sélection de profils. |
| A | `hostinger/vivant/logo-origin-officiel.png` | Logo officiel repris sans modification. |
| A | `hostinger/vivant/origin-commercial.js` | Interface des comptes, récupération, cloud, facturation et mode test. |
| A | `hostinger/vivant/origin-integration.js` | Dossier de livret minimal et reprise locale consentie, jamais preuve de paiement. |
| A | `hostinger/vivant/origin-storage.js` | Enveloppe carnet/arbre versionnée, restauration compatible et rollback local. |
| A | `hostinger/vivant/origin-vivant.css` | Charte noir/or/crème et styles responsive, ajouts ciblés. |
| A | `hostinger/vivant/origin-vivant.js` | Miroir, rituels, suivi, souvenirs et carnet du pack ; démo en lecture seule. |
| A | `pack-docs/CONFIGURATION_TEST.md` | Conditions de préproduction sans modification du site public. |
| A | `pack-docs/INSTALLATION_COMMERCIALE_V2.txt` | Notice officielle conservée, non autorisation de déployer. |
| A | `pack-docs/LISEZ_MOI_EN_PREMIER.txt` | Statut et limites officiels du pack. |
| A | `pack-docs/archive-manifest.json` | Empreintes des 17 entrées de l’archive officielle. |
| A | `pack-docs/config-exemple/origin-vivant-config.php.EXEMPLE` | Modèle de configuration avec champs vides/libellés ; aucun identifiant actif. |
| A | `pack-docs/local-delta.json` | Empreintes et neuf adaptations du pack, huit copies inchangées. |
| A | `pack-docs/migrations/002_session_version.sql` | Migration structurelle de test pour révoquer les anciennes sessions. |
| A | `pack-docs/prior-files-audit.json` | Empreintes avant/après des onze fichiers initiaux et de leur rapport. |
| A | `platform_demo.py` | Façade locale du front PHP et de la démo Python ; refuse une API distante. |
| A | `requirements-browser.txt` | Dépendances optionnelles des tests Playwright. |
| A | `requirements-demo.txt` | Dépendances de démo ; requirements.txt commercial inchangé. |
| A | `templates/demo.html` | Formulaire de démo, reprise ponctuelle des prénoms/dates et champs inconnus à compléter. |
| A | `templates/demo_result.html` | Liens vers les artefacts de démonstration. |
| A | `tests/browser/test_platform_browser.py` | Cinq parcours Chromium locaux, dont mobile et comptes PHP. |
| A | `tests/integration/test_vivant_api.py` | Cinq tests HTTP/PHP/MariaDB avec comptes et événements fictifs. |
| A | `tests/js/storage.test.cjs` | Quatre tests Node de snapshot/restauration locale. |
| A | `tests/php/policy.php` | Neuf assertions de paiement et quatre de chiffrement ; sentinelles exclusivement de test. |
| A | `tests/test_origin.py` | Dix-neuf tests du serveur, des adaptateurs et de la démonstration sans réseau réel. |
| A | `tests/test_platform.py` | Sept tests : façade, préservation et rendus supplémentaires avec sous-cas. |
| A | `tools/vivant/Dockerfile` | Image PHP 8.3 de test avec PDO MySQL, base officielle fixée par empreinte. |
| A | `tools/vivant/local_stack.py` | Stack jetable locale et génération de secrets éphémères hors racine web. |
| A | `tools/vivant/router.php` | Routeur PHP local, protège les sources et fichiers privés pendant les tests. |

Les modèles et schémas SQL sont du code/documentation sans valeurs actives ni
données clients. Les fixtures sont fictives ; les configurations exécutables
privées, volumes, bases et sorties de génération ne font pas partie de l’export.
