# Correctifs et limites

## Moteur Premium : modifications minimales

| Constat transmis | Correction | Limite avant adoption réelle |
| --- | --- | --- |
| Y1 : offre/prix Stripe insuffisamment vérifiés | Session complète et payée, mode paiement, environnement, identifiant de session, devise, montant exact, unique ligne et quantité 1, Price ID et montant de cette ligne vérifiés sur catalogue serveur. `solo` + type naissance exige le produit naissance avant normalisation. | Catalogue réel à fournir et approuver. Remises, gratuités et taxes modifiant le total sont refusées par défaut. Aucune valeur de tarif inventée. |
| Y2 : secret webhook conditionnel | Absence/secret de moins de 32 caractères → 503, secret incorrect → 401 ; comparaison constante avant lecture métier ou démarrage d'un travail. | Le formulaire doit passer par un relais serveur. Ne jamais placer ce secret dans du JavaScript public. |
| Y3 : secret de secours faible | Seul `CODES_SECRET` dédié est accepté, au moins 32 caractères ; aucun repli vers Claude, le secret webhook ou une constante. Génération et vérification fermées si non configurées. | Les codes émis avec une ancienne clé ne sont pas réacceptés silencieusement : inventaire et réémission contrôlée avant migration. |

`premium_security.py` ne contient que les contrôles d'accès. Les calculs, prompts,
textes, générateurs HTML/PDF, pièces jointes, enrichissements et le travailleur
imbriqué `generer` restent inchangés. Les empreintes AST et des 70 ressources et
dépendances originales sont vérifiées automatiquement. Voir aussi
`premium-security.diff` pour l'intégralité du changement dans `app.py`.

Le test de préservation initial est conservé dans son historique. Son successeur
utilise une preuve calculée **avant modification** depuis `32d6b68`, exclut
explicitement les seules fonctions de sécurité autorisées et vérifie séparément
le travailleur complet. Il ne remplace pas une recette éditoriale avec Claude réel.

## VIVANT : thèmes demandés (statuts exacts dans CROISEMENT_CLAUDE.md)

| Thème | Correction réelle | Limites |
| --- | --- | --- |
| Pertes de sauvegardes | Révision obligatoire, comparaison sous verrou du compte et transaction, conflit 409, historique chiffré des dix versions précédentes. Une ancienne clé manquante ou un blob corrompu bloque aussi l'écrasement. | Le stockage de l'appareil peut toujours être effacé par son utilisateur/navigateur. Exporter une copie indépendante reste nécessaire. |
| Restaurations et onglets | Journal local écrit avant toute restauration, récupération après interruption et rollback ; `tree:null` efface le précédent arbre pour éviter un mélange de comptes. Les anciens exports carnet restent importables. Écritures périmées et contenus mal formés bloqués ; export brut de secours si nécessaire. | L'export brut `origin-local-recovery-1` demande une récupération contrôlée, pas une réimportation automatique. Le quota peut empêcher une restauration ; les originaux ne sont alors pas remplacés. |
| Droits par produit | Seuls les abonnements/achats associés à une commande vérifiée du même environnement accordent les droits configurés pour ce produit. Statut, échéance et prix de l'abonnement font autorité ; aucune confiance dans `metadata.plan`. | `product_features` est vide dans l'exemple de configuration : cartographie commerciale à valider. Aucun partage familial à distance n'est activé. |
| Événements Stripe | Inbox durable `received`, transaction des effets et de leur validation, rejeu idempotent après échec. Session relue chez Stripe et vérifiée contre commande/client/prix/total. Paiements différés, expiration, abonnements, impayés, remboursements Miroir et contestations traités. Rattachement possible si le webhook devance la réponse Checkout. | Les événements inconnus/historiques sans commande restent ignorés et auditables. Les reprises nécessitent les rejeux Stripe ; pas encore de worker autonome de réconciliation. |
| Désordre Stripe | État courant de l'abonnement relu, annulation terminale non réactivable par événement ancien ; un Miroir remboursé/contesté ne redevient pas payé par un ancien Checkout. | Une contestation gagnée n'accorde pas automatiquement à nouveau les droits. Remboursements complexes d'abonnements et réconciliations manuelles restent à valider. |
| Double encaissement | UUID de commande avant Checkout, réemploi du Checkout ouvert, idempotence Stripe stable, même commande après timeout ambigu. Échéance du Checkout liée à la commande. Abonnement existant géré par le portail. | Les tests simulent le transport Stripe. Une recette Stripe TEST doit confirmer ces contrats avec la version API effective. |
| Débit et proxys | IP issue de `X-Forwarded-For` seulement depuis des IP de proxys explicitement approuvées, chaîne parcourue de droite à gauche. Compteurs atomiques MySQL, limites par IP et compte pour login, `Retry-After`. | Fenêtres fixes, pas limite glissante. Renseigner les vrais proxys Hostinger ; quotas à calibrer avant charge réelle. Ce mécanisme n'est pas une protection DDoS complète. |
| Après résiliation | Lecture, export et versions antérieures accessibles au propriétaire vérifié sans abonnement. Une rétrogradation ne détruit pas l'ancien arbre cloud. | Écriture soumise au droit produit ; la résiliation ne supprime pas le compte ni les données. |
| Chiffrement | Clé Base64 canonique de 32 octets, identifiant de clé, trousseau de rotation, nonce aléatoire et blob lié au compte. Anciennes sauvegardes toujours déchiffrables avec leur clé conservée. | Chiffrement au repos, pas de bout en bout. Les anciens blobs n'étaient pas liés au compte cryptographiquement ; leur ACL SQL reste nécessaire. Ne jamais retirer une clé encore utilisée. |
| Suppression | Confirmation, mot de passe actuel et limitation de débit ; blocage si abonnement non terminé, vérification Stripe avant suppression d'un compte lié, contrôle des paiements ouverts. Cascade des sauvegardes et de l'historique, révocation des sessions. | Pas d'annulation Stripe automatique. Conserver seulement les écritures de paiement nécessaires ; politique légale de conservation à valider. |

La démonstration n'est plus enregistrée à la place du brouillon personnel.
Les simulations de droits cloud restent explicitement limitées à
`mode=test && demo_features_enabled=true`. Elles n'affirment jamais qu'un
abonnement ou un achat réel existe. L'API HTTP de production n'accepte aucun
paramètre permettant d'injecter le transport simulé des tests.

## Variables et accès réellement vérifiés

Le shell cloud accessible ne contient aucune valeur non vide pour
`WEBHOOK_SECRET`, `CODES_SECRET`, `STRIPE_KEY`, `STRIPE_PRICE_CATALOG`,
`STRIPE_MODE`, `ENFORCE_ACCESS`, `ADMIN_KEY`, `OWNER_CODE`,
`ANTHROPIC_API_KEY`, `BREVO_SMTP_KEY`, `EMAIL_DEST`, `ORIGIN_VIVANT_CONFIG`.
Le contexte du processus Python local historique n'était pas lisible.
**Cela ne décrit pas la configuration réellement déployée**, qui n'est pas
accessible. Aucune tentative d'accès au site public ou à son hébergement.

Dans le conteneur PHP de TEST uniquement : clé de chiffrement et secret webhook
éphémères présents ; longueur décodée de la clé vérifiée ; Stripe et SMTP non
configurés. Aucune valeur de secret n'a été affichée ou ajoutée au dépôt.

Prévoir dans le gestionnaire de secrets : secrets aléatoires indépendants,
catalogue `STRIPE_PRICE_CATALOG` approuvé, `STRIPE_MODE=test` pour les essais.
Le catalogue associe les offres existantes à `price_id`, `amount` en centimes
et `currency`, sans tarifs par défaut. `ENFORCE_ACCESS=1` est recommandé pour
refuser aussi les demandes internes sans code/paiement. Les clés ne doivent
jamais être collées dans un rapport, une conversation ou le code client.

## Risques restants avant commercialisation

- Rapport détaillé reçu et rapproché : P2, P3, P5, P7, P8 et P10 ne sont pas entièrement clos. Voir `CROISEMENT_CLAUDE.md`, qui précise aussi les limites Y1–Y3.
- Ni Stripe TEST réel, ni Claude/Brevo réels, ni SMTP, ni Hostinger testés.
- Le moteur historique conserve son compteur Stripe en mémoire, son journal
  temporaire des codes et ses threads de génération : pas encore de réservation
  d'usage durable entre workers, ni file de travaux idempotente. Les correctifs
  Y ne prétendent pas réaliser cette migration.
- L'envoi historique reste destiné à la validation interne ; la livraison
  client automatisée et les URL de livrets privées restent à raccorder.
- Les logs historiques Python peuvent contenir des données de clients ; leur
  politique de minimisation/rétention reste à auditer sans retoucher le moteur.
- Reprise des achats et codes existants, consentement des proches/mineurs,
  partage familial fin et purge des sauvegardes de l'hébergeur à valider.
- Aucune recette humaine indépendante, revue de sécurité externe, charge ou
  audit d'accessibilité complet n'est revendiqué.
