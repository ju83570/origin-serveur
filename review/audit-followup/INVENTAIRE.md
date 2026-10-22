# Inventaire des changements depuis la revue 32d6b68

Les fichiers existants sont conservés ; aucun calcul, prompt ou rendu Premium supprimé.
Les documents de revue initiaux sont historiques et renvoient au nouveau dossier.
Cet inventaire exclut ses deux propres fichiers, ajoutés avec lui.

| Statut | Fichier | Fonction |
| --- | --- | --- |
| M | `README.md` | Documentation de revue, preuves, limites ou inventaire. |
| M | `app.py` | Contrôles d’accès Premium uniquement : paiement, webhook et codes cadeaux. |
| A | `demo-visual/LIRE_AVANT.txt` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/apercu-premium-mobile.png` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/arbre-vivant.html` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/confidentialite.html` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/couple-demonstration.html` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/couple-demonstration.pdf` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/index.html` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/solo-demonstration.html` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `demo-visual/solo-demonstration.pdf` | Démonstration transportable ; contenu/personnes fictifs, aucun paiement réel. |
| A | `fixtures/security-engine-preservation.json` | Preuve de préservation calculée avant modification des contrôles de sécurité. |
| A | `hostinger/vivant/api/backups.php` | Sauvegardes révisionnées, historique et lecture sans abonnement. |
| M | `hostinger/vivant/api/bootstrap.php` | Chiffrement, sessions, transport Stripe, débit et droits canoniques. |
| A | `hostinger/vivant/api/checkout.php` | Commande UUID, prix serveur, Checkout idempotent et reprise. |
| M | `hostinger/vivant/api/index.php` | Routes sécurisées, export/récupération et suppression réauthentifiée. |
| M | `hostinger/vivant/api/schema.sql` | Schéma vierge avec commandes, historique et compteurs. |
| A | `hostinger/vivant/api/security-policy.php` | Politiques pures de proxy, produit, sauvegarde et paiement. |
| A | `hostinger/vivant/api/stripe-events.php` | Inbox Stripe, validation de commande et réconciliation des droits. |
| M | `hostinger/vivant/arbre-vivant.html` | Interface existante : sauvegarde locale, reprise, démo et parcours consenti. |
| M | `hostinger/vivant/index.html` | Interface existante : sauvegarde locale, reprise, démo et parcours consenti. |
| M | `hostinger/vivant/origin-commercial.js` | Interface existante : sauvegarde locale, reprise, démo et parcours consenti. |
| M | `hostinger/vivant/origin-storage.js` | Interface existante : sauvegarde locale, reprise, démo et parcours consenti. |
| M | `hostinger/vivant/origin-vivant.js` | Interface existante : sauvegarde locale, reprise, démo et parcours consenti. |
| M | `pack-docs/config-exemple/origin-vivant-config.php.EXEMPLE` | Exemple de configuration sans secret, activation commerciale désactivée. |
| A | `pack-docs/migrations/003_security_backups_orders.sql` | Migration additive à tester et approuver, jamais exécutée sur Hostinger. |
| A | `premium_security.py` | Contrôles d’accès Premium uniquement : paiement, webhook et codes cadeaux. |
| M | `review/ARCHITECTURE_COMMUNE.md` | Documentation de revue, preuves, limites ou inventaire. |
| M | `review/COMMENCER_ICI.md` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/ARCHITECTURE_ET_MIGRATION.md` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/CORRECTIONS_ET_LIMITES.md` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/LIRE_EN_PREMIER.md` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/VALIDATION.md` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/evidence/api.txt` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/evidence/browser.txt` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/evidence/javascript.txt` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/evidence/php-checks.txt` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/evidence/python.txt` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/evidence/results.json` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/premium-security.diff` | Documentation de revue, preuves, limites ou inventaire. |
| A | `review/audit-followup/source-state.json` | Documentation de revue, preuves, limites ou inventaire. |
| M | `tests/browser/test_platform_browser.py` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| A | `tests/browser/test_visual_demo.py` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| M | `tests/integration/test_vivant_api.py` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| M | `tests/js/storage.test.cjs` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| M | `tests/php/policy.php` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| A | `tests/php/service.php` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| M | `tests/test_origin.py` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| M | `tests/test_platform.py` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| A | `tests/test_security.py` | Tests et fixtures exclusivement isolés, sans clé ou paiement réel. |
| A | `tools/build_visual_demo.py` | Outillage local : stack de test, construction visuelle ou export contrôlé. |
| A | `tools/export_review.py` | Outillage local : stack de test, construction visuelle ou export contrôlé. |
| M | `tools/vivant/local_stack.py` | Outillage local : stack de test, construction visuelle ou export contrôlé. |
| M | `review/VALIDATION_MATRIX.md` | Matrice historique conservée, avec renvoi vers les résultats actuels. |
| A | `review/audit-followup/REVUE_CLAUDE_ORIGIN_2026-10-22.md` | Rapport original reçu, conservé sans modification ; source de constats, pas autorisation de déploiement. |
| A | `review/audit-followup/CROISEMENT_CLAUDE.md` | Correspondance P1–P15 / Y1–Y5, preuves existantes et écarts encore ouverts sur le code 169636f. |
