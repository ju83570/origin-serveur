# Revue indépendante Claude — ORIGIN RÉVOLUTION / VIVANT
Base relue : commit `f2b1500` (ZIP `origin-serveur-32d6b68…`), 22 octobre 2026.

## 0. Ce que j'ai réellement vérifié

| Vérifié par moi | Résultat |
| --- | --- |
| `app.py` SHA-256 | Identique à `17a502fc…` annoncé |
| `premium-engine.diff` | Seuls `/health` et `/ready` changent dans le moteur. Prompts, calculs et rendus intacts |
| Lecture complète | `bootstrap.php`, `index.php`, `payment-policy.php`, `schema.sql`, `.htaccess`, `demo*.py`, `platform_demo.py`, `origin-*.js`, `arbre-vivant.html` (validation), `ARCHITECTURE_COMMUNE.md`, `VALIDATION_MATRIX.md` |
| `php -l` sur tous les PHP | OK |
| `node --test tests/js/storage.test.cjs` | 4/4 réussis (relancé ici) |
| Isolation démo | `app.py` n'importe ni `demo`, ni `demo_support`, ni `platform_demo`. Tests avec `socket.connect` et DNS interdits (`tests/test_origin.py:36-37`) |

**Non relancé ici** : les 26 tests Python, 5 PHP/MariaDB, 5 Chromium et le script de 13 assertions PHP. Il manque MariaDB, WeasyPrint et la config. Je ne confirme donc pas les « 40 » moi-même ; je confirme seulement que le code lu est cohérent avec ce que la matrice annonce, et que la matrice est honnête sur ses limites.

## 1. Réponses aux cinq questions

1. **Préservation du moteur : suffisante.** Hash + diff + isolation par import. Réserve : l'isolation démo repose sur des remplacements à chaud (`engine.requests`, `get_coords`, `demo_support.py:117-130`). Le moteur fait un appel `urllib` (Nominatim, `app.py:413-417`) qui contourne `requests`. Il n'est bloqué que parce que `get_coords` est remplacée. Garder le test qui interdit les sockets, et l'étendre au chemin `platform_demo`.
2. **Autorité PHP/MySQL unique + Stripe seul prestataire + Python exécutant : accepté, sous les conditions du §4.**
3. **Point d'entrée Python : voir §5.**
4. **Défauts bloquants : §2 (PHP) et §3 (Python).**
5. **Tests manquants : §6.**

## 2. Constats PHP (`hostinger/vivant/api/`)

### Bloquants avant tout Stripe test

| # | Sév. | Constat | Impact | Correction | Test attendu |
| --- | --- | --- | --- | --- | --- |
| P1 | Haute | **Sauvegarde sans révision** : `index.php:98-101`. Dernier écrit gagne. Un appareil neuf avec un carnet vide écrase la sauvegarde existante. Pas d'historique. | Perte irréversible de souvenirs familiaux. La matrice parle de « synchronisation » : ce n'est pas le cas. | Colonne `revision`. Le client envoie `base_revision`. `409` si elle diffère. Garder la version N-1. | Deux appareils, écritures croisées → conflit signalé, rien perdu |
| P2 | Haute | **Droits non liés à un produit** : `schema.sql:43-50`, `index.php:31-33`, `bootstrap.php:55`. `purchases` sans SKU, prix, montant, devise ni environnement. `mirror_paid` = « a un achat payé quelconque ». | Dès qu'un second produit existe, un achat en débloque un autre. | Table `orders`/`order_items` de l'architecture §3 avant tout SKU payant. Ne pas ajouter de SKU sur `purchases`. | Achat Miroir ≠ droit Solo |
| P3 | Haute | **Événements Stripe non gérés** (`index.php:27-47`) : ni `charge.refunded`, ni `charge.dispute.*`, ni `checkout.session.async_payment_succeeded/failed`, ni `invoice.payment_failed`. | Remboursement : accès jamais retiré. Paiement différé : accès jamais accordé. | Les traiter, avec règles métier écrites d'abord (remboursement partiel, litige). | Un test par événement |
| P4 | Haute | **Événements désordonnés** : `index.php:39-44` et `:133` appliquent le contenu de l'événement, pas l'état courant. Un `updated` ancien après un `deleted` réactive l'abonnement. | Accès payant sans abonnement. | Sur chaque événement d'abonnement, relire `subscriptions/{id}` (déjà fait ligne 35 pour `completed`) ou comparer `event.created` stocké. | Rejouer updated après deleted → reste annulé |
| P5 | Moyenne | **Appel réseau Stripe dans la transaction du webhook** : `index.php:23` ouvre la transaction, `:35` appelle Stripe (timeout 20 s, `bootstrap.php:54`). | Verrou long sur `stripe_events`. Livraisons concurrentes bloquées. Timeouts répétés côté Stripe. | Inbox : INSERT + commit, réponse 200, puis traitement. C'est votre §5 de l'architecture. | Deux livraisons parallèles du même événement |
| P6 | Haute | **Limitation de débit par `REMOTE_ADDR`** : `bootstrap.php:32-33`. Derrière un CDN/proxy, tous les visiteurs partagent l'IP du proxy. | 5 inscriptions par heure et 12 connexions par 15 min **pour tout le site**. Les clients légitimes sont bloqués dès quelques essais. | N'utiliser `X-Forwarded-For` que si `REMOTE_ADDR ∈ trusted_proxy_ips` (liste déjà lue ligne 17). Ajouter une limite par e-mail. | Requêtes via IP proxy de confiance, avec XFF distinctes |
| P7 | Moyenne | **Checkout sans idempotence** : `index.php:105-116`, `bootstrap.php:54` (pas d'`Idempotency-Key`). Double clic → deux clients Stripe (ligne 111) et deux sessions payantes Miroir. | Doublons, double paiement possible. | `order_id` créé avant Checkout. `Idempotency-Key` sur chaque appel Stripe. Verrou sur la création du client. | Deux POST `checkout` simultanés → une seule session |
| P8 | Moyenne | **Chiffrement** : `bootstrap.php:40-42`. Clé unique globale, pas d'identifiant de clé, pas de liaison au compte. Même `app_key` aussi utilisée comme clé HMAC du limiteur (`:32`). | Rotation impossible. Une personne qui peut écrire en SQL copie le blob d'un compte vers un autre et il se déchiffre. | Préfixe `version\|key_id`. XChaCha20-Poly1305 avec AAD = `user_id`. Sous-clés dérivées par usage (HKDF). | Blob copié vers un autre compte → refus. Déchiffrement avec ancienne clé après rotation |
| P9 | Haute | **Données verrouillées sans abonnement** : `index.php:99` et `:103` bloquent `save` ET `load` en production sans abonnement actif. | Une personne qui résilie ne peut plus récupérer ses données (accès/portabilité RGPD). | Toujours autoriser `load`/export. Ne conditionner que l'écriture, si c'est le modèle voulu. | Compte sans abonnement → `load` OK, `save` 402 |
| P10 | Moyenne | **Suppression de compte** : `schema.sql:49` `ON DELETE CASCADE` sur `purchases` (et sur `subscriptions`) efface la trace comptable. `index.php:120-125` n'exige pas de mot de passe. | Perte de pièces comptables. Un compte détourné peut être supprimé en un clic. | `orders` en `RESTRICT` ou anonymisation. Re-demander le mot de passe avant suppression. | Suppression → ligne comptable conservée sans e-mail |

### Durcissements (non bloquants)

- **P11** (Basse) `index.php:10-15` : la vérification d'e-mail se fait en GET. Les scanners de messagerie consomment le jeton. Prévoir une page de confirmation + POST.
- **P12** (Basse) Énumération : `index.php:54` (409 « déjà utilisée ») et `:66` (erreur SMTP uniquement pour un compte existant, alors que l'inconnu reçoit 200).
- **P13** (Basse) `index.php:133` : `ON DUPLICATE KEY UPDATE user_id=VALUES(user_id)` permet de réattribuer un abonnement à un autre compte via la métadonnée de repli (`:42`). Retirer `user_id` de la mise à jour.
- **P14** (Basse) Pas de CSP sur les pages HTML (`.htaccess:1-9`), alors que l'API en a une. Les scripts inline imposent hash ou nonce. L'impact d'un XSS serait fort (même origine que l'API et la session).
- **P15** (Basse) `bootstrap.php:34` : chemin de cookie `/vivant` codé en dur, et pas de `session.save_path` ni de `gc_maxlifetime` explicites.

### Ce qui est bon (à ne pas casser)
- Signature webhook : horodatage, comparaison constante, rejet test/live croisé (`index.php:17-22`).
- Jeton de réinitialisation haché, usage unique, `FOR UPDATE`, `session_version` incrémenté (`:71-85`).
- Politique de paiement fermée par défaut (`payment-policy.php`).
- CSRF sur tous les POST. Le webhook est traité avant `csrf()`, ce qui est correct.
- **Front : pas de XSS trouvé.** `arbre-vivant.html:76` applique une liste blanche stricte sur les photos (`data:image/(png|jpeg|webp);base64,…`) et le reste passe par `escapeHTML`. Une sauvegarde restaurée depuis le serveur est revalidée au chargement. J'avais soupçonné `src="'+p.photo+'"` (`:97`, `:102`) ; la validation en amont le rend sûr. **Conserver cette validation.** Elle devient critique avec le partage entre comptes.

## 3. Constats Python (moteur figé, à vérifier sur l'environnement RÉEL)

Ces points concernent le code **déjà en production**. Je ne demande pas de modifier `app.py` aujourd'hui, mais de **vérifier les variables d'environnement maintenant**.

| # | Sév. | Constat | Impact | Action |
| --- | --- | --- | --- | --- |
| Y1 | Haute | **Un paiement Stripe ne prouve pas l'offre** : `_stripe_verifier` (`app.py:6272-6286`) accepte toute session `paid` ou `no_payment_required`. L'offre vient du client (`webhook`, `:6417+`). Aucun contrôle de produit, montant ni `livemode`. | Une session Solo (79 €), Miroir (19 €) ou un abonnement Vivant (9,90 €) ouvre Famille ou Lignée, 3 fois. Compteur en mémoire (`:6267`, `:6676`) remis à zéro au redémarrage. | Critique dès qu'un 2ᵉ produit Stripe existe sur le même compte. Correction future : lier `session → offre` (prix/métadonnée) et persister la consommation. |
| Y2 | Haute | **Authentification conditionnelle** : `if WEBHOOK_SECRET and …` (`:6419`). Si la variable est absente, le webhook est ouvert. `ENFORCE_ACCESS` est désactivé par défaut (`:6266`). La comparaison utilise `!=` (non constante). | N'importe qui peut déclencher des générations (coût Claude, e-mails). | **Vérifier maintenant** : `WEBHOOK_SECRET` défini, `ENFORCE_ACCESS=1`, `STRIPE_KEY` défini. `/ready` (`:6402-6413`) ne signale rien de tout ça. |
| Y3 | Moyenne | **Secret des codes cadeau** : repli sur `"origin"` (`:6288`) si ni `CODES_SECRET`, ni `WEBHOOK_SECRET`, ni clé API. Le fichier des codes utilisés est dans `/tmp`. | Codes forgeables. Codes réutilisables après redéploiement. | Vérifier `CODES_SECRET` défini et fort. |
| Y4 | Moyenne | **Travail non durable** : la génération part dans un thread dans la requête (`:6677`). | Un redémarrage ou un timeout Gunicorn tue le livret. Pas de reprise. | C'est exactement le worker de l'architecture §6. |
| Y5 | Basse | `load_engine()` ré-exécute les 6 700 lignes de `app.py` à chaque génération de démo (`demo_support.py:23-28`). | Mémoire et latence. Pas un risque de sécurité. | Acceptable pour une démo locale. Ne jamais exposer. |

**Isolation démo : validée.** À ajouter au déploiement : `demo.py`, `demo_support.py`, `platform_demo.py` et `fixtures/` ne doivent pas être servis en production.

## 4. Décisions sur l'architecture (`ARCHITECTURE_COMMUNE.md`)

| Décision | Verdict |
| --- | --- |
| Autorité unique PHP/MySQL pour comptes, commandes, droits | **Accepté** |
| Stripe seul prestataire de paiement | **Accepté** |
| Python exécutant, sans droit propre | **Accepté**. `_stripe_verifier` sort du nouveau parcours |
| `order_id` UUID serveur avant Checkout, + `environment` partout | **Accepté** |
| États séparés paiement / travail / validation / livraison | **Accepté** |
| Inbox durable + outbox | **Accepté** (corrige P5) |
| Bail SQL sans broker | **Accepté sous condition** : `SELECT … FOR UPDATE SKIP LOCKED` exige MySQL 8 ou MariaDB ≥ 10.6. **Vérifier la version réelle d'Hostinger avant de concevoir le bail.** Sinon, bail par `UPDATE … WHERE state='queued' LIMIT 1` + vérification de `ROW_COUNT()` |
| HMAC machine à machine avec secrets par environnement | **Accepté**. Rejeter les requêtes rejouées (nonce + fenêtre) |
| Partage familial : invitation à jeton haché, rôles, révocation | **Accepté**. Hors périmètre du premier test, `family_ready` reste fermé |
| Tables FK | **À corriger** : `orders` en `RESTRICT`, jamais `CASCADE` depuis `users` (P10) |

**Conditions pour reprendre le développement :**
1. Schéma `orders`, `order_items`, `payment_attempts`, `stripe_inbox`, `entitlements`, `jobs`, avec unicité `(environment, stripe_event_id)` et `(order_item_id, revision, environment)`.
2. Règles écrites : remboursement, litige, échec du travail après paiement, qui relance, qui valide.
3. Version MySQL d'Hostinger confirmée.
4. P1, P6, P8 et P9 corrigés avant que de vraies personnes testent l'espace.

## 5. Point d'entrée Python

`generer()` est une fonction imbriquée dans `webhook()` (`app.py:6417+`). On ne peut pas l'appeler sans passer par HTTP. Deux options :

- **A (recommandée pour le premier test) : ne rien changer dans le moteur.** PHP appelle `/webhook` en privé, avec `X-ORIGIN-SECRET`. PHP impose l'offre et les données autorisées. Le moteur garde sa validation par e-mail à `EMAIL_DEST`. Statut côté PHP = `submitted`, **jamais** « livré ». C'est cohérent avec votre remarque sur la validation interne. Prérequis : `WEBHOOK_SECRET` défini et `ENFORCE_ACCESS=1` (Y2), et soit un code cadeau à usage unique, soit un contrôle d'accès équivalent pour que PHP passe cette barrière. **Décision à prendre** : comment PHP s'authentifie auprès d'un moteur qui exige un code ou un paiement ?
- **B (après le premier test) : extraction mécanique.** Sortir `generer()` en fonction de module, sans changer son contenu, derrière une route interne signée `/internal/job` idempotente sur `job_id`. À valider par diff AST + hash de tous les prompts. **Accord explicite de Julien requis.**

## 6. Tests manquants avant UN parcours Solo en Stripe test

1. Webhook : désordre (updated après deleted), deux livraisons simultanées, session inconnue, montant/devise/prix incorrect, `async_payment_*`, remboursement, litige.
2. Double clic sur Checkout : un seul client et une seule session.
3. Deux appareils : conflit de sauvegarde. Blob copié entre comptes. Rotation de clé.
4. Limitation de débit derrière proxy de confiance.
5. Python : une session Solo ne débloque pas Famille. Environnement sans `WEBHOOK_SECRET`/`ENFORCE_ACCESS` → `/ready` dégradé. Codes avec secret par défaut refusés.
6. Panne après paiement et avant travail. Crash du worker en cours de travail. Timeout Brevo → état `unknown`, pas de renvoi automatique.
7. Suppression de compte : ligne comptable conservée et anonymisée. `load` possible sans abonnement.
8. Sur Hostinger réel : version MySQL, `.htaccess` (sources privées non servies), SMTP réel, cookie sur `/vivant/`, HTTPS.

## 7. Verdict

Le dossier est **honnête** : la matrice sépare correctement développé, automatisé, ponctuel et non testé, et le moteur est bien préservé. L'architecture proposée est **bonne**.

Le code PHP actuel est un **bon prototype de comptes et de sauvegarde, pas encore un registre de droits**. Les quatre points à traiter d'abord sont **P1** (perte de données), **P2/P3/P4** (droits), **P6** (blocage par IP partagée) et **P9** (données verrouillées). Côté production existante, **Y1 à Y3 sont à vérifier cette semaine**, indépendamment de VIVANT.

Rien n'a été fusionné, déployé ni modifié.
