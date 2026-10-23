# ORIGIN — corrections finales du 23 octobre 2026

Le code est corrigé sur `fix/audit-final-2026-10-23`, depuis
`dddceecfc7ae77115968c87c2f3f4ce8c5feda86`. Aucun merge dans `main`, aucune
intervention sur le site public et aucun déploiement Hostinger n'ont été faits.
Le partage de la branche sert uniquement à la revue et au téléchargement.

**Validation locale : 98 tests réussis, zéro échec et zéro test ignoré dans les
dernières exécutions, plus 42 assertions PHP réussies.** Ce résultat ne vaut pas
recette Stripe/SMTP/Hostinger ni validation indépendante par Claude.

1. [CORRECTIONS.md](CORRECTIONS.md) : statut P1–P10, changements Python et limites.
2. [VALIDATION.md](VALIDATION.md) et [evidence/](evidence/) : commandes et preuves.
3. [EXPLOITATION_TEST.md](EXPLOITATION_TEST.md) : migration, clés et worker privé.
4. [INVENTAIRE.md](INVENTAIRE.md) et `inventory.json` : fichiers de cette phase.
5. `premium-security.diff` : les seules lignes modifiées dans `app.py` depuis
   le rapprochement documentaire du 22 octobre.

Le rapport original de Claude reste intact dans
[../audit-followup/REVUE_CLAUDE_ORIGIN_2026-10-22.md](../audit-followup/REVUE_CLAUDE_ORIGIN_2026-10-22.md).
Il concernait la version initiale `f2b1500`/`32d6b68`, pas ces correctifs.
Les recommandations jointes sont des éléments d'audit ; seule la demande du
propriétaire autorise le périmètre de modification. Aucune notice du pack ne
constitue une autorisation de déploiement.

## Résultat utilisable

Les comptes et sauvegardes fonctionnent dans la stack locale isolée. Le Miroir,
l'arbre et le parcours gratuit vers les rendus de démonstration restent utilisables
sans clés. Après extraction, ouvrir `demo-visual/index.html` suivant
`demo-visual/LIRE_AVANT.txt`, ou démarrer la façade locale du README.
Les PDF de démonstration sont de vrais PDF avec des textes fictifs explicites.
Les pages et les ressources commerciales existantes n'ont pas été réécrites.

Stripe est simulé uniquement par les tests CLI privés. L'API HTTP locale garde
les paiements désactivés et aucune clé Stripe fictive n'est enregistrée dans sa
configuration. Le nouveau worker financier rapproche les événements mais ne
génère aucun livret et n'envoie aucun email. Jobs et outbox préparent le contrat
futur ; aucun dispatcher de génération/livraison n'est activé.

## Conditions avant commercialisation

- Relire les correctifs et approuver les règles conservatrices de remboursement
  et de litige dans [../../docs/FINANCIAL_RULES.md](../../docs/FINANCIAL_RULES.md).
- Tester la migration et le rapprochement des droits historiques sur une copie
  dédiée ; aucune conversion aveugle des anciens achats n'est fournie.
- Recetter un paiement Stripe TEST, ses événements et les relances avec la
  vraie version d'API du compte, puis SMTP et HTTPS sur une préproduction autorisée.
- Résoudre la consommation durable côté moteur historique : paiements en mémoire,
  codes cadeaux dans `/tmp`. Valider le contrat privé d'un seul job Solo durable
  depuis PHP, sans créer un second registre de commandes dans Python.

La configuration réellement déployée n'est pas accessible. Les secrets de
production, clés anciennes de sauvegarde et bases clients ne sont pas dans ce
dossier. Ne pas présenter cette archive comme une version déjà déployée ou
immédiatement prête à encaisser en production.

## Archive

`tools/export_review.py` produit, depuis un commit propre, un ZIP contrôlé avec
`EXPORT_MANIFEST.json` et `EXPORT_SECURITY.json` dans ce dossier. Chaque fichier
du projet y est issu d'un blob Git ; ni historique Git, `.env` réel, configuration
privée, base, session, volume ou sortie client d'exécution n'est parcouru.
Le contrôle des motifs de clés complète ce périmètre sans être une certification
de sécurité exhaustive. Les fixtures contiennent uniquement des exemples fictifs.

Le ZIP GitHub du commit partagé contient les mêmes fichiers suivis, avec une
racine et une compression propres à GitHub ; les deux métadonnées générées par
l'export local n'y figurent pas. Ne pas comparer son empreinte à celle du ZIP
local. Le lien GitHub doit être ouvert avec un compte autorisé à ce dépôt privé.
