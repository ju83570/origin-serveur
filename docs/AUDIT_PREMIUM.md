# Audit ORIGIN RÉVOLUTION — intégration premium

Date : 22 octobre 2026. Branche : `feat/origin-vivant-integration-test`.
Base commerciale : `b6231d12838b57e18932d620f7f3c2bbd36ca317`.

## Périmètre et méthode

L'archive officielle comporte **17 fichiers**, 1 695 285 octets décompressés.
Son SHA-256 est
`13bee11c0429c4eb3c792da371149e77d2f5ad1ad59190def8deb555eaf18d9c`.
Les chemins, types, CRC, encodages des textes et images ont été vérifiés avant
installation. Aucun lien symbolique ou chemin sortant du répertoire d'extraction.
Les notices, HTML, JavaScript, CSS, PHP et SQL ont été inspectés ; le PNG a été
décodé et vérifié. Les ressources embarquées sont conservées.

Les notices du ZIP sont des documents d'installation, **pas une autorisation de
déploiement**. Aucune de leurs instructions d'upload sur le site public n'a été
exécutée. Les fichiers originaux sont décrits par leurs empreintes dans
`pack-docs/archive-manifest.json` ; `pack-docs/local-delta.json` trace les neuf
adaptations et les huit copies identiques. L'archive d'origine est préservée.

## Inventaire intégral du pack

| Fichier original | Fonction et constat |
| --- | --- |
| `LISEZ_MOI_EN_PREMIER.txt` | Statut de préproduction, fonctionnalités et limites annoncées ; conservé |
| `INSTALLATION_COMMERCIALE_V2.txt` | PHP 8.3, extensions, base dédiée, config privée, mail et Stripe ; non exécuté sur Hostinger |
| `config-exemple/origin-vivant-config.php.EXEMPLE` | Modèle, sans clé Stripe ; conservé hors racine web |
| `vivant/.htaccess` | Pas d'index de répertoire, en-têtes, protection SQL/logs ; conservé |
| `vivant/CGV_A_COMPLETER_AVANT_LANCEMENT.txt` | Checklist juridique, aucune CGV finale ; conservée |
| `vivant/INSTALLATION_HOSTINGER.txt` | Notice ancienne renvoyant vers la V2 ; conservée |
| `vivant/api/.htaccess` | Protection des fichiers internes ; complétée pour la nouvelle politique de paiement |
| `vivant/api/bootstrap.php` | PDO, sessions, CSRF, chiffrement Sodium, SMTP STARTTLS, accès Stripe, droits ; adapté |
| `vivant/api/index.php` | Comptes, vérification mail, récupération, sauvegarde, checkout, portail, webhooks ; adapté |
| `vivant/api/schema.sql` | Huit tables InnoDB, clés étrangères, index ; ajout de la version des sessions |
| `vivant/arbre-vivant.html` | Arbre local interactif, proches, photos, récits, liens, import/export ; réutilisé et corrigé |
| `vivant/confidentialite.html` | Document de travail à compléter ; conservé, non déclaré conforme ou prêt à publier |
| `vivant/index.html` | Miroir, souvenirs, carnet, parcours, dialogues ; ajout de la vue Mes livrets |
| `vivant/logo-origin-officiel.png` | Image officielle conservée à l'identique |
| `vivant/origin-commercial.js` | Espace client, connexion, récupération, cloud, portail et abonnement individuel ; réutilisé |
| `vivant/origin-vivant.css` | Charte noir/or/crème et règles responsive ; conservées, ajouts ciblés |
| `vivant/origin-vivant.js` | Miroir guidé, consentement de la seconde personne, suivi local et exports ; conservé, démo isolée |

## Audit des onze fichiers de la première livraison

Le dépôt contenait les **onze fichiers concernés**, plus `docs/VALIDATION.md`,
rapport ajouté ensuite. Ils ont tous été vérifiés ; aucun travail préexistant
n'a été écrasé par un reset ou une nouvelle extraction.

| Fichier | Impact sur le moteur commercial |
| --- | --- |
| `app.py` | Seules modifications historiques : `/health` répond sans clés et `/ready` décrit leur présence. Aucun calcul, prompt ou traitement de livret modifié |
| `.gitignore` | Ignore les sorties locales ; complété pour ne pas versionner des configurations secrètes |
| `README.md` | Instructions ; aucune exécution automatique en production |
| `demo.py` | Point d'entrée séparé ; copie du moteur par requête, calculs/rendus réels, prestataires simulés |
| `demo_support.py` | Réponses préécrites et blocage réseau limités à la démo et aux tests ; jamais importé par `app:app` |
| `docs/INTEGRATION.md` | Dossier d'architecture, actualisé après réception du pack |
| `fixtures/demo_narrative.json` | Textes fictifs explicitement réservés à la démonstration |
| `requirements-demo.txt` | Exigence WeasyPrint 70 de la démo ; `requirements.txt` original inchangé |
| `templates/demo.html` | Formulaire de démonstration ; ajout d'une reprise consentie de prénoms/dates, sans inférer genre/ville |
| `templates/demo_result.html` | Affichage des artefacts de démonstration, sans livraison réelle |
| `tests/test_origin.py` | Tests avec réseau bloqué, aucun remplacement des appels en production |

`docs/VALIDATION.md` reste le compte rendu de cette première étape ; les nouveaux
résultats figurent dans `docs/VALIDATION_PREMIUM.md`.

### Preuve de protection du cœur

`fixtures/engine-preservation.json` est calculé à partir de la base commerciale.
Un test compare l'arbre syntaxique **intégral** de `app.py`, hormis les deux
fonctions de santé explicitement autorisées. Cela couvre les constantes,
prompts, calculs, orchestrations, contrôles, personnalisations et générateurs.
Un deuxième test compare les empreintes des **70 autres fichiers historiques**,
dont `requirements.txt`, les images et le PDF bonus. Les deux contrôles passent.

Les tests rendent aussi les HTML/PDF Solo, Couple, Famille, Prestige, Naissance
et Vocation avec des données de test. Ils ne prouvent pas la qualité d'une
nouvelle réponse Claude ni la livraison distante : ces opérations restent
séparées de la démonstration et nécessitent des accès réels autorisés.

## Composants déjà présents, réutilisés

- **Miroir des Liens** : relation, sujet, ressenti et besoin déclarés, dialogue
  volontaire de la deuxième personne, lecture guidée et gestes concrets. Les
  textes sont locaux et annoncés comme symboliques, pas comme une analyse Claude.
- **Arbre familial vivant** : proches, générations, photos réduites, souvenirs,
  liens de parenté, import/export, rapprochement local avec le Miroir.
- **Expériences** : souvenirs distinguant vécu/récit/hypothèse, parcours de 90 jours,
  20 questions tournantes, sept rituels, bilan quotidien. Il ne s'agit pas de 90
  contenus distincts ni d'un accompagnement humain automatisé.
- **Espace client** : comptes, mots de passe hachés, confirmation mail, sessions
  Secure/HttpOnly/SameSite, CSRF, récupération et suppression de compte côté API.
- **Commerce** : droits d'abonnement, achat Miroir, portail, checkout et événements
  Stripe. L'interface du pack propose seulement l'abonnement individuel ; les
  offres Famille/Miroir restent conditionnées à leur livraison effective.

## Défauts identifiés et corrections isolées

| Constat initial | Correction et preuve |
| --- | --- |
| Checkout interdit tant que `mode != production` ; impossible de tester avant ouverture | Mode `test` explicite, `test_payments_enabled`, clé `sk_test_` exigée ; politique testée sans appel Stripe |
| Anciens drapeaux suffisants pour activer le live | Approbation `live_payments_approved` supplémentaire, absente/false dans cet environnement ; clés/événements live rejetés en test |
| Anti-rejeu webhook non transactionnel | Insertion de l'événement et effets SQL dans la même transaction ; test de doublon et d'échec suivi d'un rejeu |
| Réinitialiser le mot de passe laissait les sessions ouvertes | Version de session par utilisateur, incrément au changement ; ancienne session rejetée en test HTTP |
| Deux utilisations simultanées possibles du jeton de récupération | Lecture du jeton sous verrou SQL avant consommation ; deuxième utilisation rejetée |
| Confiance implicite dans `X-Forwarded-Proto` | En-tête utilisé uniquement depuis une adresse de proxy explicitement autorisée |
| Arbre absent de la sauvegarde cloud | Enveloppe `origin-vivant-cloud-2`, carnet + arbre personnel, accord explicite et anciens carnets compatibles |
| Objets JSON vides transformés en tableaux | Sérialisation préservant les types JSON ; aller-retour PHP/MySQL testé |
| Chiffrement illisible assimilé à une absence de sauvegarde | Erreur explicite, aucune restauration silencieuse d'un état vide |
| Restauration navigateur pouvant être partielle après dépassement de quota | Rétablissement des valeurs précédentes si l'une des écritures échoue |
| Date d'arbre acceptant des jours inexistants | Vérification jour/mois/année exacte, sans changer la numérologie |
| Identifiants spéciaux d'import risquant d'altérer les objets JS | Identifiants réservés rejetés, dictionnaire de positions sans prototype |
| Modifier une fiche fictive rendait tout l'arbre prétendument personnel | Démarrage d'un arbre personnel vide ; la démonstration reste identifiable |
| Modifier un champ du Miroir fictif mélangeait les réponses fictives aux saisies personnelles | Démo en lecture seule ; nouvelle relation pour commencer une saisie personnelle |

## Dépendances et limites restantes

Le front du pack n'a aucune dépendance npm ni appel à une IA externe. Il utilise
les API du navigateur, `localStorage` non chiffré et des ressources locales. Les
liens vers le site public sont conservés comme liens ; aucun test ne les suit.
Le backend cible PHP **8.3+**, PDO MySQL, sodium, mbstring, curl et openssl ; le
schéma cible MySQL/InnoDB. Les contrôles locaux utilisent PHP 8.3 et MariaDB 11.4,
pas les services du compte Hostinger. Le moteur Python reste un service distinct.

Les points suivants empêchent encore une déclaration de disponibilité commerciale :

1. Aucun paiement Stripe distant ni email SMTP/transactionnel réel testé. Les
   événements locaux sont des fixtures signées de test, pas des achats Stripe.
2. Pas de livraison payante durable et idempotente reliant une commande PHP à un
   travail Python ; le webhook Python historique utilise toujours des threads.
3. Abonnements : ordre des événements, rapprochement périodique, remboursements,
   contestations, annulations et consommation des droits d'achat à finaliser.
4. Aucun partage inter-comptes ni invitations familiales à distance ; conserver
   `family_ready=false` et `mirror_paid_ready=false` tant que non livrables.
5. Limitation de débit actuelle à renforcer pour des requêtes concurrentes ;
   validation métier des états familiaux, quotas, sauvegardes et rotation de clés
   à compléter. Vérifier aussi la politique de mots de passe longs avec le
   hachage choisi par PHP sur Hostinger.
6. Chiffrement **au repos**, pas de chiffrement de bout en bout : le serveur
   détient la clé. Textes de confidentialité/CGV encore incomplets, politique des
   mineurs, conservation, effacement et audit indépendant nécessaires.
7. Les images féminines optionnelles absentes dans certains rendus historiques
   déclenchent leurs replis existants ; aucun asset du moteur n'a été remplacé.

Aucune régression détectée dans les contrôles exécutés. Cela ne constitue pas un
audit exhaustif de production, de la qualité narrative ou de l'hébergement réel.
