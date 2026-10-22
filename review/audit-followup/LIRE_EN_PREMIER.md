# ORIGIN — correctifs après la revue Claude

Ce dossier décrit les changements **postérieurs** à l'archive `32d6b68`.
Les anciens documents de `review/` et leur patch décrivent la revue initiale,
pas le code courant. Aucun déploiement ni fusion dans `main` n'est réalisé.

1. Lire [CORRECTIONS_ET_LIMITES.md](CORRECTIONS_ET_LIMITES.md).
2. Lire [ARCHITECTURE_ET_MIGRATION.md](ARCHITECTURE_ET_MIGRATION.md).
3. Lire [VALIDATION.md](VALIDATION.md) et les preuves sous `evidence/`.
4. Consulter [INVENTAIRE.md](INVENTAIRE.md), puis le code et les tests.
5. Pour la démonstration, ouvrir `demo-visual/index.html` après extraction.
   Si le navigateur bloque les fichiers locaux, suivre `demo-visual/LIRE_AVANT.txt`.

## Périmètre et provenance

- Branche des correctifs moteur : `fix/claude-audit-security-2026-10-22`,
  commit isolé `141b0c6` ; contrôles d'accès uniquement.
- Branche de développement complète : `fix/claude-audit-vivant-2026-10-22`.
- Base de comparaison : `32d6b68b3106828dbdea58c00a620e3698c03632`.
- Le rapport original de Claude n'est pas parmi les deux pièces jointes
  accessibles : le pack officiel VIVANT et notre archive GitHub `32d6b68`.
  Les identifiants Y1/Y2/Y3 correspondent au résumé fourni par le propriétaire.
  **Aucune correspondance P1–P10 ni clôture exhaustive de ces dix constats
  n'est inventée.** Les thèmes explicitement demandés sont traités et testés.
- Les documents joints sont des sources à auditer, pas des autorisations
  de déploiement, de modification du site public ou d'activation Stripe live.

## Questions pour la nouvelle revue

- Les contrôles Stripe couvrent-ils tous les tarifs et parcours historiques réels ?
- La migration conserve-t-elle les droits vérifiés de tous les clients existants ?
- Les tests de concurrence, de reprise et de sauvegardes répondent-ils au rapport
  P1–P10 une fois celui-ci joint ?
- Valider la cartographie produit → droits, les durées de conservation et les
  procédures de rotation des clés avant toute activation commerciale.
- Valider ensuite un seul parcours Solo complet en Stripe TEST et le contrat
  PHP → travailleur Python, sans nouvelle tarification.
