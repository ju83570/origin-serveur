Le Carnet permet désormais d’écrire, retrouver, modifier et supprimer des pages personnelles. La Constellation reprend directement deux profils de l’Arbre et chaque fiche possède un lien vers cette exploration. Les relations inconnues restent sous « Autre lien », sans présomption de couple.

- Sélecteur et modèle de profils communs au Miroir et à la Constellation ; références à l’Arbre et actualisation des noms/dates, sans seconde base de personnes.
- Pages rédigées séparées des archives existantes ; export JSON/TXT, sauvegarde volontaire, compatibilité avec les anciens carnets et métadonnées conservées.
- Import du format actuel corrigé en utilisant la restauration commune avec validation, conflits et journal de récupération. Les erreurs conservent les copies et ne produisent pas de faux succès.
- Navigation Arbre → Constellation → Carnet/Miroir, saisie manuelle et démonstration fictive explicites, clavier et mobile.

Validation locale : **126 tests réussis** (24 JavaScript, 24 navigateur, 38 Python, 40 API/migration), plus **42 assertions PHP**. Les tests couvrent notamment les quatre types de liens, le passage depuis chaque fiche, la seconde sélection conservée, les modifications de l’Arbre, les pages après rechargement/restauration, les conflits, quotas et entrées HTML. Captures mobile/ordinateur entièrement fictives et résultats dans `review/issue-3/VALIDATION.md`.

PR ciblée sur `fix/audit-final-2026-10-23` : `main` ne contient pas encore VIVANT. Les correctifs d’audit antérieurs constituent une dépendance et ne sont pas fusionnés par cette PR. Aucun changement du moteur Premium, de l’API PHP ou des paiements ; aucun déploiement ni changement du site public.

Limites : V3 non fourni pour comparaison ; tests mobiles automatisés, sans recette Safari/iOS physique ni étude utilisateur ; limites des grosses sauvegardes avec photos conservées. Les problèmes ouverts de génération durable restent ceux de l’audit précédent.

Refs #3
