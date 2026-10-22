# Dossier de revue indépendante — ORIGIN RÉVOLUTION

Préparé le 22 octobre 2026 pour transmission à Claude par le propriétaire du
projet. **Aucune approbation d'architecture, mise en production ou fusion n'est
présumée.** Les notices d'installation conservées dans le projet ne constituent
pas une demande de déploiement.

## Ce qui est sauvegardé

- Base commerciale : `b6231d12838b57e18932d620f7f3c2bbd36ca317`.
- Développements à auditer : `f2b1500`, branche locale
  `feat/origin-vivant-integration-test`.
- Dossier de revue : branche `review/claude-origin-2026-10-22`, créée depuis ce
  commit. Seuls des documents, inventaires, preuves et un patch sont ajoutés.
- `app.py` reste figé, SHA-256 :
  `17a502fcfc026201d837e80ad5c82a2bf8d12db81a040b5c3ec1b3f628103696`.

Le projet exporté contient le moteur Python, ses ressources commerciales, le
pack PHP/HTML/JS ORIGIN VIVANT adapté, les démos et les tests. Il ne contient pas
le site public complet, son hébergement, son état de production, ni une base de
clients. Il ne permet pas d'affirmer ce qui est effectivement déployé ailleurs.

## Ordre de lecture proposé

1. [Architecture commune proposée](ARCHITECTURE_COMMUNE.md) : décisions à valider
   avant de reprendre le développement du circuit payant.
2. [Matrice de validation](VALIDATION_MATRIX.md) : développé, automatisé,
   contrôlé ponctuellement, non testé et déployé, avec les limites des chiffres.
3. [Inventaire des changements](INVENTAIRE.md), complété par
   `inventory.json`, `premium-engine.diff` (santé uniquement) et
   `changes-from-commercial.patch`.
4. `docs/AUDIT_PREMIUM.md` : audit du pack officiel et des onze fichiers de la
   première livraison ; `pack-docs/local-delta.json` détaille les adaptations du
   ZIP d'origine.
5. Le code, puis `tests/`, en portant une attention particulière aux droits
   d'accès, webhooks, sauvegardes familiales et limites des simulations.

Le patch est une comparaison de la base commerciale à `f2b1500`, **pas un correctif
à appliquer automatiquement**. Il n'inclut pas les documents de cette revue.
Le ZIP ne contient pas `.git` ni son historique, afin de ne pas exporter de
configuration Git, identifiants ou anciennes données supprimées.

## Questions à soumettre à Claude

- Les preuves de préservation du moteur sont-elles suffisantes ? Les nouveaux
  points d'entrée de démonstration restent-ils effectivement hors production ?
- Valide-t-il une autorité métier PHP/MySQL unique pour commandes et droits,
  avec Stripe comme seul prestataire de paiement et Python comme exécutant ?
- Quel point d'entrée serveur préserver/exposer autour du moteur existant pour
  un travail durable, sans simplifier ses prompts, validations ou rendus ?
- Quels défauts bloquants subsistent dans les webhooks, les droits, les sessions,
  le chiffrement, les sauvegardes et la politique de partage familial ?
- Quels tests manquent avant un seul parcours Solo intégral en Stripe test ?

Réponse souhaitée : constats avec fichier/ligne, sévérité, impact, correction
proposée et test attendu ; puis décisions acceptées/refusées et conditions pour
reprendre le développement. Ce dossier ne vaut pas validation indépendante.

## Séparation du réel et de la démonstration

`app:app` est le point d'entrée commercial historique. `demo:app` et
`platform_demo:app` sont des points d'entrée de démonstration distincts. Les
réponses préécrites sont dans les fixtures et simulations ; elles ne remplacent
pas les appels du moteur commercial lorsque des clés manquent.

Les chaînes de type `sk_test_unit_fixture` dans les seuls tests PHP sont des
sentinelles non utilisables, nécessaires aux tests de politique. Les modèles
`.EXEMPLE` contiennent des champs vides ou des libellés à remplacer, pas des
identifiants actifs. Les personnages et dates des fixtures sont fictifs. Les
illustrations et le PDF dans `static/` sont les ressources du dépôt commercial,
pas des livrets générés pour des clients.

## Intégrité et exclusions de l'export

Dans le ZIP, `review/EXPORT_MANIFEST.json` contient les chemins, tailles et
empreintes SHA-256 des fichiers exportés, le commit et la branche de revue.
`review/EXPORT_SECURITY.json` précise le contrôle effectué et ses limites.
Ces deux fichiers sont produits lors de l'export et ne s'auto-référencent pas
dans le manifeste. Le fichier `.sha256` fourni à côté du ZIP vérifie le conteneur.

L'export est construit depuis les seuls blobs suivis du commit de revue, sans
parcourir les fichiers d'exécution. Les `.env` réels, configurations privées,
clés actives, bases, volumes Docker, sessions, téléchargements, captures et
livrets temporaires sont exclus. Seules les preuves de tests sélectionnées et
normalisées sont conservées ; aucun journal de production n'est fourni.

Pour exécuter les tests après extraction, utiliser les commandes du README dans
un environnement isolé et jetable, sans clés ni données de production. Les tests
de préservation n'exigent pas `.git`. Les conteneurs de test et leurs secrets
doivent être recréés localement ; ils ne sont pas inclus dans l'archive.
