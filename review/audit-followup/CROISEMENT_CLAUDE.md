# Rapprochement du rapport original de Claude avec les correctifs

Rapport lu intégralement : [REVUE_CLAUDE_ORIGIN_2026-10-22.md](REVUE_CLAUDE_ORIGIN_2026-10-22.md).
Les deux pièces jointes sont identiques, SHA-256 :
`a964464b01a8afd2f26428c6ff576cb1dac2abd1e5574b42d8602230998cdb5a`.

**Claude a relu la base initiale `f2b1500`, transmise avec les documents `32d6b68`.
Il n'a pas encore audité les correctifs `169636f`.** Ce rapprochement est notre
analyse du code courant, pas une nouvelle validation indépendante de Claude.

Les instructions dans le rapport sont des recommandations techniques à
confronter à la demande du propriétaire. Par exemple, le rapport proposait de
ne pas modifier le moteur à ce stade ; le propriétaire a ensuite explicitement
demandé les correctifs minimaux Y1–Y3. Aucune extraction du générateur ni
modification de calcul, prompt ou rendu n'est engagée à la réception du rapport.

## P1 à P10 : statut exact

« Corrigé localement » signifie correction présente et preuves locales,
sans recette Hostinger/Stripe ni approbation indépendante du correctif.

| Constat | Statut sur 169636f | Code et preuve existants | Écart / test restant |
| --- | --- | --- | --- |
| P1 — écrasement des sauvegardes | Corrigé localement | `backups.php` : révision sous verrou, conflit 409, dix versions précédentes ; API `test_revision_conflicts_and_recovery_versions`, `test_competing_saves_have_one_winner`, tests navigateur d'onglet périmé. | Les requêtes concurrentes passent par le serveur PHP de développement ; pas de charge multi-processus réelle ni test sur deux appareils physiques. |
| P2 — registre des droits par produit | **Partiel** | `orders` conserve compte, environnement, produit, prix, total/devise ; accès par commande vérifiée. Le test du Miroir montre qu'il n'accorde que `mirror_deep`. | Le rapport demande `order_items`, `payment_attempts`, `entitlements`, etc. absents. `purchases.product` a été ajouté : cela ne suit pas la recommandation de ne pas y ajouter de SKU. Recentrer le registre sur les commandes/lignes et préparer la migration avant tout nouveau SKU. Le test direct « Miroir n'autorise pas un job Solo » attend le contrat de jobs. |
| P3 — événements financiers manquants | **Partiel** | Paiements différés, `invoice.payment_failed`, remboursement et création de litige traités. Tests de succès différé/remboursement et impayé d'abonnement. | Tous les événements `charge.dispute.*` ne sont pas traités. Tests dédiés encore manquants pour `async_payment_failed`, expiration, création/résolution d'un litige. Une réouverture après litige gagné est volontairement manuelle ; règle à faire valider. |
| P4 — désordre d'abonnements | Corrigé localement | État courant relu et annulation terminale conservée ; `test_subscription_plan_from_price_and_out_of_order_cancellation` rejoue un updated après deleted. | Recette depuis Stripe et concurrence réelle à compléter. |
| P5 — réseau dans une transaction | **Non clos** | L'insertion initiale de `stripe_events` est durable ; les échecs restent rejouables. | `processStripeEvent()` ouvre encore la transaction, puis `applyStripeEvent()` appelle `$read()` pendant celle-ci. Pas de réponse 200 après simple mise en inbox, pas de worker/outbox. Il faut dissocier réception durable et traitement différé, avec reprise et contrat de concurrence testés. |
| P6 — proxy et débit | Corrigé localement, cible non vérifiée | `proxyClientIp()` ne fait confiance qu'aux proxys déclarés, choisit la frontière de confiance et refuse les entêtes invalides. Limites compte + IP sur login, compteurs SQL atomiques. Assertions PHP et test API par compte. | Les IP des proxys réels restent inconnues ; pas encore de recette HTTP de plusieurs clients derrière le vrai proxy Hostinger. |
| P7 — idempotence Checkout | **Partiel côté validation** | Commande avant Checkout, idempotence client et session, verrou sur la commande, réemploi de session. Tests de deuxième demande séquentielle et de timeout ambigu. | Le test demandé de deux POST simultanés créant un seul client/une seule session manque. La création du client utilise l'idempotence Stripe et une écriture conditionnelle, pas un verrou tenu pendant l'appel réseau. Vérifier également les réponses Stripe de conflit d'idempotence. |
| P8 — séparation des clés et AAD | **Partiel** | Préfixe de clé, rotation, lecture historique, propriétaire authentifié dans le contenu chiffré ; copie inter-comptes et ancienne clé testées. | Toujours `secretbox`, pas XChaCha20-Poly1305/AAD. Le limiteur utilise encore directement `app_key` ; pas de sous-clés HKDF par usage. Prévoir une nouvelle version de blob avec lecture des anciennes versions et tests de migration. Ne jamais remplacer simplement l'ancienne clé. |
| P9 — données après résiliation | Corrigé localement | `load`, `export`, versions accessibles au compte vérifié sans abonnement. Test `test_export_and_recovery_remain_available_without_entitlement`. | L'écriture refusée renvoie 403 `product_required`, et non le 402 proposé. La différence est explicite ; lecture et récupération restent autorisées. |
| P10 — suppression et comptabilité | **Partiel côté validation** | Mot de passe redemandé, paiement/abonnement ouvert bloquant. `orders.user_id` devient NULL par FK ; la commande n'est pas supprimée avec le compte et ne contient pas l'email. | Le test actuel supprime un compte avec sauvegardes, pas un compte avec commande comptable conservée. Ajouter ce test, le contrôle de l'anonymisation et la politique de rétention. Le Stripe Customer ID conservé reste un identifiant pseudonyme, pas une anonymisation totale. |

## Y1 à Y5 et préservation du moteur

| Constat | Statut exact |
| --- | --- |
| Y1 | Contrôle offre/prix/devise/environnement corrigé et testé, y compris Solo/Naissance. La consommation Stripe reste en mémoire et ne résiste pas au redémarrage ou aux workers multiples. **Constat complet partiellement résolu.** |
| Y2 | Webhook fermé si secret absent/faible, comparaison constante. Cependant `ENFORCE_ACCESS` reste désactivé par défaut, `/ready` ne vérifie pas les variables de sécurité et la configuration réellement déployée est inaccessible. Le test de readiness sécurité demandé par Claude manque. |
| Y3 | Repli faible supprimé ; secret cadeau dédié exigé. Le registre d'usage reste dans `/tmp` : la résistance au redéploiement n'est pas résolue. |
| Y4 | Thread non durable inchangé. Aucun worker, reprise après crash ni état email `unknown` implémentés. |
| Y5 | Coût de rechargement du moteur démo inchangé, acceptable uniquement dans le cadre local. |

Les preuves de préservation du moteur restent applicables aux calculs, prompts,
rendus et au travailleur imbriqué. Le hash global diffère désormais de celui
vérifié par Claude, à cause des correctifs d'accès autorisés : comparer le diff
de sécurité et les preuves AST, sans présenter l'ancien hash comme actuel.

Le test d'interdiction des sockets couvre l'application de démonstration directe.
Les tests navigateur interdisent les requêtes navigateur externes, mais cela ne
prouve pas l'interdiction de tout réseau côté serveur de `platform_demo`.
L'extension de ce contrôle au chemin complet de la façade reste à ajouter.

## Conditions d'architecture encore ouvertes

1. Confirmer la version MySQL/MariaDB réelle d'Hostinger, sans la déduire de
   MariaDB 11.4 dans Docker. Le rapport exige MySQL 8 ou MariaDB ≥ 10.6 pour
   `SKIP LOCKED`, sinon un bail compatible par UPDATE conditionnel.
2. Compléter le modèle commande/lignes/tentatives/inbox/droits/jobs et les
   unicités environnement/événement et ligne/révision/environnement.
3. Valider les règles de remboursement partiel, litige, travail en échec,
   relance et validation humaine. Les règles conservatrices existantes sont
   documentées mais ne valent pas approbation commerciale.
4. Définir le contrat privé PHP → Python et l'accès de PHP à un moteur qui
   exige un code/paiement. `submitted` ne signifie jamais « livré ».
5. Aucun essai commercial ni de vraies données familiales tant que ces écarts,
   en particulier P5 et P8, ne sont pas corrigés et validés.

P11–P15 : P13 est traité par le rattachement propriétaire immuable de
l'abonnement. Confirmation email par POST (P11), anti-énumération (P12), CSP
des pages Hostinger (P14) et configuration de sessions portable (P15) restent
à auditer/traiter. La CSP de la façade locale ou du pack autonome ne constitue
pas une preuve de CSP correcte sur Hostinger.

## Ce que ce rapprochement change

Les **71 tests et 31 assertions PHP** du code 169636f restent les résultats
de notre dernière exécution ; Claude n'en a pas confirmé l'ensemble et aucune
suite n'est relancée pour cette mise à jour documentaire seule. Ce total ne
démontre pas la clôture de P1–P10. Le plan prioritaire est P5 puis P8 et le modèle
P2, suivis des tests ciblés P3/P7/P10 et de la supervision/configuration Y2.

Aucune modification supplémentaire de moteur, aucun changement de tarif,
aucune fusion et aucun déploiement ne sont réalisés pour ce rapprochement.
