# Inventaire des fichiers de la phase finale

Comparaison depuis `dddceec` ; 42 fichiers ci-dessous. `inventory.json` donne tailles et empreintes.
Les deux fichiers d’inventaire ne se hachent pas eux-mêmes ; le manifeste du ZIP les couvre.
Les fichiers antérieurement modifiés mais inchangés dans cette phase restent dans les inventaires historiques.

| Fichier | État | Fonction |
| --- | --- | --- |
| `README.md` | Modifié | Accès au dossier final, readiness sécurité, suites et branche courante. |
| `app.py` | Modifié | Sécurité d’accès, défaut fermé et readiness ; aucun calcul/prompt/rendu modifié. |
| `docs/FINANCIAL_RULES.md` | Ajouté | Règles conservatrices de remboursement, litige et suppression écrites pour la recette. |
| `fixtures/security-engine-preservation.json` | Modifié | Empreintes recalculées depuis la base figée, exceptions d’accès explicites. |
| `hostinger/vivant/api/accounts.php` | Ajouté | Réauthentification, rapprochement Stripe et suppression avec conservation comptable. |
| `hostinger/vivant/api/bootstrap.php` | Modifié | HKDF, AEAD/AAD version 2, lecture historique, droits du registre et CLI HTTPS. |
| `hostinger/vivant/api/checkout.php` | Modifié | Commande et tentative préalables ; clients/sessions idempotents avec baux et jetons. |
| `hostinger/vivant/api/index.php` | Modifié | Réception durable asynchrone des webhooks et appel à la suppression sécurisée. |
| `hostinger/vivant/api/registry.php` | Ajouté | Lecture canonique, lignes/tentatives, droits par produit et garde de futur job. |
| `hostinger/vivant/api/registry.sql` | Ajouté | Schéma additif 004 sans conversion automatique de droits. |
| `hostinger/vivant/api/schema.sql` | Modifié | Installation vierge incluant le registre normalisé. |
| `hostinger/vivant/api/security-policy.php` | Modifié | Commentaire de compatibilité : ancien helper sans autorité dans le runtime. |
| `hostinger/vivant/api/stripe-events.php` | Modifié | Rapprochement des ressources courantes, événements financiers et effets SQL. |
| `hostinger/vivant/api/stripe-inbox.php` | Ajouté | Minimisation, chiffrement et unicité de réception, claim/retry/commit sous bail. |
| `pack-docs/CONFIGURATION_TEST.md` | Modifié | Lien vers migration 004 et exploitation du worker en préproduction. |
| `pack-docs/migrations/004_registry_inbox.sql` | Ajouté | Copie identique de la migration additive 004. |
| `premium_security.py` | Modifié | Catalogue Stripe approuvé non ambigu et présence/validité de la configuration de sécurité. |
| `review/COMMENCER_ICI.md` | Modifié | Renvoi explicite du dossier historique vers les corrections finales. |
| `review/audit-followup/CROISEMENT_CLAUDE.md` | Modifié | Statuts historiques conservés avec renvoi à la nouvelle phase. |
| `review/audit-followup/LIRE_EN_PREMIER.md` | Modifié | Notice historique ; lien vers les correctifs finaux. |
| `review/final-2026-10-23/CORRECTIONS.md` | Ajouté | Dossier final : corrections, validation, limites ou exploitation de test. |
| `review/final-2026-10-23/EXPLOITATION_TEST.md` | Ajouté | Dossier final : corrections, validation, limites ou exploitation de test. |
| `review/final-2026-10-23/LIRE_EN_PREMIER.md` | Ajouté | Dossier final : corrections, validation, limites ou exploitation de test. |
| `review/final-2026-10-23/VALIDATION.md` | Ajouté | Dossier final : corrections, validation, limites ou exploitation de test. |
| `review/final-2026-10-23/evidence/browser.txt` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/evidence/environment-presence.json` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/evidence/integration.txt` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/evidence/javascript.txt` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/evidence/operations.txt` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/evidence/python.txt` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/evidence/validation.json` | Ajouté | Preuve locale normalisée, sans journal client ni valeur de secret. |
| `review/final-2026-10-23/premium-security.diff` | Ajouté | Diff minimal app.py depuis la base de cette phase ; document de revue. |
| `tests/fixtures/schema-before-final.sql` | Ajouté | Schéma figé précédent sans données, fixture de migration. |
| `tests/integration/test_registry_migration.py` | Ajouté | Migration sur base fictive dédiée : données conservées, aucun droit inventé. |
| `tests/integration/test_vivant_api.py` | Modifié | 39 tests API/services réels PHP/MySQL, fournisseurs simulés et processus concurrents. |
| `tests/php/policy.php` | Modifié | 42 assertions de politiques, chiffrement/rotation/AAD et minimisation. |
| `tests/php/service.php` | Modifié | Adaptateur CLI strictement réservé aux fixtures de test localhost. |
| `tests/test_origin.py` | Modifié | Tests santé/readiness et webhook adaptés au mode fermé. |
| `tests/test_platform.py` | Modifié | Préservation du moteur et génération via la façade avec réseau interdit. |
| `tests/test_security.py` | Modifié | 11 tests des contrôles Premium, configuration, défaut fermé et catalogue. |
| `tools/export_review.py` | Modifié | Export des seuls blobs du commit ; métadonnées dans le dossier final. |
| `tools/vivant/stripe_worker.php` | Ajouté | Worker CLI financier privé, status et reprise ciblée ; aucune livraison. |

Ajoutés aussi : `review/final-2026-10-23/INVENTAIRE.md` et `inventory.json` (cet inventaire et ses empreintes).

Aucun fichier commercial supprimé. Les pages HTML/JS/CSS, le site public et les générateurs Premium ne sont pas réécrits.
