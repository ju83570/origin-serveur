# RACINE 2.0 — Feuille de route commune

**État : cadrage actif — aucune fonction nouvelle déclarée en production.**  
**Pilotage :** propriétaire ORIGIN valide le produit, les budgets et toute mise en production ; Claude Code et ChatGPT peuvent contribuer via les mêmes issues et PR GitHub.  
**Mission mère :** https://github.com/ju83570/origin-serveur/issues/5

## 1. Proposition de valeur

**ORIGIN** est le point de départ : un livret personnalisé conçu à partir des informations disponibles. **RACINE** prolonge cette expérience avec un espace privé, vivant et transmissible où la famille peut, selon ses autorisations, enrichir son arbre, ses souvenirs, documents, témoignages et chronologies.

On ne vend pas une vérité cachée révélée par des nombres. On aide les familles à conserver des traces, à poser des questions, à explorer des correspondances vérifiables et à transmettre leur histoire.

### Les règles de vérité

- **Fait documenté** : associé à une source, avec sa date et son degré de certitude.
- **Témoignage familial** : attribué à une personne contributrice, sans devenir automatiquement un fait établi.
- **Hypothèse** : explicitement révisable.
- **Lecture symbolique** (numérologie/astrologie) : distincte des faits et jamais diagnostique ou causale.
- **Information inconnue** : affichée comme inconnue; ne jamais inventer pour combler un blanc.

## 2. Expérience cible en 7 gestes

1. Le client accède à son **livret exact** et à son arbre via un espace privé.
2. Il touche une personne de l'arbre pour ouvrir sa **fiche vivante**.
3. Il consulte ses liens, une **frise de vie** et les sources accessibles.
4. Il ajoute une photo, un événement, un souvenir ou, plus tard, un message audio.
5. Le système enregistre la contribution, l'auteur, la date, le degré de visibilité et l'historique.
6. Il invite, avec consentement, un proche autorisé à compléter des souvenirs.
7. Il peut transmettre ou exporter ce patrimoine numérique de manière lisible et pérenne.

Le livret existant reste la photographie éditoriale de la commande initiale; l'ajout d'un souvenir ne réécrit pas magiquement son PDF.

## 3. Missions et ordre strict

| Ordre | Mission GitHub | Objectif et critère de sortie |
|---|---|---|
| P0 | [#6](https://github.com/ju83570/origin-serveur/issues/6) | Audit vérifié, risques et sauvegardes; aucune modification de production |
| P1a | [#7](https://github.com/ju83570/origin-serveur/issues/7) | Schéma multi-familles privé + migrations et tests d'isolation |
| P1b | [#8](https://github.com/ju83570/origin-serveur/issues/8) | Une fiche avec photo/souvenir sauvegardés **côté serveur** et retrouvés sur un autre appareil |
| P2 | [#9](https://github.com/ju83570/origin-serveur/issues/9) | Invitation et contribution d'un proche autorisé, sans fuite entre familles |
| P3 | [#10](https://github.com/ju83570/origin-serveur/issues/10) | Chronologies, correspondances sourcées et export complet |
| P4 | [#11](https://github.com/ju83570/origin-serveur/issues/11) | Recette pilote, coûts, retour arrière et décision explicite de lancement |

**Première démonstration sérieuse :** sur téléphone, un utilisateur autorisé ouvre la fiche d'une personne fictive, ajoute un souvenir et une photo, recharge sur un autre appareil et retrouve sa contribution. Test de lecture/écriture refusée depuis une seconde famille. Ceci ne doit pas être une simple sauvegarde `localStorage`.

## 4. Détails non négociables

- **Aucune interruption** des parcours ORIGIN existants (paiement, formulaire, production et livraison du PDF).
- **Aucune donnée personnelle réelle** et aucun secret dans ce dépôt actuellement public; les démos utilisent des données fictives cohérentes.
- Stockage privé des médias; authentification/autorisations **côté serveur** et isolation stricte des familles.
- Permissions pour administrateur/contributeur/lecteur; accès personnel et révocable; notes privées par défaut.
- Filiation et situations familiales diverses, dates inconnues ou approximatives, personnes décédées et mineurs pris en compte sans supposition.
- Sauvegarde, restauration, export et suppression à tester; historique des modifications; gestion des conflits.
- Ne jamais affirmer qu'un module est en ligne sans test de bout en bout sur l'environnement visé.
- Phase 1 de protection = privée avec fichiers fictifs, avant toute invitation de familles réelles.

## 5. Architecture : décisions à prendre après audit

Conserver la séparation du front Hostinger et du moteur Python Render si elle reste justifiée. Ne pas imposer une base de données ni une refonte sans état des lieux. Prévoir :
- API d'accès à chaque famille avec contrôle du droit serveur.
- Modèle versionné `family/person/relationship/event/source/contribution/media/permission/revision`.
- Identifiants techniques stables, journaux sans informations sensibles, sauvegardes et tests de restauration.
- Contenus des clients distincts des fichiers du site et des ressources publiques.
- Structure modulaire : éviter toute nouvelle fonctionnalité majeure dans le monolithe existant avant justification.

## 6. Gouvernance et collaboration

- **Une mission = une issue = une branche/PR de portée limitée**. Le nom `feature/racine-vivant-v2` est un espace de préparation; ne pas travailler directement sur `main`.
- Claude Code et ChatGPT peuvent relire issues, docs, commits et PR. Ce ne sont pas des agents connectés en conversation temps réel : les commentaires GitHub sont la trace partagée.
- Pour chaque livraison : résumé, fichiers modifiés, tests effectués et preuves, risques, procédure de retour arrière.
- On ne fusionne pas un module dans `main` et on ne le déploie pas sans validation explicite.
- En cas de doute ou de contradiction entre la documentation et le serveur, privilégier l'état **réellement constaté** et demander une décision.

## 7. Critères d'excellence ORIGIN

**Émotion** : l'expérience doit donner envie de raconter une histoire et retrouver un proche.  
**Confiance** : le client sait ce qui est factuel, raconté ou symbolique.  
**Simplicité** : lisible et utilisable au doigt, particulièrement sur Android.  
**Transmission** : les données ne sont pas enfermées dans un format opaque.  
**Sécurité** : on ne doit jamais accéder à la famille d'autrui, même en changeant une URL.  
**Réalisme économique** : estimer l'hébergement, le stockage, les sauvegardes et le support avant de promettre une conservation indéfinie.

## 8. Hors périmètre du premier jalon

- Recherche automatisée exhaustive d'archives ou collecte de données sans autorisation.
- Diagnostic familial, « secrets » révélés, transmissions de traumatismes affirmées.
- IA qui invente des mémoires ou dialogue au nom de proches décédés.
- Abonnement, nouveaux tarifs, marketing annonçant une disponibilité non constatée.
- Publication de photos d'enfants ou de souvenirs privés dans une démo publique.

**Référence de départ** : cahier des charges RACINE du 29/10/2026; vérifier les fichiers réels avant implémentation.
