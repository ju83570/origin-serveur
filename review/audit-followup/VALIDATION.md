# Validation des correctifs — 22 octobre 2026

> Rapport original désormais reçu : [CROISEMENT_CLAUDE.md](CROISEMENT_CLAUDE.md)
> détaille les exigences non encore couvertes. Les résultats ci-dessous ne
> démontrent pas la clôture de l'ensemble des constats P1–P10 et Y1–Y3.

Derniers résultats : **71 tests automatisés réussis, 0 échec, 0 test ignoré**,
plus **31 assertions PHP réussies**. Ces totaux ne sont pas additionnés en
« tests de bout en bout ». Les 40 tests et 13 assertions de la revue initiale
sont historiques ; les suites élargies figurent ci-dessous.

| Suite | Résultat final | Périmètre |
| --- | --- | --- |
| Python `unittest discover -s tests -v` | 33/33 | Claude/Brevo simulés, Y1–Y3, santé, calculs/rendus réels hors ligne, préservation du moteur et ressources originales. |
| PHP/MySQL `unittest discover -s tests/integration -v` | 18/18 | PHP/MariaDB locaux : sessions, CSRF, conflits, récupération, chiffrement, suppression, droits et événements. Transport Stripe simulé uniquement par le lanceur CLI de test. |
| Chromium `unittest discover -s tests/browser -v` | 10/10 | 8 recettes plateforme dont mobile 320/390/768/1440, onglet périmé, brouillon préservé, copie mal formée ; 2 recettes du pack transportable/PDF. |
| Node `node --test tests/js/storage.test.cjs` | 10/10 | Formats anciens/nouveaux, arbre absent, journal, rollback, reprise après interruption et contenus incompatibles. |
| PHP `/tests/policy.php` en conteneur isolé | 31 assertions | Politique de paiement, chiffrement/rotation/intégrité/propriétaire, proxys et droits par produit. Aucun transport Stripe. |
| Syntaxe PHP | 7 fichiers valides | Tous les fichiers PHP de l'API. |
| Syntaxe JavaScript | Valide | Modules modifiés et script inline de l'arbre. |
| Dépendances Python | `pip check` réussi | Pas de dépendance cassée dans l'environnement préparé. |

## Réalisation et niveau de preuve

| Élément | Développé | Testé automatiquement | Testé manuellement/ponctuellement | Non testé | Déployé |
| --- | --- | --- | --- | --- | --- |
| Y1 offre/prix | Oui | Payloads simulés et refus négatifs | Diff inspecté | Stripe réel, catalogue historique | Non |
| Y2 authentification | Oui | Aucun travail/email si configuration ou secret incorrect | Présence des variables du shell sans valeurs | Relais et configuration déployés | Non |
| Y3 secret cadeau | Oui | Création/vérification et changement de clé | Diff inspecté | Reprise des codes déjà vendus | Non |
| Préservation Premium | Conservé | AST hors sécurité, travailleur, 70 empreintes ; six types d'offres rendus | Diff `app.py` limité à la sécurité | Qualité Claude et personnalisation exhaustive | Non pour ces correctifs |
| Sauvegarde révisionnée/historique | Oui | Conflits, copies anciennes, corruption, export | Migration locale 003, nombres de comptes/sauvegardes conservés | Vraie base hébergée, crash disque, volumes | Non |
| Copie locale / reprise / onglets | Oui | Node et Chromium | Captures mobile inspectées | Tous navigateurs et quotas | Non |
| Commandes/droits/Checkout | Oui, PHP | Reprise après timeout, transport simulé | Schéma vierge validé dans une base de test distincte | Stripe TEST, reprise clientèle | Non |
| Webhooks | Oui | Signature locale, mode, rejeu, async, remboursement, désordre, commande | Transactions et contraintes inspectées | Rejeu depuis Stripe, comptabilité complexe | Non |
| Proxy / débit | Oui | Politique pure et limites API compte/IP | Configuration conservatrice | Proxys Hostinger, charge | Non |
| Export après résiliation | Oui | Lecture/export sans droits ; arbre antérieur conservé | Parcours décrit | Conservation légale | Non |
| Chiffrement / suppression | Oui | Intégrité, rotation/ancienne clé, propriétaire, cascade | Secrets éphémères contrôlés par booléens | Rotation et snapshots hébergés | Non |
| Miroir et parcours vers Premium | Réutilisé et assemblé | Export consenti, parcours gratuit, vrais PDF de fixture | Capture 390 px inspectée | Recette humaine, accessibilité complète | Non |
| Génération/livraison depuis PHP | Non | Non | Architecture documentée | File/worker, livraison privée, ambiguïtés email | Non |

« Ponctuellement » désigne commandes vérifiées et inspection assistée par
l'agent. Les clics Chromium restent automatisés ; aucune validation humaine
indépendante n'est revendiquée.

## Échecs rencontrés pendant le travail et corrigés

- Le lanceur CLI transformait les objets JSON vides `{}` en tableaux `[]`.
  Deux tests ont révélé cette erreur de fixture ; la lecture préserve désormais
  les types comme l'API HTTP. Le validateur n'a pas été affaibli.
- PHP 8.3 refuse une chaîne comme valeur par défaut d'un paramètre typé
  `callable`. Syntaxe et tests ont bloqué cette régression durant l'ajout du
  transport injectable de Checkout. Le paramètre nullable initialise maintenant
  le transport réel. API et navigateur ont ensuite été relancés intégralement
  avec succès. Aucun de ces états intermédiaires n'a été déployé.
- `file://` est bloqué par la politique du Chromium de cet environnement.
  Aucun contournement : pack transportable testé sur HTTP loopback, sans
  moteur ni API. L'ouverture par double-clic ailleurs reste **non testée**.

## Limites

Aucune clé réelle Claude/Brevo/Stripe, aucun SMTP, aucune requête au site public
ou à Hostinger. Ces tests n'attestent pas d'un paiement, d'une livraison client
ou d'une qualité éditoriale IA réels. La concurrence vérifie une seule révision
gagnante ; le serveur PHP de développement n'est pas un banc de charge
multi-processus. Les verrous doivent aussi être éprouvés sur le serveur cible.

Les PDF portables utilisent WeasyPrint et les rendus préservés, avec personnes
fictives et textes préécrits identifiés. Aucun compte fictif présenté comme
réel, aucun paiement, aucun email dans cette démonstration autonome.

Preuves normalisées sous `evidence/` : aucun secret, dump SQL, cookie, jeton
de session ni donnée de compte n'y est copié.
