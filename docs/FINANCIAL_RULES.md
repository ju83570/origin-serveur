# Règles appliquées par les correctifs financiers

Ces règles conservatrices sont testées localement. Leur mise en production
reste soumise à validation commerciale et aux essais Stripe TEST réels.

- Un événement signé est seulement reçu et stocké durablement par HTTP.
  Aucun droit, appel Stripe ou travail Python n'est exécuté dans la requête.
- Le worker relit les ressources Stripe hors transaction SQL. Il applique
  ensuite les effets et la validation de l'inbox dans une transaction courte,
  protégée par un bail avec jeton. Un worker périmé ne peut rien valider.
- Commande, ligne et tentative de paiement sont créées côté serveur. Aucun
  produit, prix, total ou bénéficiaire ne vient du formulaire ou d'une simple
  métadonnée Stripe. Les anciens achats restent des archives sans autorité.
- Un paiement différé non payé n'accorde aucun droit. Échec ou expiration ne
  retire jamais un paiement déjà confirmé. Un succès ultérieur est rapproché.
- Tout remboursement, même partiel, retire l'accès à l'achat concerné ; le
  montant remboursé est monotone. Une reprise exceptionnelle est manuelle.
  Une charge de renouvellement est rapprochée par sa facture et son abonnement,
  même si son PaymentIntent n'est pas celui du Checkout initial. Son ajustement
  est conservé séparément ; le remboursement bloque conservativement la commande
  d'abonnement. La création de commandes par échéance et la réactivation après
  remboursement ne sont pas implémentées.
- Un litige ouvert, des fonds retirés ou une perte suspendent les droits.
  Un litige gagné peut les rétablir uniquement si la charge courante est payée,
  non remboursée et qu'aucun autre litige bloquant n'existe. Les événements
  anciens ne réactivent pas un abonnement annulé ou un achat remboursé.
- La période, le statut et le prix courants d'un abonnement font autorité.
  Un changement de prix/produit hors commande vérifiée suspend les droits
  jusqu'au rapprochement ; il ne donne jamais les droits d'une autre offre.
- Un double clic ou un timeout ambigu réutilise la commande, la tentative et
  les clés d'idempotence. Une préparation déjà louée renvoie 409 et Retry-After.
- La suppression du compte efface les données familiales et les droits,
  détache les commandes du compte et conserve les écritures financières sans
  email ni nom. Les références Stripe sont pseudonymes, pas totalement anonymes.
  Les remboursements et litiges ultérieurs continuent de mettre à jour le registre
  financier après suppression, sans recréer le compte ni ses droits. La durée
  légale de conservation et la purge finale restent à faire valider ; aucune
  suppression automatique des pièces financières n'est activée.
- Les tables de jobs/outbox ne déclenchent aucune génération ni livraison
  dans cette phase. Aucun nouvel abonnement, tarif ou SKU n'est activé.
