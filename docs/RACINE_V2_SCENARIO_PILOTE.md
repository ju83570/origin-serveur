# RACINE 2.0 — Scénario pilote de validation

**Objectif** : prouver la valeur réelle et le fonctionnement technique avant une ouverture aux familles.

## Jeu de démonstration
Famille 100 % fictive sur quatre branches ancestrales. Membres fictifs, dates, photographies de test autorisées/non personnelles. Un second espace familial fictif distinct pour tester l'isolation. Les dates des tests doivent être cohérentes entre générations.

## Test 1 — Fiche et émotion
- Depuis un téléphone, ouvrir l'arbre.
- Toucher un portrait → afficher la fiche, la place dans l'arbre et les événements.
- Lire le souvenir « Comment notre grand-père préparait le repas du dimanche » (fictif).
- Ajouter une photo de test et un souvenir; choisir « privé » ou « partagé ».
- Fermer l'écran et se reconnecter depuis un second appareil.
- Retrouver la photo, le souvenir, leur auteur, la date, leur visibilité et leur révision.

**Échec si** une image disparaît, les modifications ne sont qu'en mémoire locale, ou un partage se fait à l'insu du contributeur.

## Test 2 — Collaboration et sécurité
- L'administrateur de la famille A invite le contributeur A2.
- A2 enrichit la fiche, puis l'administrateur voit la contribution et l'approuve selon le mode choisi.
- Un compte de la famille B tente de consulter et modifier la fiche de A : refus serveur.
- L'invitation est révoquée : le lien cesse de fonctionner.
- Un souvenir privé reste invisible au lecteur familial non autorisé.

**Échec si** l'interface masque une ressource mais son API reste accessible, si un lien partagé contourne les droits, ou si une photo d'une famille apparaît dans une autre.

## Test 3 — Véracité de l'histoire
- Événement avec document : afficher « fait documenté » + source.
- Souvenir oral : afficher « témoignage », sans le présenter comme vérifié.
- Événement incertain : afficher « à confirmer ».
- Analyse de dates : montrer les sources et les limites, pas de causalité implicite.
- Absence de dates : ne pas calculer de profil inventé.

## Test 4 — Transmission
- Exporter l'arbre, les événements, contributions et médias autorisés dans un format lisible et réimportable.
- Restaurer sur un environnement de test et retrouver les liens, auteurs, dates, droits et sources.

## Définition du premier « WOW »
> « Je retrouve une personne de ma famille, j'ajoute ce que je sais d'elle, et ce souvenir reste là pour que les personnes autorisées puissent le découvrir et le prolonger. »

Le premier WOW vient d'un fonctionnement vrai, simple et rassurant, pas d'une animation superficielle.

## Mesures avant bêta
- Taux de réussite des parcours sur 2 appareils.
- Zéro accès croisé entre familles lors des tests.
- Pas de régression commande/livret.
- Restauration de sauvegarde démontrée.
- Temps et coût de maintenance évalués.
- Accord explicite du propriétaire ORIGIN avant publication.
