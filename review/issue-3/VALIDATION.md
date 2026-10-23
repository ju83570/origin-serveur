# Issue #3 — Carnet intuitif et Constellation reliée à l’Arbre

Issue : https://github.com/ju83570/origin-serveur/issues/3

Branche : `feat/issue-3-carnet-constellation`, depuis
`f13a3459b41d6be643103d2d998f7abd127dece6` (`fix/audit-final-2026-10-23`).
La PR cible cette branche d’audit, car `main` ne contient pas encore les sources
VIVANT. Cela permet une revue UX ciblée, sans y mélanger les correctifs de sécurité
précédents. Aucune fusion ni publication du site public n’est effectuée.

## Changements concrets

- **Carnet** : CTA « Écrire dans mon Carnet » avant l’historique ; sujet et texte,
  enregistrement explicite, relecture, modification et suppression confirmée.
  Les pages rédigées sont séparées des Miroirs, souvenirs et bilans conservés.
  Le texte d’une page en échec reste dans le formulaire, avec erreur explicite ;
  pas de faux message de succès ni de suppression en mémoire présentée comme acquise.
- **Constellation** : deux sélecteurs des profils personnels de l’Arbre, avec
  prénom et année utile. Le CTA de chaque fiche personnelle transmet seulement
  l’identifiant dans un fragment d’URL : pas de nom/date dans la requête serveur.
  La seconde sélection reste conservée si elle est distincte ; un doublon est
  empêché. Une sélection disparue n’est pas remplacée arbitrairement par un proche.
- **Relation** : parent/enfant, fratrie et partenaires uniquement à partir des
  liens enregistrés ; absence ou contradiction → « Autre lien ». Correction
  explicite possible pour l’exploration, sans modifier les liens de l’Arbre.
  Aucun couple n’est présumé à partir d’un prénom, d’une date ou d’un nombre.
  Le Miroir commence aussi par « Autre lien » pour un nouveau dossier.
- **Source partagée** : `origin-profiles.js` minimise et valide les personnes
  depuis l’unique stockage de l’Arbre. Constellation et Miroir utilisent le même
  composant de sélection. Le Miroir conserve des références aux profils liés et
  suit leurs noms/dates après édition de l’Arbre ; une saisie manuelle détache
  explicitement le champ sans modifier la personne dans l’Arbre.
- **Navigation** : Arbre → fiche → Constellation → Miroir/Carnet et retour à
  l’Arbre ; fragments réouvrables, retour navigateur, commandes au clavier,
  focus sur les titres/formulaires, états vides, démo fictive et saisie manuelle.
- **Données** : champ `pages` optionnel dans le Carnet existant, sans nouvelle
  base de personnes. Archives et métadonnées anciennes sont préservées. Les pages
  survivent au rechargement, aux exports JSON/TXT et à la sauvegarde en ligne
  volontaire existante. Un format de page inconnu bloque l’écriture/restauration,
  sans réinitialisation silencieuse.
- **Import corrigé** : le bouton du Carnet ne reconnaissait que l’ancienne
  enveloppe `origin-vivant-1` alors que l’export utilise `origin-vivant-cloud-2`.
  Il utilise maintenant la restauration commune avec validation préalable,
  contrôle de conflit et journal de récupération. Les deux formats et le Carnet
  brut antérieur restent acceptés. Une sauvegarde complète peut aussi restaurer
  l’Arbre ; l’utilisateur confirme le remplacement avant toute écriture.

Aucun changement du moteur Python, des prompts/calculs/rendus, de l’API PHP,
des paiements, de `origin-commercial.js` ou du transfert Premium commercial.
La seule adaptation Python est l’autorisation du nouveau fichier JS statique dans
la façade locale de test, avec sa même restriction aux API localhost.

## Validation exécutée le 23 octobre 2026

| Suite | Résultat | Portée |
| --- | --- | --- |
| JavaScript Node | 24/24 | Relations, ambiguïtés, choix distincts, profils invalides, dates, lecture sans écriture, migration/exports et restauration avec panne |
| Navigateur Chromium/Playwright | 24/24 | 14 nouveaux tests UX + les 10 tests navigateur existants ; largeurs 320/390/768/1440 px |
| Python | 38/38 | Contrôles d’accès, préservation AST/70 ressources, rendus HTML/PDF, démonstrations et réseau serveur interdit |
| API PHP/MySQL | 40/40 | Suites de non-régression existantes : Stripe simulé, droits, sauvegardes, concurrence et migration |
| Assertions PHP | 42/42 | Politique de paiement, chiffrement/AAD et minimisation ; distinctes des cas de test |
| Syntaxe JavaScript | 4 scripts OK | Application, stockage, profils et script inline de l’Arbre |

Total : **126 cas de test réussis, aucun échec ni test ignoré final**, plus
42 assertions PHP. Les noms et résultats sont sous [evidence/](evidence/).
Les suites API et navigateur utilisent exclusivement la stack locale fictive ;
aucun appel Stripe/Claude/Brevo réel et aucun email livré. Le test de sauvegarde
chiffrée navigateur inclut maintenant une page rédigée et vérifie sa restauration.

Le premier test d’import a été renforcé pour effacer réellement la copie locale
avant restauration : retrouver une page qui était encore présente n’aurait pas
prouvé l’import. Les assertions de sélection attendent l’affichage de la nouvelle
vue après navigation et lisent la propriété native `disabled` des options.
Une incohérence initiale de forme du résultat « relation inconnue » a également
été corrigée. Les chiffres ci-dessus concernent les exécutions finales uniquement.

Commandes, depuis l’environnement cloud préparé (adapter le chemin du venv) :

```bash
node --test tests/js/*.test.cjs
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests/integration -v
XDG_CACHE_HOME=/workspace/.cache PYTHONDONTWRITEBYTECODE=1 \
  /workspace/.venvs/origin-serveur/bin/python -m unittest discover -s tests/browser -v
docker exec origin-vivant-api-test php /tests/policy.php
```

La façade locale et la stack Docker doivent être démarrées suivant le README.
Exécuter les suites API et navigateur successivement : elles utilisent la même
base jetable. Ne jamais pointer ces suites vers une base cliente ou la production.
Les tests de l’issue seuls se lancent aussi avec `python tests/browser/test_issue3_ux.py`.

## Captures et contrôle visuel

Toutes les personnes, dates adultes et pages des nouvelles fixtures/captures
sont **inventées**, avec la mention « Exemple » ou « fictive ». Aucune photo,
date réelle de mineur, souvenir client ou donnée familiale réelle n’est utilisée.

- [Carnet mobile](screenshots/carnet-mobile.png)
- [Fiche de l’Arbre et accès Constellation sur mobile](screenshots/arbre-fiche-mobile.png)
- [Constellation mobile](screenshots/constellation-mobile.png)
- [Constellation ordinateur](screenshots/constellation-desktop.png)

Captures générées depuis les vraies sources de la façade locale, sans requêtes
navigateur externes ; inspection visuelle ponctuelle effectuée. Elles ne sont pas
issues d’un second prototype HTML. `demo-visual/` n’est pas régénéré dans cette PR.

## Limites avant ouverture publique

- Le pack V3 mentionné par l’issue n’est pas disponible dans les fichiers accessibles
  (seul le pack V2 fourni est présent). Aucun rapprochement V3 n’est donc prétendu.
  Les améliorations partent des sources officielles de la branche d’audit.
- Le test mobile écrit une page en moins d’une minute **par automatisation** ;
  ce n’est pas une mesure d’utilisabilité chez un nouvel utilisateur humain.
  Pas de recette Safari/iOS physique, lecteur d’écran ou audit WCAG exhaustif.
- Stockage local non chiffré, sans synchronisation automatique entre appareils.
  Sauvegarde en ligne uniquement à la demande, avec les conditions/droits existants.
  Une saisie non enregistrée doit être copiée avant de recharger en cas de panne ;
  l’avertissement de sortie ne remplace pas une sauvegarde.
- Limites existantes conservées : 300 pages par collection, 70 personnes,
  4 000 caractères par page, import du Carnet de 3 Mo maximum. Les photos volumineuses
  d’un export complet peuvent dépasser cette limite ou celle du cloud ; aucun
  contenu n’est tronqué pour forcer l’import. Prévoir une recette spécifique des
  grosses sauvegardes avec photos avant commercialisation.
- Pas de visite/recette sur Hostinger réel ni déploiement. Les points ouverts de
  sécurité et de génération durable de l’audit précédent restent documentés dans
  `review/final-2026-10-23/` et ne sont pas présentés comme résolus par cette PR UX.
