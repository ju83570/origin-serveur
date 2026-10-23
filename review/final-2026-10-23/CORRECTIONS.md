# Corrections réalisées et limites

« Corrigé et testé localement » signifie code exécuté sur données fictives dans
PHP 8.3 / MariaDB 11.4. La recette distante et l'approbation indépendante restent
à faire. Les anciennes tables ne sont pas supprimées ; aucun calcul, prompt,
texte narratif ou rendu Premium n'a été modifié.

## P2, P3, P5, P7, P8, P10

| Constat | Correction effective | Preuve automatisée | Limite restante |
| --- | --- | --- | --- |
| P2 — droits par produit | `registry.php`, migration 004 : lignes immuables, tentatives, droits explicites, environnement et révision. L'API ne lit plus `purchases` pour accorder des droits et n'y inscrit plus les paiements. Le registre normalisé est l'autorité ; les anciennes colonnes de commande sont des miroirs de compatibilité. | Achat Miroir ≠ cloud ou job Solo ; altération d'un ancien achat ou en-tête sans effet ; contraintes d'unicité des jobs ; migration sans droits inventés. | Rapprochement Stripe et import contrôlé des commandes historiques à préparer sur copie. Aucun nouveau SKU activé ni job Solo réellement exposé. |
| P3 — événements financiers | Checkout différé réussi/échoué, expiration, abonnement créé/modifié/supprimé, facture payée/impayée, remboursement et cinq variantes de litige traités. Ressources Stripe courantes relues ; montant remboursé monotone ; annulation/litige terminal protégés. Facture de renouvellement rapprochée même si son PaymentIntent est inconnu du Checkout initial. | Tests distincts d'échec/expiration, remboursement avant Checkout, partiel, fin de litige gagnée/perdue, retrait/rétablissement de fonds, impayé et événement ancien. | Pas d'appel au vrai Stripe. API `2025-08-27.basil` et formes exactes de facture à recetter. Tout remboursement d'une échéance bloque conservativement l'accès de l'abonnement ; commandes par échéance non implémentées. |
| P5 — transaction et inbox | HTTP vérifie signature/mode et insère durablement un événement minimisé/chiffré, puis répond 200. Worker CLI indépendant : lectures Stripe hors transaction, effets SQL + outbox + validation inbox atomiques. Bail de 300 s renouvelable, jeton vérifié au commit, reprise après crash, backoff et blocage après dix tentatives. | Deux vrais processus PHP traitent une seule inbox ; jeton périmé interdit d'accorder un droit ; panne rejouable ; aucun callback fournisseur autorisé en transaction ; HTTP sans effet de droit. | Cron privé et supervision à installer seulement après accord de déploiement. Outbox sans dispatcher ; aucun worker de génération/délivrance. |
| P7 — double clic | Commande et tentative avant Stripe. Client Stripe protégé par verrou court + bail de 90 s, clé d'idempotence stable par utilisateur/environnement. Session protégée de même, clé stable par commande ; réseau hors transaction ; concurrence renvoie 409 avec Retry-After. | Deux processus PHP CLI concurrents : un seul POST client et un seul POST session ; variante client existant ; timeout ambigu réutilise les mêmes références. | Comportement réel des conflits Stripe et rétention distante des clés d'idempotence à recetter. Les baux ne remplacent pas l'idempotence fournisseur après un timeout. |
| P8 — chiffrement | Nouvelles écritures `ov2:key_id:…`, XChaCha20-Poly1305. AAD lie version, clé, environnement, usage et sujet (utilisateur ou événement). Sous-clés HKDF séparées pour sauvegardes, inbox et limiteur. Lectures historiques conservées. | Copie entre comptes refusée, altération/AAD incorrects refusés, rotation et ancienne clé, lecture ov1 et format initial, clé/version inconnue refusée, usages distincts. | Le format initial non versionné ne possédait pas de liaison au propriétaire : il reste lisible pour préserver les données. Réécrire prudemment ces sauvegardes après chargement vérifié. Clés anciennes indispensables pour l'historique. |
| P10 — suppression | Mot de passe actuel et confirmation requis ; nouvelle vérification sous verrou après réconciliation Stripe hors transaction. Abonnement non terminal, paiement ou préparation en cours bloquent. Sauvegardes/droits supprimés ; commandes détachées (`user_id=NULL`), lignes/tentatives/litiges/ajustements conservés. Remboursement après suppression possible sans recréer le compte. | Compte avec paiement et sauvegardes réellement supprimé : pièces conservées sans nom/email, données familiales effacées ; remboursement ultérieur rapproché ; abonnement distant actif et pagination inconnue bloquants. | Références Stripe pseudonymes, pas anonymisation totale. Durée légale, purge et rétention des factures à faire valider. Aucune suppression distante de Stripe Customer déclenchée. |

## P1, P4, P6, P9 conservés

| Constat | Fonction conservée et vérifiée | Limite |
| --- | --- | --- |
| P1 | Révision optimiste sous verrou, conflit 409, dix anciennes versions, refus d'écraser un blob illisible. API concurrente et navigateur : onglet périmé et JSON local endommagé récupérables. | Concurrence de sauvegardes locale ; pas deux appareils physiques ni test de charge multi-nœuds. |
| P4 | Abonnement relu chez Stripe, propriétaire immuable, prix exact, fin de période nécessaire ; événement ancien ne réactive pas une annulation terminale. | Propriétaire immuable couvre aussi P13 ; test Stripe distant encore requis. |
| P6 | IP transférée acceptée uniquement du proxy déclaré ; frontière de confiance et en-têtes invalides contrôlés ; quotas SQL atomiques par compte et IP. HKDF remplace la clé brute du HMAC. | Adresses des proxys Hostinger inconnues : pas de confiance automatique dans X-Forwarded-For. Réseau réel non testé. |
| P9 | Lecture, export et récupération d'historique ouverts au compte vérifié même après perte de l'abonnement. Écriture soumise au droit précis. | Le refus d'écriture reste HTTP 403 `product_required`, pas le 402 suggéré ; comportement explicite conservé. |

## Y1–Y3 : sécurité minimale du moteur

Les contrôles déjà présents sont maintenus : session en paiement unique, état
complet/payé, environnement exact, une ligne de quantité 1, Price ID, montant et
devise du catalogue approuvé, avant toute normalisation Naissance → Solo. Un
abonnement ou le Miroir ne prouve pas l'achat d'un livret différent (Y1).

Cette phase ajoute le rejet d'un catalogue ambigu (même Price ID pour deux offres),
de produits non livrets et des montants/devises invalides. `ENFORCE_ACCESS` vaut
désormais 1 par défaut ; une désactivation explicite ferme aussi le webhook.
L'absence ou faiblesse du secret ferme toujours le webhook, et la comparaison
reste constante. `/ready` signale les paramètres de sécurité manquants ou invalides
sans appeler de fournisseur ; `/health` reste indépendant (Y2).

Le secret cadeau dédié fort reste obligatoire, sans repli sur `origin`, le secret
webhook ou une clé API (Y3). Les tests de refus sont conservés.

**Y1 et Y3 ne sont pas clos intégralement** : `_stripe_usages` reste en mémoire,
et le fichier d'usage des cadeaux reste dans `/tmp`. Réutilisation après crash,
redéploiement ou avec plusieurs workers possible. Proposition minimale suivante :
réservation atomique de l'usage et du job par commande/ligne/révision dans l'unique
registre PHP/MySQL, contrat privé signé vers Python, puis accusé durable séparé
de « livré ». Ne pas ajouter un registre concurrent de paiements ou de droits
dans Python. Ce contrat et son adaptateur vers le moteur doivent être validés
avant implémentation. Le thread de génération non durable et le statut d'un
email en timeout (Y4) restent inchangés.

### Préservation

`premium-security.diff` contient quatre lignes ajoutées et trois retirées
dans `app.py` par rapport à `dddceec`. La fixture de préservation est calculée
depuis la base figée `32d6b68`, pas depuis le code nouvellement corrigé. Elle
autorise explicitement readiness et les seules affectations de sécurité en plus
des fonctions d'accès déjà autorisées. Les empreintes AST du reste du module et
du travailleur imbriqué sont testées ; l'empreinte de ce travailleur reste
`ab5eaf334792c25e0874a339b7d2e267df672f670246c09e1f37e76e7f3442ff`.
Les 70 ressources/dépendances historiques suivies par la fixture sont inchangées.
Les six parcours Solo/Couple/Famille/Prestige/Naissance/Vocation rendent de vrais
HTML/PDF personnalisés avec des narratives de test.

### Environnement accessible

Contrôle limité à la présence, sans affichage des valeurs : `WEBHOOK_SECRET`,
`CODES_SECRET`, `STRIPE_KEY`, `STRIPE_PRICE_CATALOG`, `STRIPE_MODE`,
`ENFORCE_ACCESS`, `ANTHROPIC_API_KEY`, `BREVO_SMTP_KEY`, `EMAIL_DEST` sont absents
ou vides dans le shell cloud. L'absence d'ENFORCE_ACCESS est désormais sûre par
défaut ; elle ne renseigne pas la configuration du service réellement déployé.

La stack PHP de test a ses propres secrets de base/chiffrement/webhook aléatoires,
privés et éphémères, sans clé réelle de fournisseur. Les sentinelles ressemblant
à des clés Stripe sont limitées aux processus CLI de test protégés par mode test
et origine localhost ; aucun endpoint HTTP de simulation n'est ajouté.
**La configuration et les secrets de production sont inaccessibles et non vérifiés.**

## Autres points ouverts

- P11 (confirmation email par POST), P12 (anti-énumération), P14 (CSP des pages
  réellement servies par Hostinger), P15 (portabilité des sessions) ne font pas
  partie des corrections finales. Les politiques de la façade ne prouvent pas
  celles d'Apache/Hostinger.
- Aucun dispatcher PHP → Python, reprise de génération ni livraison client
  durable n'est activé. Un HTTP 200 du moteur historique ne prouve pas la livraison.
- Aucun partage de données familiales entre comptes n'est ajouté : accès au
  propriétaire uniquement, export volontaire ; données locales du navigateur
  non chiffrées et sauvegarde serveur non assimilable à du chiffrement de bout en bout.
- API financières : isolation des environnements par configuration et contraintes.
  Les environnements distants doivent avoir des bases et secrets distincts.
- Aucune nouvelle offre, tarification ou activation Stripe live. Les textes
  commerciaux préexistants du pack ne constituent pas une validation des offres.
