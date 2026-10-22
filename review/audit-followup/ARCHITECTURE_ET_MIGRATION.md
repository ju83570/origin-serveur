# Architecture conservée et adoption contrôlée

Les décisions validées sont maintenues : PHP/MySQL pour les comptes, commandes
et droits ; Stripe seul prestataire de paiement ; Python pour la génération.
Le même UUID apparaît dans `orders.order_id`, `client_reference_id` et
`metadata.origin_order_id` Stripe. Le contrat du futur travailleur réutilisera
ce même identifiant. Pas de nouveau tarif ni nouvel abonnement.

## Implémenté dans cette branche

- Commande créée avant Checkout, propriétaire/environnement/prix/montant/devise
  persistés côté serveur. Les webhooks ne créent pas de commande à partir d'un
  simple `origin_user_id` ou d'un email.
- Un seul créateur Checkout dans ce module PHP, clés d'idempotence, paiements et droits reliés
  à cette commande. Stripe reste l'autorité sur l'état financier effectif.
- Inbox SQL durable avant traitement, effets transactionnels et états
  `received`/`processed`/`ignored`. Un échec retourne une erreur et reste
  rejouable. Aucun appel de génération dans le webhook Stripe.
- ACL par compte pour sauvegardes, historique et export ; chiffrement au repos
  et rattachement cryptographique du nouveau blob au propriétaire.
- Séparation test/production vérifiée pour clés, événements et commandes.
  Les drapeaux live restent désactivés. Le produit Famille à distance et le
  Miroir payant ne sont pas déclarés prêts commercialement.

Les tables originales et données historiques sont conservées. La migration
ajoute des références ; elle ne considère pas rétrospectivement un ancien achat
non qualifié comme une preuve de droit valable pour n'importe quel produit.

## Encore à intégrer

Le §4 du rapport exige aussi `order_items`, `payment_attempts`, une inbox avec
unicité événement/environnement, `entitlements` et `jobs`. Le schéma courant
monoproduit ne satisfait pas encore l’ensemble de ces conditions. Aucun nouveau
SKU payant ni essai avec de vraies données familiales avant cette revue.

La proposition de `review/ARCHITECTURE_COMMUNE.md` décrit toujours le contrat
PHP → worker Python, l'outbox, les baux de travail, les artefacts et la livraison.
Ces composants ne sont pas annoncés comme réalisés ici. Les vérifications
Stripe Python historiques sont durcies mais restent un chemin de transition,
à retirer seulement après bascule validée vers les autorisations PHP.

Un seul flux de paiement par commande doit être activé lors de cette bascule.
Ne pas raccorder le Checkout PHP neuf aux anciens formulaires sans reprise du
registre et désactivation contrôlée de la création concurrente de paiements.

## Migration 003 — procédure proposée, non exécutée sur Hostinger

1. Traiter les écarts du rapport Claude détaillé maintenant reçu, puis figer les correspondances produit/droits. Confirmer la version MySQL/MariaDB réelle d’Hostinger avant de choisir les baux du worker.
2. Sur une **copie de préproduction**, sauvegarder base et trousseau de clés ;
   démontrer la restauration avant toute migration.
3. Exécuter `pack-docs/migrations/003_security_backups_orders.sql` une seule fois.
   Le schéma complet `api/schema.sql` est destiné à une base vierge.
4. Conserver impérativement `app_key` pour les anciennes sauvegardes. Ajouter
   une nouvelle clé au trousseau, puis changer `encryption_key_id` pour les
   nouvelles écritures ; conserver toutes les clés encore référencées dans
   l'état courant et les dix versions historiques. Aucune rotation automatique.
5. Rapprocher les anciens achats/abonnements avec Stripe : compte, produit,
   prix et environnement vérifiés, puis UUID de commande et rattachement.
   **Sans ce rapprochement, les anciennes lignes ne donnent pas de nouveaux
   droits cloud.** Faire une liste d'anomalies à résoudre avant toute bascule.
6. Préparer la réémission contrôlée des codes cadeaux signés par un ancien
   secret de secours. Tester le relais authentifié des formulaires ; aucun
   secret dans le navigateur. Vérifier les droits et les parcours existants.
7. Vérifier les proxys réels, clés TEST, Price IDs déjà approuvés, endpoint
   webhook et destinataires SMTP de test. Configurer `product_features` après
   validation, pas en devinant le contenu des offres.
8. Recette Stripe TEST complète : commande → paiement → webhook → droits →
   génération Solo → validation interne → livraison privée ; tester aussi
   retard, double clic, rejeu, remboursement, résiliation, export et suppression.
9. Revue Claude/ChatGPT, contrôle du retour arrière et **validation explicite
   du propriétaire avant toute fusion ou déploiement**.

Le retour arrière ne consiste pas à supprimer les nouvelles colonnes ou les
révisions : conserver les données et rétablir un service compatible. Tester la
restauration des sauvegardes chiffrées avec leurs clés sur une copie isolée.

## Accès nécessaires pour la suite

- Rapport Claude désormais archivé ; validation de la réponse aux écarts P1–P10 et aux conditions du §4.
- Environnement Hostinger de préproduction séparé du site public, copie
  anonymisée de schéma/données utiles et accès sécurisé aux clés conservées.
- Compte Stripe TEST, Price IDs et catalogue existants approuvés, signature
  webhook, accès aux événements et à leurs rejeux ; aucun identifiant live requis.
- Validation commerciale produit → droits et inventaire des achats/codes hérités.
- Confirmation des IP de proxys Hostinger, du HTTPS et de la configuration de session.
- Plus tard seulement : secrets Claude/Brevo dans le gestionnaire prévu,
  destinataires de test et autorisation d'une recette distante à coût contrôlé.
- Décisions de consentement, partage des proches, mineurs et conservation légale.
