# Matrice de validation pour la revue indépendante

> Résultats historiques de `32d6b68`. Pour la validation des correctifs actuels,
> lire [audit-followup/VALIDATION.md](audit-followup/VALIDATION.md).

Périmètre : code de `f2b1500`, conservé sans changement fonctionnel dans la
branche de revue. Les documents de cette mission ne constituent pas une
implémentation de l'architecture proposée.

« Déployé » signifie ici déploiement effectué pour cette branche : **aucun**.
Les serveurs et conteneurs de la machine de test ne sont pas un déploiement
Hostinger. L'état des services de production historiques n'est pas audité.

## Développé, vérifié et restant à vérifier

| Périmètre | Développé | Testé automatiquement | Testé manuellement / ponctuellement | Non testé | Déployé |
| --- | --- | --- | --- | --- | --- |
| Moteur Premium | Existant préservé ; changement antérieur limité à la santé | Comparaison syntaxique du moteur hors santé ; empreintes des 70 autres fichiers historiques ; tests de validation/rendus | Inspection ponctuelle d'un PDF Couple par extraction de texte lors de l'étape précédente ; pas une recette éditoriale | Réponses Claude réelles et toutes les personnalisations possibles | Aucun nouveau déploiement |
| Santé Python | `/health` indépendant des clés, `/ready` décrit leur présence | Sans clés, configuration présente et absence de requête distante | Requêtes HTTP ponctuelles scriptées ; pas un parcours humain | Disponibilité réelle et quotas des prestataires | Non |
| Livret de démonstration Solo/Couple | Entrée séparée, réponses simulées et vrais calculs/rendus | Deux parcours, artefacts HTML/PDF, pièces jointes et empreintes | Contrôle ponctuel du texte et de la mention DÉMONSTRATION du PDF | Qualité d'une narration Claude nouvelle ; livraison distante | Non |
| Autres offres | Code commercial conservé | Famille, Prestige, Naissance et Vocation avec narratifs fixtures et vrais HTML/PDF ; bundle testé pour ses pièces jointes | Pas de recette éditoriale indépendante | Parcours distants complets, génération narrative complète du bundle | Non |
| Miroir, carnet, parcours | Fonctions du pack réutilisées | Saisie, absence de témoignage inventé, échappement, enregistrement, bilan et export dans Chromium | Inspection assistée d'une capture mobile ; aucune recette humaine indépendante déclarée | Tous navigateurs, accessibilité complète et suivi humain de 90 jours | Non |
| Arbre et passage au livret | Arbre réutilisé, démo séparée, sélection et accord de reprise | Création d'un arbre personnel, champs transmis minimaux, accord requis, données inconnues à compléter, génération de démo | Pas de recette humaine indépendante | Partage entre comptes, coexistence de tous les liens familiaux, cas limites exhaustifs | Non |
| Comptes PHP/MySQL | API du pack et révocation de sessions après récupération | Connexion, CSRF, cookies, jeton consommé, ancienne session refusée, login/logout navigateur | Contrôles exécutés par scripts, pas d'essai d'inscription par email réel | Délivrance de confirmation/récupération SMTP ; audits bcrypt/mots de passe longs et concurrence complets | Non |
| Sauvegardes | Carnet + arbre versionnés, chiffrement au repos, types JSON préservés, échec explicite | PHP/MariaDB et navigateur, accès anonyme refusé, taille, altération, rollback local, ancien format | Pas de restauration distante sur l'hébergement cible | Rotation des clés, sinistre réel, quotas en charge, fine granularité de partage | Non |
| Stripe local | Politique test/live et transaction du webhook | Clés sentinelles, événements signés fictifs, expiration, mode live refusé, doublon et échec/rejeu | Aucun achat manuel, même en Stripe test distant | Checkout/portail Stripe distants, abonnements complets, remboursements, concurrence et événements désordonnés | Non |
| Commandes/droits communs et worker | Proposition dans `ARCHITECTURE_COMMUNE.md` | Aucun test d'une implémentation : elle n'existe pas encore | À valider par Claude et le propriétaire | Registre canonique, bascule historique, travail durable, livraison idempotente | Non |
| Hostinger et site public | Compatibilité ciblée, notices et schéma préparés | PHP 8.3 et MariaDB locaux seulement ; façade protège les sources privées | Aucun accès hPanel ni essai sur le site public | Version MySQL cible, Apache/.htaccess, TLS, SMTP, charge et reprise sur Hostinger | Non |

Les parcours Chromium sont **automatisés**, y compris le login, la restauration
et les clics. Ils ne doivent pas être présentés comme cinq recettes humaines.
L'inspection visuelle d'une capture ne certifie pas une expérience mobile
irréprochable ni l'accessibilité sur tous les appareils.

## Justification des 40 tests annoncés

| Suite | Commande | Réussis | Échoués / ignorés | Origine de la preuve et portée |
| --- | --- | ---: | --- | --- |
| Python | `python -m unittest discover -s tests -v` | 26 | 0 / 0 | Résultat conservé de l'étape précédente : moteur, démo, rendus fixtures, façade et préservation |
| JavaScript | `node --test tests/js/storage.test.cjs` | 4 | 0 / 0 | Réexécuté pour ce dossier ; sauvegarde/restauration locale, compatibilité et échec |
| API PHP/MariaDB | `python tests/integration/test_vivant_api.py` | 5 | 0 / 0 | Résultat conservé de l'étape précédente, après recréation de la stack ; vrais HTTP/SQL locaux |
| Chromium | `python tests/browser/test_platform_browser.py` | 5 | 0 / 0 | Résultat conservé de l'étape précédente ; navigateur réel, origine distante interdite |
| **Total** | | **40** | **0 / 0** | Tests de tailles différentes, pas 40 validations commerciales de bout en bout |

Le test de rendus supplémentaires contient plusieurs sous-cas ; le test
responsive parcourt quatre largeurs. Ils ne sont pas comptés une seconde fois.
Parmi les 26 tests figurent aussi des contrôles structurels : leur succès prouve
la préservation du code, pas l'exactitude scientifique des lectures.

Les 26 + 5 + 5 tests n'ont pas été relancés pour cette mission documentaire.
Leurs sorties précédentes ont été vérifiées, puis normalisées sans recopier des
journaux d'exécution privés. Tous les fichiers du commit source sont comparés
octet pour octet avant export. La liste des cas et leur résultat est conservée
dans `evidence/results.json` et les trois fichiers texte correspondants.

## Les 13 vérifications PHP, distinctes des 40 tests

Commande : `docker exec origin-vivant-api-test php /tests/policy.php`.
Réexécutée pour préparer ce dossier : **13 assertions réussies**, aucune
requête Stripe distante. Il s'agit d'un script unique, pas de treize tests
d'intégration indépendants :

| N° | Assertion |
| ---: | --- |
| 1 | Paiement fermé par défaut |
| 2 | Checkout test autorisable sans passer en production |
| 3 | Sentinelle de clé test permise dans la politique test |
| 4 | Sentinelle de clé live rejetée pour le paiement test |
| 5 | Sentinelle live rejetée pour le transport test |
| 6 | Staging n'active pas Checkout |
| 7 | L'activation test peut rester désactivée |
| 8 | Production non approuvée refusée |
| 9 | Les anciens drapeaux ne suffisent pas à activer du live |
| 10 | Le résultat chiffré ne contient pas le texte clair de la fixture |
| 11 | Déchiffrement correct de la fixture |
| 12 | Nonce aléatoire produisant un autre chiffré |
| 13 | Altération du chiffré rejetée |

Les clés sentinelles sont uniquement dans les tests. La vraie configuration de
test et sa clé de chiffrement aléatoire ne sont pas dans le dossier exporté.
Ces assertions ne certifient ni la sécurité cryptographique globale, ni une
politique de conservation, ni un paiement effectivement encaissé.

## Vérifications complémentaires et limites

Syntaxe PHP/JavaScript, `pip check`, extraction du PDF et contrôles Git ont été
effectués lors de l'étape précédente ; ils ne sont pas ajoutés au total de 40.
Les erreurs initiales (port 5060 interdit, réseau Docker, objets JSON vides,
double inclusion PHP) ont été corrigées et les suites affectées relancées.

Les illustrations féminines optionnelles manquantes utilisent les replis
historiques ; aucun remplacement n'a été fait. Aucune autre régression n'a été
détectée dans les tests exécutés. Il reste notamment à auditer les cas de
concurrence, droits inter-comptes, reprises, paiements différés, remboursements,
réconciliation des abonnements et résultats indéterminés des prestataires.

La revue indépendante de Claude, les décisions d'architecture et les essais
commerciaux distants ne sont pas réalisés par la préparation de cette archive.
